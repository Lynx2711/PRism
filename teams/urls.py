from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    TeamView,
    RepositoryView,
    RepoReviewsView,
    RepoConfigView,
    RepoAnalyticsView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('teams/', TeamView.as_view(), name='teams'),
    path('repos/', RepositoryView.as_view(), name='repos'),
    path('repos/<int:repo_id>/reviews/', RepoReviewsView.as_view(), name='repo-reviews'),
    path('repos/<int:repo_id>/config/', RepoConfigView.as_view(), name='repo-config'),
    path('repos/<int:repo_id>/analytics/', RepoAnalyticsView.as_view(), name='repo-analytics'),
]