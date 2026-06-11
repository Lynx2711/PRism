import logging
from celery import shared_task
from django.conf import settings
from github import Github, GithubException
from github import Auth

logger = logging.getLogger(__name__) 

@shared_task(
    bind = True, # Celery passes the task instance as self — just like a method on a class. This gives you access to self.retry() which is how you tell Celery "this failed, try again later." Without bind=True, you have no way to trigger retries from inside the task.
    max_retries = 3,
    default_retry_delay = 60
)

def analyze_pull_request(self, event_id):
    from .models import PullRequestEvent #Importing inside the function guarantees the model is always available by the time the task actually runs
    from reviews.scanner import scan_diff
    from reviews.analyzer import analyzer
    try:
        event = PullRequestEvent.objects.get(id=event_id)
    except PullRequestEvent.DoesNotExist:
        logger.error(f"PullRequestEvent {event_id} not found - Task Aborted")
        return

    event.status = 'processing'
    event.save(update_fields=['status'])

    try:
        # Support both direct key content (production) and file path (local dev)
        import os
        private_key = os.getenv('GITHUB_APP_PRIVATE_KEY')
        if private_key:
            # Env vars from .env files store newlines as literal '\n' —
            # convert them to actual newline characters for PEM parsing
            private_key = private_key.replace('\\n', '\n')
        else:
            # fallback to file for local development
            private_key = open(settings.GITHUB_APP_PRIVATE_KEY_PATH).read()

        auth = Auth.AppAuth(
            app_id=int(settings.GITHUB_APP_ID),
            private_key=private_key
        )
        from github import GithubIntegration
        gi = GithubIntegration(auth=auth)
        installation = gi.get_repo_installation(
            event.repo_full_name.split('/')[0],  # owner
            event.repo_full_name.split('/')[1]   # repo name
        )
        install_client = gi.get_github_for_installation(installation.id)
        repo = install_client.get_repo(event.repo_full_name)
        pull_request = repo.get_pull(event.pr_number)
        # --- Fetch diff (same as before) ---
        files = list(pull_request.get_files())
        diff_content = []
        for file in files:
            diff_content.append({
                'filename': file.filename,
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'patch': file.patch or '',
            })

        logger.info(f"Fetched diff for PR #{event.pr_number} — {len(files)} files changed")

        # --- Load knowledge graph for this repo ---
        repo_config = event.repository_config
        if repo_config:
            from reviews.knowledge_graph import RepositoryKnowledgeGraph
            kg = RepositoryKnowledgeGraph.from_dict(
                dict(repo_config.knowledge_graph_data)
            )
        else:
            from reviews.knowledge_graph import RepositoryKnowledgeGraph
            kg = RepositoryKnowledgeGraph()

        # --- Stage 1: Security scanner ---
        scanner_findings = scan_diff(diff_content)
        logger.info(f"Scanner found {len(scanner_findings)} issues")

        # --- Stage 2: Graph insights ---
        changed_files = [f['filename'] for f in diff_content]
        missing_files = kg.get_missing_coupled_files(changed_files)
        if missing_files:
            for m in missing_files:
                logger.info(f"Graph insight: {m['message']}")

        # --- Stage 3: CodeBERT ---
        codebert_findings = analyzer.analyze_diff(diff_content)
        logger.info(f"CodeBERT analysis complete — {len(codebert_findings)} files scored")

        # --- Stage 4: Post review comments ---
        _post_review_comments(
            pull_request, scanner_findings,
            codebert_findings, missing_files, event
        )

        # --- Stage 5: Update knowledge graph ---
        kg.update_from_pr(event, diff_content, scanner_findings)

        # --- Save everything ---
        event.raw_payload['diff_content'] = diff_content
        event.raw_payload['scanner_findings'] = scanner_findings
        event.raw_payload['codebert_findings'] = codebert_findings
        event.raw_payload['graph_insights'] = missing_files
        event.status = 'complete'
        event.save(update_fields=['raw_payload', 'status'])

        # Save updated graph back to repo config
        if repo_config:
            repo_config.knowledge_graph_data = kg.to_dict()
            repo_config.save(update_fields=['knowledge_graph_data'])

        # --- Send WebSocket notification (after save so DB is consistent) ---
        if event.repository_config:
            _send_websocket_notification(event, scanner_findings, codebert_findings)
        else:
            logger.warning(f"No repository_config for event {event.id} — skipping WebSocket notification")

        return {
            'event_id': event_id,
            'files_changed': len(files),
            'scanner_issues': len(scanner_findings),
            'graph_insights': len(missing_files),
            'status': 'complete'
        }

    except GithubException as e:
        logger.error(f"GitHub API error for PR #{event.pr_number}: {e}")
        if self.request.retries >= self.max_retries:
            # genuinely giving up
            event.status = 'failed'
            event.save(update_fields=['status'])
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Unexpected error for PR #{event.pr_number}: {e}")
        if self.request.retries >= self.max_retries:
            event.status = 'failed'
            event.save(update_fields=['status'])
        raise self.retry(exc=e)

