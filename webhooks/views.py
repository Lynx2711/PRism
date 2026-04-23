import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from teams.models import RepositoryConfig
from .models import PullRequestEvent
from .utils import validate_github_signature

logger = logging.getLogger(__name__)


class GitHubWebhookView(APIView):
    permission_classes = [AllowAny] #GitHub doesn't have a JWT token. It can't log in to your system. The authentication mechanism here is the HMAC signature validation, not Django's auth system. Two completely different auth patterns for two completely different callers.
    authentication_classes = []

    def post(self, request):
        if not validate_github_signature(request):
            logger.warning("Webhook received with invalid signature — rejected")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        event_type = request.headers.get('X-GitHub-Event', '')
        payload = request.data

        logger.info(f"Received GitHub event: {event_type}")

        if event_type == 'ping':
            return Response({'message': 'pong'}, status=status.HTTP_200_OK)

        if event_type == 'pull_request':
            return self._handle_pull_request(payload)

        return Response({'message': f'Event {event_type} received but not handled'})

    def _handle_pull_request(self, payload):
        action = payload.get('action')

        if action not in ('opened', 'synchronize'):
            return Response({'message': f'PR action {action} ignored'})

        pr = payload['pull_request']
        repo = payload['repository']
        repo_full_name = repo['full_name']
        # Look up which team owns this repo
        # If no team has connected this repo, we still process it
        # but without team-specific config
        try:
            configs = list(RepositoryConfig.objects.filter(
                repo_full_name=repo_full_name,
                is_active=True
            ))
            if len(configs) > 1:
                logger.warning(
                    f"Multiple active configs found for {repo_full_name} — using first match"
                )
            repo_config = configs[0] if configs else None  # returns None if no matches
            if repo_config is None:
                logger.info(f"No team config found for {repo_full_name} - using defaults")
        except Exception as e:
            repo_config = None
            logger.error(f"Error looking up repo config for {repo_full_name}: {e}")

        event = PullRequestEvent.objects.create(
            github_pr_id=pr['id'],
            repo_full_name=repo['full_name'],
            pr_number=pr['number'],
            pr_title=pr['title'],
            pr_author=pr['user']['login'],
            head_sha=pr['head']['sha'],
            diff_url=pr['diff_url'],
            raw_payload=payload,
            repository_config=repo_config,
        )

        logger.info(f"Saved PR #{event.pr_number} from {event.repo_full_name} - queuing analysis")

        from .tasks import analyze_pull_request
        analyze_pull_request.delay(event.id)

        return Response({
            'message': 'PR event queued for analysis',
            'event_id': event.id,
        }, status=status.HTTP_202_ACCEPTED)