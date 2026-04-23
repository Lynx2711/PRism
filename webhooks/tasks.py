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
        auth = Auth.AppAuth(
            app_id=int(settings.GITHUB_APP_ID),
            private_key=open(settings.GITHUB_APP_PRIVATE_KEY_PATH).read()
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
        # --- Fetch diff ---
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
        
        logger.info(
            f"Fetched diff for PR #{event.pr_number} — "
            f"{len(files)} files changed"
        )
        # --- Stage 1: Security scanner (fast, runs first) ---
        scanner_findings = scan_diff(diff_content)
        logger.info(f"Scanner found {len(scanner_findings)} issues")
        # --- Stage 2: CodeBERT analysis (slower, runs after) ---
        codebert_findings = analyzer.analyze_diff(diff_content)
        logger.info(f"CodeBERT analysis complete — {len(codebert_findings)} files scored")

        # --- Stage 3: Post review comments to GitHub ---
        _post_review_comments(pull_request, scanner_findings, codebert_findings, event)
        # --- Save everything ---
        event.raw_payload['diff_content'] = diff_content
        event.raw_payload['scanner_findings'] = scanner_findings
        event.raw_payload['codebert_findings'] = codebert_findings
        event.status = 'complete'
        event.save(update_fields=['raw_payload', 'status'])

        # logger.info(
        #     f"Successfully processed PR #{event.pr_number} — "
        #     f"{len(files)} files changed"
        # )

        return{
            'event_id': event_id,
            'files_changed': len(files),
            'scanner_issues': len(scanner_findings),
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

def _post_review_comments(pull_request, scanner_findings, codebert_findings, event):
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
            'position': finding['line'],  # position in diff, not file line number
            'body': body,
        })

    # Add a summary comment from CodeBERT at PR level
    if codebert_findings:
        high_risk = [f for f in codebert_findings if f['severity'] in ('high', 'medium')]
        if high_risk:
            summary_lines = ["**CodeSense Analysis Summary**\n"]
            for f in high_risk:
                summary_lines.append(
                    f"- `{f['filename']}` — risk score {f['risk_score']} ({f['severity']})"
                )
            pull_request.create_issue_comment('\n'.join(summary_lines))
            logger.info("Posted CodeBERT summary comment to PR")

    # Post inline comments from scanner
    if comments:
        try:
            commits = list(pull_request.get_commits())
            review = pull_request.create_review(
                commit=commits[-1],
                body="**CodeSense Security Review**\n\nAutomated security scan complete.",
                event="COMMENT",
                comments=comments
            )
            logger.info(f"Posted review with {len(comments)} inline comments to PR #{event.pr_number}")
        except GithubException as e:
            logger.error(f"Failed to post review comments: {e}")
            # Fall back to PR-level comment instead
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