from django.db import models

# Create your models here.
class PullRequestEvent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('failed', 'Failed'),
    ]

    github_pr_id = models.BigIntegerField()
    repo_full_name = models.CharField(max_length=255)
    pr_number = models.IntegerField()
    pr_title = models.CharField(max_length=500)
    pr_author = models.CharField(max_length=150)
    head_sha = models.CharField(max_length=40)
    diff_url = models.URLField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_payload = models.JSONField() #stores the entire GitHub webhook payload as-is. This might seem wasteful but it's a deliberate engineering decision. GitHub's PR payload has 200+ fields. You don't know today which ones you'll need in Week 6 when you're building analytics. Storing the raw payload means you never lose data — you can always go back and extract new fields from historical events without asking GitHub to resend them.
    repository_config = models.ForeignKey(
        # Link to which team's repo config this belongs to
        # null=True for now — existing records don't have this yet
        # We'll populate it when the webhook comes in
        'teams.RepositoryConfig',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pull_request_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # gives human-readable representation in Django admin and shell
        return f"PR #{self.pr_number} — {self.repo_full_name} [{self.status}]"