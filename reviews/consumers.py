import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class ReviewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time review notifications.
    
    Each repo gets its own "group" in the channel layer.
    When Celery finishes analyzing a PR for repo #1,
    it sends a message to group "repo_1_reviews".
    Every browser connected to that group receives it instantly.
    
    This is the pub/sub pattern:
    - Celery publishes to a group
    - Connected browsers subscribe to that group
    - Redis is the message bus between them
    """

    async def connect(self):
        self.repo_id = self.scope['url_route']['kwargs']['repo_id']
        self.group_name = f'repo_{self.repo_id}_reviews'

        # Verify the user has access to this repo
        # before accepting the WebSocket connection
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            logger.warning(f"Unauthenticated WebSocket connection attempt for repo {self.repo_id}")
            await self.close()
            return

        has_access = await self._check_repo_access(user, self.repo_id)
        if not has_access:
            logger.warning(f"User {user} attempted to connect to repo {self.repo_id} without access")
            await self.close()
            return

        # Join the group for this repo
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected: user {user} watching repo {self.repo_id}")

        # Send current pending reviews immediately on connect
        # So the dashboard doesn't start blank
        pending = await self._get_pending_reviews(self.repo_id)
        if pending:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'pending_count': pending,
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected from repo {self.repo_id}")

    async def receive(self, text_data):
        # Client can send a ping to keep connection alive
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    # ----------------------------------------------------------------
    # Message handlers — called when Celery sends to this group
    # Method name must match the message type exactly
    # ----------------------------------------------------------------

    async def review_complete(self, event):
        """
        Called when Celery sends a 'review_complete' message.
        Forwards it to the connected browser.
        """
        await self.send(text_data=json.dumps({
            'type': 'review_complete',
            'event_id': event['event_id'],
            'pr_number': event['pr_number'],
            'pr_title': event['pr_title'],
            'status': event['status'],
            'scanner_issues': event['scanner_issues'],
            'codebert_risk': event['codebert_risk'],
        }))

    async def review_failed(self, event):
        """Called when a review fails after all retries."""
        await self.send(text_data=json.dumps({
            'type': 'review_failed',
            'event_id': event['event_id'],
            'pr_number': event['pr_number'],
            'error': event.get('error', 'Analysis failed'),
        }))

    # ----------------------------------------------------------------
    # Database helpers — must be async since consumer is async
    # database_sync_to_async wraps synchronous ORM calls
    # ----------------------------------------------------------------

    @database_sync_to_async
    def _check_repo_access(self, user, repo_id):
        from teams.models import TeamMembership, RepositoryConfig
        try:
            repo = RepositoryConfig.objects.get(id=repo_id)
            return TeamMembership.objects.filter(
                team=repo.team,
                user=user
            ).exists()
        except RepositoryConfig.DoesNotExist:
            return False

    @database_sync_to_async
    def _get_pending_reviews(self, repo_id):
        from webhooks.models import PullRequestEvent
        return PullRequestEvent.objects.filter(
            repository_config_id=repo_id,
            status='pending'
        ).count()