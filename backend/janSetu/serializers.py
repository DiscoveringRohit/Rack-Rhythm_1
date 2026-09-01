from rest_framework import serializers
from .models import CustomUser, CivicIssue, Comment, NotificationItem, State, City, Ward, Profile, OTPRecord

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'state']

class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ['id', 'name', 'ward_number', 'city', 'pincode']

class ProfileSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Profile
        fields = ['public_username', 'full_name', 'state', 'state_name', 'city', 'city_name', 'pincode', 'is_email_verified', 'number']

class CustomUserSerializer(serializers.ModelSerializer):
    stats = serializers.JSONField(read_only=True)
    badges = serializers.JSONField(read_only=True)
    profile = ProfileSerializer(read_only=True)
    ward_details = WardSerializer(source='ward', read_only=True)
    civicCitizenXP = serializers.IntegerField(source='civic_citizen_xp', read_only=True)
    levelTitle = serializers.CharField(source='level_title', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'phone_number', 'role', 'avatar', 
            'ward', 'ward_details', 'civic_citizen_xp', 'civicCitizenXP', 'level', 'level_title', 'levelTitle',
            'verified_citizen', 'aadhaar_linked', 'stats', 'badges', 'profile',
            'gender', 'pin_code', 'state', 'city'
        ]

class OTPRequestSerializer(serializers.Serializer):
    target = serializers.CharField(max_length=255)
    channel = serializers.ChoiceField(choices=['email', 'sms'])

class OTPVerifySerializer(serializers.Serializer):
    target = serializers.CharField(max_length=255)
    otp_code = serializers.CharField(max_length=6)

class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    public_username = serializers.CharField(max_length=150, required=False)
    full_name = serializers.CharField(max_length=255, required=False)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    role = serializers.CharField(max_length=15, required=False, default='citizen')
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    pincode = serializers.CharField(max_length=10, required=False, allow_blank=True)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    identifier = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

class ReporterSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    isVerified = serializers.BooleanField(source='verified_citizen')
    karma = serializers.IntegerField(source='civic_citizen_xp')

    class Meta:
        model = CustomUser
        fields = ['name', 'avatar', 'isVerified', 'karma']

    def get_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile.full_name:
            return obj.profile.full_name
        return obj.username

class OfficerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.CharField(source='level_title')
    phone = serializers.CharField(source='phone_number')

    class Meta:
        model = CustomUser
        fields = ['name', 'role', 'avatar', 'phone']

    def get_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile.full_name:
            return obj.profile.full_name
        return obj.username

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.URLField(source='author.avatar', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    is_officer = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'issue', 'author', 'author_name', 'author_username', 'author_avatar', 'author_role', 'is_officer', 'text', 'created_at', 'timestamp']
        read_only_fields = ['author', 'issue', 'created_at', 'timestamp']

    def get_author_name(self, obj):
        if obj.author:
            if hasattr(obj.author, 'profile') and obj.author.profile.full_name:
                return obj.author.profile.full_name
            full_name = obj.author.get_full_name()
            return full_name if full_name.strip() else obj.author.username
        return "Citizen"

    def get_is_officer(self, obj):
        return bool(obj.author and obj.author.role in ['officer', 'corporator'])

class CivicIssueSerializer(serializers.ModelSerializer):
    reporter = ReporterSerializer(read_only=True)
    assignedOfficer = OfficerSerializer(source='assigned_officer', read_only=True)
    isUpvoted = serializers.SerializerMethodField()
    commentsCount = serializers.IntegerField(source='comments_count', read_only=True)
    verificationVotes = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    aiAnalysis = serializers.JSONField(source='ai_analysis', required=False, allow_null=True)
    assignedDepartment = serializers.CharField(source='assigned_department', required=False, allow_blank=True, allow_null=True)
    timesReported = serializers.IntegerField(source='times_reported', required=False, default=1)
    mergedTicketIds = serializers.JSONField(source='merged_ticket_ids', required=False, default=list)
    pincode = serializers.CharField(source='pin_code', read_only=True)

    class Meta:
        model = CivicIssue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'urgency',
            'location', 'pin_code', 'pincode', 'reporter', 'images', 'aiAnalysis', 'assignedDepartment',
            'assignedOfficer', 'timeline', 'upvotes', 'isUpvoted', 'commentsCount',
            'verificationVotes', 'is_hidden_from_map', 'times_reported', 'timesReported',
            'merged_ticket_ids', 'mergedTicketIds', 'createdAt', 'updatedAt'
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
