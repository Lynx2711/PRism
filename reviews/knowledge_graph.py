import json
import logging
import networkx as nx
from collections import defaultdict

logger = logging.getLogger(__name__)


class RepositoryKnowledgeGraph:
    """
    Builds and queries a knowledge graph for a single repository.
    Each RepositoryConfig gets its own graph instance.
    
    The graph captures relationships that emerge over time:
    - Which files change together frequently
    - Which patterns keep appearing in this codebase
    - Which authors touch which files
    - How function complexity trends over time
    
    This is what makes CodeSense stateful — it remembers.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.pr_count = 0  # how many PRs have been analyzed

    # ----------------------------------------------------------------
    # Serialization — storing the graph in PostgreSQL as JSON
    # ----------------------------------------------------------------

    def to_dict(self):
        """
        Convert graph to a JSON-serializable dict.
        NetworkX has a built-in serializer for this.
        """
        data = nx.node_link_data(self.graph)
        data['pr_count'] = self.pr_count
        return data

    @classmethod
    def from_dict(cls, data):
        """
        Rebuild graph from stored JSON.
        Called at the start of each Celery task.
        """
        instance = cls()
        if not data:
            return instance
        pr_count = data.pop('pr_count', 0)
        instance.graph = nx.node_link_graph(data)
        instance.pr_count = pr_count
        return instance

    # ----------------------------------------------------------------
    # Graph building — called after each PR is analyzed
    # ----------------------------------------------------------------

    def update_from_pr(self, pr_event, diff_content, scanner_findings):
        """
        Update the graph with data from a newly analyzed PR.
        This is how the graph grows over time.
        """
        self.pr_count += 1
        changed_files = [f['filename'] for f in diff_content if f['status'] != 'removed']

        # Update file nodes
        for file in diff_content:
            self._update_file_node(file)

        # Update co-change edges between files
        # Every pair of files that changed in the same PR
        # gets an edge — or their existing edge gets stronger
        self._update_co_change_edges(changed_files)

        # Update pattern nodes from scanner findings
        for finding in scanner_findings:
            self._update_pattern_node(finding)

        # Update author node
        self._update_author_node(pr_event.pr_author, changed_files)

        logger.info(
            f"Knowledge graph updated — "
            f"{self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges, "
            f"{self.pr_count} PRs analyzed"
        )

    def _update_file_node(self, file):
        """
        Each file gets a node tracking its history.
        Additions/deletions trend over time tells you
        if a file is growing out of control.
        """
        filename = file['filename']

        if self.graph.has_node(filename):
            # update existing node
            node = self.graph.nodes[filename]
            node['times_changed'] = node.get('times_changed', 0) + 1
            node['total_additions'] = node.get('total_additions', 0) + file['additions']
            node['total_deletions'] = node.get('total_deletions', 0) + file['deletions']
            # rolling average of additions per PR
            node['avg_additions'] = node['total_additions'] / node['times_changed']
        else:
            self.graph.add_node(
                filename,
                type='file',
                times_changed=1,
                total_additions=file['additions'],
                total_deletions=file['deletions'],
                avg_additions=file['additions'],
            )

    def _update_co_change_edges(self, changed_files):
        """
        Files that change together frequently are coupled.
        High coupling means: if one changes without the other,
        something might be wrong — flag it in the review.
        """
        # every combination of two files in this PR
        for i, file_a in enumerate(changed_files):
            for file_b in changed_files[i + 1:]:
                if self.graph.has_edge(file_a, file_b):
                    self.graph[file_a][file_b]['co_changes'] += 1
                else:
                    self.graph.add_edge(file_a, file_b, co_changes=1, type='co_change')

    def _update_pattern_node(self, finding):
        """
        Track recurring security patterns.
        A pattern that keeps appearing in this repo
        should be flagged with higher confidence.
        """
        pattern_id = f"pattern:{finding['pattern_name']}"

        if self.graph.has_node(pattern_id):
            self.graph.nodes[pattern_id]['occurrences'] += 1
        else:
            self.graph.add_node(
                pattern_id,
                type='pattern',
                pattern_name=finding['pattern_name'],
                severity=finding['severity'],
                occurrences=1,
            )

        # edge from file to pattern — this file has this problem
        filename = finding['filename']
        edge_key = (filename, pattern_id)
        if self.graph.has_edge(*edge_key):
            self.graph[filename][pattern_id]['count'] += 1
        else:
            self.graph.add_edge(filename, pattern_id, count=1, type='has_pattern')

    def _update_author_node(self, author, changed_files):
        """
        Track which authors touch which files.
        Useful for routing reviews to the right people
        and understanding code ownership.
        """
        author_id = f"author:{author}"

        if not self.graph.has_node(author_id):
            self.graph.add_node(author_id, type='author', username=author, pr_count=0)

        self.graph.nodes[author_id]['pr_count'] += 1

        for filename in changed_files:
            if self.graph.has_edge(author_id, filename):
                self.graph[author_id][filename]['touches'] += 1
            else:
                self.graph.add_edge(author_id, filename, touches=1, type='touches')

    # ----------------------------------------------------------------
    # Graph querying — called during PR analysis to improve reviews
    # ----------------------------------------------------------------

    def get_file_insights(self, filename):
        """
        What does the graph know about this file?
        Returns context that improves review quality.
        """
        if not self.graph.has_node(filename):
            return {'known': False}

        node = self.graph.nodes[filename]
        insights = {
            'known': True,
            'times_changed': node.get('times_changed', 0),
            'avg_additions': round(node.get('avg_additions', 0), 1),
            'frequently_coupled_with': self._get_coupled_files(filename),
            'recurring_patterns': self._get_file_patterns(filename),
        }
        return insights

    def _get_coupled_files(self, filename, threshold=2):
        """
        Files that have changed together with this file
        more than `threshold` times — strong coupling signal.
        """
        if not self.graph.has_node(filename):
            return []
        coupled = []
        for neighbor in self.graph.neighbors(filename):
            edge = self.graph[filename][neighbor]
            if edge.get('type') == 'co_change' and edge.get('co_changes', 0) >= threshold:
                coupled.append({
                    'filename': neighbor,
                    'co_changes': edge['co_changes'],
                })
        return sorted(coupled, key=lambda x: x['co_changes'], reverse=True)

    def _get_file_patterns(self, filename):
        """
        Security patterns that have appeared in this file before.
        If a pattern keeps recurring, flag with higher confidence.
        """
        if not self.graph.has_node(filename):
            return []
        patterns = []
        for neighbor in self.graph.neighbors(filename):
            if neighbor.startswith('pattern:'):
                edge = self.graph[filename][neighbor]
                node = self.graph.nodes[neighbor]
                patterns.append({
                    'pattern_name': node['pattern_name'],
                    'occurrences': node['occurrences'],
                    'severity': node['severity'],
                })
        return patterns

    def get_missing_coupled_files(self, changed_files):
        """
        The most powerful graph query — find files that
        SHOULD have changed but DIDN'T.

        If auth.py and utils.py always change together (8/10 PRs)
        but this PR only changed auth.py — flag it.
        The developer might have forgotten to update utils.py.
        """
        missing = []
        changed_set = set(changed_files)

        for filename in changed_files:
            if not self.graph.has_node(filename):
                continue
            coupled = self._get_coupled_files(filename, threshold=3)
            for coupled_file in coupled:
                if coupled_file['filename'] not in changed_set:
                    missing.append({
                        'changed_file': filename,
                        'missing_file': coupled_file['filename'],
                        'co_changes': coupled_file['co_changes'],
                        'message': (
                            f"`{coupled_file['filename']}` usually changes with "
                            f"`{filename}` ({coupled_file['co_changes']} times) "
                            f"but wasn't included in this PR."
                        )
                    })
        return missing

    def get_pattern_confidence(self, pattern_name):
        """
        How many times has this pattern appeared in this repo?
        More occurrences = higher confidence in the finding.
        Used to adjust severity dynamically.
        """
        pattern_id = f"pattern:{pattern_name}"
        if not self.graph.has_node(pattern_id):
            return 1  # first time seeing it — base confidence

        occurrences = self.graph.nodes[pattern_id].get('occurrences', 1)

        # confidence multiplier — caps at 3x
        # seen 5+ times in this repo = very high confidence
        return min(occurrences, 5) / 5 * 3