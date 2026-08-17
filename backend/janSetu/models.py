from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('citizen', 'Citizen'),
        ('officer', 'Officer'),
        ('corporator', 'Corporator'),
    ]
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='citizen')
    avatar = models.URLField(max_length=500, blank=True, null=True, default='https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400&auto=format&fit=crop&q=80')
    ward = models.CharField(max_length=100, blank=True, null=True, default='Shanti Nagar')
    ward_number = models.IntegerField(blank=True, null=True, default=42)
    karma_xp = models.IntegerField(default=100)
    level = models.IntegerField(default=1)
    level_title = models.CharField(max_length=100, default='Active Citizen')
    verified_citizen = models.BooleanField(default=True)
    aadhaar_linked = models.BooleanField(default=False)
    
    # Store aggregated stats as JSON
    stats = models.JSONField(default=dict, blank=True) 
    
    # Store unlocked badges list as JSON
    badges = models.JSONField(default=list, blank=True) 

    def __str__(self):
        return self.username

class OTPRecord(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.otp_code}"

class CivicIssue(models.Model):
    CATEGORY_CHOICES = [
        ('Roads', 'Roads'),
        ('Water', 'Water'),
        ('Sanitation', 'Sanitation'),
        ('Electricity', 'Electricity'),
        ('Waste', 'Waste'),
        ('Traffic', 'Traffic'),
        ('Parks', 'Parks'),
    ]
    STATUS_CHOICES = [
        ('Reported', 'Reported'),
        ('AI Verified', 'AI Verified'),
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]
    URGENCY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Moderate', 'Moderate'),
        ('Low', 'Low'),
    ]
    
    id = models.CharField(max_length=50, primary_key=True) # Custom ID format, e.g., JS-101
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Reported')
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    
    # Nested field JSON mappings
    location = models.JSONField() # {"address": str, "ward": str, "wardNumber": int, "lat": float, "lng": float}
    reporter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reported_issues')
    images = models.JSONField() # {"reported": str, "resolved": str (optional)}
    ai_analysis = models.JSONField(blank=True, null=True) # classifier fields
    
    assigned_department = models.CharField(max_length=150, blank=True, null=True)
    assigned_officer = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks'
    )
    
    timeline = models.JSONField(default=list, blank=True) # chronological list of events
    upvotes = models.IntegerField(default=1)
    upvoted_users = models.ManyToManyField(CustomUser, related_name='upvoted_issues', blank=True)
    comments_count = models.IntegerField(default=0)
    
    verification_votes = models.JSONField(default=dict, blank=True) # {"yes": int, "no": int, "users": list}
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.title}"

class Comment(models.Model):
    issue = models.ForeignKey(CivicIssue, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} on {self.issue.id}"

class NotificationItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20) # status, upvote, ward, etc.
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    issue_id = models.CharField(max_length=50, blank=True, null=True)
    action_url = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

