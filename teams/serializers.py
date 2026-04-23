from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Team, TeamMembership, RepositoryConfig

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        # use create_user so password gets hashed properly
        # never store plain text passwords
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        return user


class TeamSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'slug', 'github_org_name', 'owner_username', 'member_count', 'created_at')
        read_only_fields = ('id', 'created_at', 'owner_username')

    def get_member_count(self, obj):
        return obj.memberships.count()

    def validate_slug(self, value):
        # slugs must be lowercase
        return value.lower()


class RepositoryConfigSerializer(serializers.ModelSerializer):
    full_config = serializers.SerializerMethodField()
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = RepositoryConfig
        fields = (
            'id', 'repo_full_name', 'is_active',
            'config', 'full_config', 'team_name', 'connected_at'
        )
        read_only_fields = ('id', 'connected_at', 'team_name')

    def get_full_config(self, obj):
        # expose merged config (defaults + overrides) to the frontend
        return obj.get_full_config()


class ReviewSummarySerializer(serializers.Serializer):
    """
    Serializes a PullRequestEvent into a review summary for the dashboard.
    Not a ModelSerializer because we're shaping the output specifically
    for the frontend — not exposing the raw model fields.
    """
    event_id = serializers.IntegerField(source='id')
    pr_number = serializers.IntegerField()
    pr_title = serializers.CharField()
    pr_author = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    scanner_issues = serializers.SerializerMethodField()
    codebert_risk = serializers.SerializerMethodField()

    def get_scanner_issues(self, obj):
        findings = obj.raw_payload.get('scanner_findings', [])
        return {
            'total': len(findings),
            'critical': len([f for f in findings if f['severity'] == 'critical']),
            'high': len([f for f in findings if f['severity'] == 'high']),
        }

    def get_codebert_risk(self, obj):
        findings = obj.raw_payload.get('codebert_findings', [])
        if not findings:
            return None
        # return the highest risk score across all files
        return max(f['risk_score'] for f in findings)