from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs


@database_sync_to_async
def get_user_from_token(token_key):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    User = get_user_model()
    try:
        token = AccessToken(token_key)
        user_id = token.get('user_id')
        if user_id is None:
            return AnonymousUser()
        return User.objects.get(id=int(user_id))  # force int conversion
    except (InvalidToken, TokenError, User.DoesNotExist, ValueError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Reads JWT token from query parameter for WebSocket connections.
    Usage: ws://localhost:8000/ws/repos/1/reviews/?token=<access_token>
    """
    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', [None])
        token = token_list[0] if token_list else None

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)