import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from .models import Team, TeamMembership, RepositoryConfig
from .serializers import (
    UserRegistrationSerializer,
    TeamSerializer,
    RepositoryConfigSerializer,
    ReviewSummarySerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """Create a new user account."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # issue tokens immediately on registration
            # user doesn't need to log in separately
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserRegistrationSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """Exchange credentials for JWT tokens."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class TeamView(APIView):
    """Create a team or get current user's teams."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # return teams the user is a member of
        memberships = TeamMembership.objects.filter(
            user=request.user
        ).select_related('team')
        teams = [m.team for m in memberships]
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            # creator becomes owner and first admin member
            team = serializer.save(owner=request.user)
            TeamMembership.objects.create(
                team=team,
                user=request.user,
                role='admin'
            )
            logger.info(f"Team '{team.name}' created by {request.user.username}")
            return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RepositoryView(APIView):
    """Connect a repo to a team or list connected repos."""
    permission_classes = [IsAuthenticated]

    def _get_user_team(self, request):
        """
        Get the team for this user.
        For now assumes one team per user — we'll handle
        multi-team users when we build team switching in React.
        """
        membership = TeamMembership.objects.filter(
            user=request.user
        ).select_related('team').first()

        if not membership:
            return None
        return membership.team

    def get(self, request):
        team = self._get_user_team(request)
        if not team:
            return Response(
                {'error': 'You are not a member of any team'},
                status=status.HTTP_403_FORBIDDEN
            )

        repos = RepositoryConfig.objects.filter(team=team, is_active=True)
        serializer = RepositoryConfigSerializer(repos, many=True)
        return Response(serializer.data)

    def post(self, request):
        team = self._get_user_team(request)
        if not team:
            return Response(
                {'error': 'You are not a member of any team'},
                status=status.HTTP_403_FORBIDDEN
            )

        # check admin role — only admins can connect repos
        membership = TeamMembership.objects.get(team=team, user=request.user)
        if membership.role != 'admin':
            return Response(
                {'error': 'Only team admins can connect repositories'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RepositoryConfigSerializer(data=request.data)
        if serializer.is_valid():
            repo = serializer.save(team=team)
            logger.info(f"Repo '{repo.repo_full_name}' connected to team '{team.name}'")
            return Response(
                RepositoryConfigSerializer(repo).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(never_cache, name='dispatch')
class RepoReviewsView(APIView):
    """Get all reviews for a specific repo."""
    permission_classes = [IsAuthenticated]

    def get(self, request, repo_id):
        team = RepositoryView._get_user_team(self, request)
        if not team:
            return Response(
                {'error': 'You are not a member of any team'},
                status=status.HTTP_403_FORBIDDEN
            )

        # verify this repo belongs to the user's team
        # this is the data isolation check
        repo = get_object_or_404(
            RepositoryConfig,
            id=repo_id,
            team=team        # ← can't access another team's repo
        )

        events = repo.pull_request_events.all().order_by('-created_at')
        serializer = ReviewSummarySerializer(events, many=True)
        return Response(serializer.data)


class RepoConfigView(APIView):
    """Update configuration for a specific repo."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, repo_id):
        team = RepositoryView._get_user_team(self, request)
        if not team:
            return Response(
                {'error': 'You are not a member of any team'},
                status=status.HTTP_403_FORBIDDEN
            )

        membership = TeamMembership.objects.get(team=team, user=request.user)
        if membership.role != 'admin':
            return Response(
                {'error': 'Only admins can update repo configuration'},
                status=status.HTTP_403_FORBIDDEN
            )

        repo = get_object_or_404(RepositoryConfig, id=repo_id, team=team)

        # merge new config into existing — don't replace entirely
        # PATCH means partial update
        repo.config.update(request.data.get('config', {}))
        repo.save(update_fields=['config'])

        return Response(RepositoryConfigSerializer(repo).data)