def _post_review_comments(pull_request, scanner_findings, codebert_findings, missing_files, event):
    """
    Post structured review comments back to the PR on GitHub.
    This is what makes CodeSense visible to the developer —
    comments appear directly on the lines in the PR diff.
    """
    comments = []

    # Build comments from scanner findings first (highest confidence)
    for finding in scanner_findings:
        severity_emoji = {
            'critical': 'CRITICAL',
            'high': 'HIGH',
            'medium': 'MEDIUM',
            'low': 'LOW'
        }.get(finding['severity'], 'INFO')

        body = (
            f"**[CodeSense {severity_emoji}]** {finding['description']}\n\n"
            f"```\n{finding['code']}\n```\n\n"
            f"*Detected by security scanner*"
        )

        comments.append({
            'path': finding['filename'],
            'position': finding['line'],
            'body': body,
        })

    # Post graph insights as PR-level comment
    # These are repo-level observations, not line-level
    if missing_files:
        insight_lines = ["**CodeSense Graph Insights**\n"]
        insight_lines.append("*Based on historical patterns in this repository:*\n")
        for m in missing_files:
            insight_lines.append(f"- {m['message']}")
        pull_request.create_issue_comment('\n'.join(insight_lines))
        logger.info(f"Posted {len(missing_files)} graph insights to PR #{event.pr_number}")

    if codebert_findings:
        high_risk = [f for f in codebert_findings if f['severity'] in ('high', 'medium')]
        if high_risk:
            summary_lines = ["**CodeSense Analysis Summary**\n"]
            for f in high_risk:
                summary_lines.append(
                    f"- `{f['filename']}` — risk score {f['risk_score']} ({f['severity']})"
                )
            pull_request.create_issue_comment('\n'.join(summary_lines))

    if comments:
        try:
            commits = list(pull_request.get_commits())
            pull_request.create_review(
                commit=commits[-1],
                body="**CodeSense Security Review**\n\nAutomated security scan complete.",
                event="COMMENT",
                comments=comments
            )
            logger.info(f"Posted review with {len(comments)} inline comments to PR #{event.pr_number}")
        except GithubException as e:
            logger.error(f"Failed to post review comments: {e}")
            _post_as_pr_comment(pull_request, scanner_findings, event)


def _post_as_pr_comment(pull_request, scanner_findings, event):
    """
    Fallback — post findings as a regular PR comment when
    inline comments fail. Less precise but always works.
    """
    if not scanner_findings:
        return

    lines = ["**CodeSense Security Review**\n"]
    lines.append("*Inline comments could not be posted — showing summary instead*\n")

    for f in scanner_findings:
        severity = f['severity'].upper()
        lines.append(f"**[{severity}]** `{f['filename']}` line {f.get('file_line', f['line'])}")
        lines.append(f"> {f['description']}")
        lines.append(f"```\n{f['code']}\n```\n")

    pull_request.create_issue_comment('\n'.join(lines))
    logger.info(f"Posted fallback PR comment for PR #{event.pr_number}")


def _send_websocket_notification(event, scanner_findings, codebert_findings):
    """
    Send real-time notification to connected dashboard browsers.
    Uses async_to_sync because Celery tasks are synchronous
    but the channel layer is async.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("No channel layer configured — skipping WebSocket notification")
        return

    group_name = f'repo_{event.repository_config_id}_reviews'

    codebert_risk = None
    if codebert_findings:
        scores = [f['risk_score'] for f in codebert_findings]
        codebert_risk = max(scores) if scores else None

    message = {
        'type': 'review_complete',  # maps to review_complete() in consumer
        'event_id': event.id,
        'pr_number': event.pr_number,
        'pr_title': event.pr_title,
        'status': 'complete',
        'scanner_issues': {
            'total': len(scanner_findings),
            'critical': len([f for f in scanner_findings if f['severity'] == 'critical']),
            'high': len([f for f in scanner_findings if f['severity'] == 'high']),
        },
        'codebert_risk': codebert_risk,
    }

    try:
        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.info(f"WebSocket notification sent for PR #{event.pr_number}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")
        # Don't re-raise — WebSocket failure shouldn't fail the whole task