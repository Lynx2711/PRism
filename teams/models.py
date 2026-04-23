from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model — extends Django's built-in user.
    AUTH_USER_MODEL = 'teams.User' points here.
    Even if we don't add custom fields now, having a custom user model
    from the start means we can add fields later without painful migrations.
    """
    pass



class Team(models.Model):
    """
    A team is one company/organization using CodeSense.
    Everything in the system belongs to a team.
    This is the top of the isolation hierarchy.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # url-safe identifier e.g. "acme-corp"
    github_org_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # The user who created/owns this team
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # can't delete owner without handling team first
        related_name='owned_teams'
    )

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """
    Which users belong to which team.
    A user can belong to multiple teams (consultant scenario).
    A team can have multiple users (normal scenario).
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),      # can configure repos, manage members
        ('member', 'Member'),    # can view reviews
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'user')  # can't be in same team twice

    def __str__(self):
        return f"{self.user} in {self.team} as {self.role}"


class RepositoryConfig(models.Model):
    """
    Each repo a team connects gets its own configuration.
    This is where per-repo rules live — max function length,
    naming conventions, which scanners to run, etc.
    
    This is the bridge between a Team and a GitHub repo.
    A repo only exists in CodeSense if a team explicitly connected it.
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='repositories')
    repo_full_name = models.CharField(max_length=255)  # "myorg/myrepo"
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    # Per-repo configuration rules stored as JSON
    # Flexible — teams can add custom rules without schema changes
    config = models.JSONField(default=dict)
    # The knowledge graph — grows with every PR analyzed
    # Stored as JSON, loaded into NetworkX when needed
    knowledge_graph_data = models.JSONField(default=dict, blank=True)

    # Sensible defaults — teams that haven't configured anything
    # get these automatically. Team overrides take priority.
    DEFAULT_CONFIG = {
        'max_function_lines': 50,
        'enforce_naming': True,
        'run_security_scanner': True,
        'run_codebert': True,
        'notify_on_critical': True,
    }

    class Meta:
        unique_together = ('team', 'repo_full_name')  # one config per repo per team

    def __str__(self):
        return f"{self.repo_full_name} ({self.team.name})"

    def get_full_config(self):
        """
        Returns team config merged with defaults.
        Team config takes priority — defaults fill in missing keys.
        """
        return {**self.DEFAULT_CONFIG, **self.config}

    def get_config(self, key, default=None):
        """Helper to safely read a single config value with a default."""
        return self.get_full_config().get(key, default)
