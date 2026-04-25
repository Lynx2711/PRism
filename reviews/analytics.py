from django.db.models import Count
from collections import defaultdict


def get_repo_analytics(repo_config):
    """
    Aggregate all review data for a repository into
    meaningful metrics for the dashboard.
    """
    events = repo_config.pull_request_events.filter(
        status='complete'
    ).order_by('created_at')

    if not events.exists():
        return {'message': 'No completed reviews yet'}

    total_prs = events.count()
    issues_by_severity = defaultdict(int)
    pattern_counts = defaultdict(int)
    file_issue_counts = defaultdict(int)
    author_stats = defaultdict(lambda: {'prs': 0, 'issues': 0})
    risk_trend = []

    for event in events:
        # Author stats
        author_stats[event.pr_author]['prs'] += 1

        # Scanner findings aggregation
        scanner_findings = event.raw_payload.get('scanner_findings', [])
        for finding in scanner_findings:
            issues_by_severity[finding['severity']] += 1
            pattern_counts[finding['pattern_name']] += 1
            file_issue_counts[finding['filename']] += 1
            author_stats[event.pr_author]['issues'] += 1

        # CodeBERT risk trend
        codebert_findings = event.raw_payload.get('codebert_findings', [])
        if codebert_findings:
            max_risk = max(f['risk_score'] for f in codebert_findings)
            risk_trend.append({
                'pr_number': event.pr_number,
                'risk_score': max_risk,
                'date': event.created_at.isoformat(),
            })

    # Most problematic files — sorted by issue count
    problematic_files = sorted(
        [{'filename': f, 'issue_count': c} for f, c in file_issue_counts.items()],
        key=lambda x: x['issue_count'],
        reverse=True
    )[:5]  # top 5

    # Top recurring patterns
    top_patterns = sorted(
        [{'pattern': p, 'count': c} for p, c in pattern_counts.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:5]

    return {
        'total_prs_reviewed': total_prs,
        'issues_by_severity': dict(issues_by_severity),
        'most_problematic_files': problematic_files,
        'top_patterns': top_patterns,
        'risk_trend': risk_trend,
        'author_stats': dict(author_stats),
        'total_issues_found': sum(issues_by_severity.values()),
    }