from rest_framework import serializers
from .models import CustomUser, CivicIssue, Comment, NotificationItem

class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)

class ReporterSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    isVerified = serializers.BooleanField(source='verified_citizen')
    karma = serializers.IntegerField(source='karma_xp')

    class Meta:
        model = CustomUser
        fields = ['name', 'avatar', 'isVerified', 'karma']

    def get_name(self, obj):
        full_name = obj.get_full_name().strip()
        return full_name if full_name else obj.username

class OfficerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.CharField(source='level_title')
    phone = serializers.CharField(source='phone_number')

    class Meta:
        model = CustomUser
        fields = ['name', 'role', 'avatar', 'phone']

    def get_name(self, obj):
        full_name = obj.get_full_name().strip()
        return full_name if full_name else obj.username

class CustomUserSerializer(serializers.ModelSerializer):
    stats = serializers.JSONField(read_only=True)
    badges = serializers.JSONField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'phone_number', 'role', 'avatar', 
            'ward', 'ward_number', 'karma_xp', 'level', 'level_title', 
            'verified_citizen', 'aadhaar_linked', 'stats', 'badges'
        ]

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.URLField(source='author.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'issue', 'author', 'author_name', 'author_avatar', 'text', 'created_at']
        read_only_fields = ['author']

class CivicIssueSerializer(serializers.ModelSerializer):
    reporter = ReporterSerializer(read_only=True)
    assignedOfficer = OfficerSerializer(source='assigned_officer', read_only=True)
    isUpvoted = serializers.SerializerMethodField()
    commentsCount = serializers.IntegerField(source='comments_count', read_only=True)
    verificationVotes = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = CivicIssue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'urgency',
            'location', 'reporter', 'images', 'ai_analysis', 'assigned_department',
            'assignedOfficer', 'timeline', 'upvotes', 'isUpvoted', 'commentsCount',
            'verificationVotes', 'createdAt', 'updatedAt'
        ]

    def get_isUpvoted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvoted_users.filter(id=request.user.id).exists()
        return False

    def get_verificationVotes(self, obj):
        votes = obj.verification_votes or {"yes": 0, "no": 0, "users": {}}
        yes_count = votes.get("yes", 0)
        no_count = votes.get("no", 0)
        user_voted = None
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            users_dict = votes.get("users", {})
            user_voted = users_dict.get(str(request.user.id))
            
        return {
            "yes": yes_count,
            "no": no_count,
            "userVoted": user_voted
        }

class NotificationSerializer(serializers.ModelSerializer):
    issueId = serializers.CharField(source='issue_id', required=False, allow_null=True)
    actionUrl = serializers.CharField(source='action_url', required=False, allow_null=True)

    class Meta:
        model = NotificationItem
        fields = ['id', 'title', 'message', 'notification_type', 'timestamp', 'read', 'issueId', 'actionUrl']

