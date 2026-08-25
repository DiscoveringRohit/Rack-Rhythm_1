from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
import random
import os
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

from .models import CustomUser, OTPRecord, CivicIssue, Comment, NotificationItem, State, City, Ward, Profile
from .serializers import (
    OTPRequestSerializer, OTPVerifySerializer, CustomUserSerializer,
    CivicIssueSerializer, CommentSerializer, NotificationSerializer,
    StateSerializer, CitySerializer, WardSerializer, RegisterSerializer, LoginSerializer
)

# Helper to set refresh cookie on responses
def _set_refresh_cookie(resp: Response, refresh_token: str):
    # Secure should be True in production (requires HTTPS). Use settings.DEBUG to toggle locally.
    secure_flag = not settings.DEBUG
    # 14 days for example; align with your JWT settings
    max_age = 14 * 24 * 3600
    resp.set_cookie(
        key='janseva_refresh',
        value=refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite='Lax',
        max_age=max_age,
        path='/'
    )
    return resp

class CookieTokenObtainPairView(TokenObtainPairView):
    """Subclass the standard TokenObtainPairView to set the refresh token as an HttpOnly cookie.

    Returns JSON body: { "access": "<access_token>" }
    and sets janseva_refresh cookie with the refresh token.
    """
    def post(self, request, *args, **kwargs):
        original_response = super().post(request, *args, **kwargs)
        # original_response.data typically contains {'refresh': '...', 'access': '...'} on success
        if original_response.status_code == 200 and isinstance(original_response.data, dict):
            refresh = original_response.data.get('refresh')
            access = original_response.data.get('access')
            resp = Response({'access': access}, status=status.HTTP_200_OK)
            if refresh:
                _set_refresh_cookie(resp, refresh)
            return resp
        return original_response

@api_view(["GET"])
def hello_api(request):
    return Response({"message": "Hello from Django!", "status": "success"})

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}

def send_otp_message(channel, target, code):
    """Function to send OTP via SMS or Email"""
    if channel == 'email' or '@' in str(target):
        try:
            subject = 'JanSeva - Your Verification Code'
            message = f'Hello,\n\nYour JanSeva verification OTP is: {code}\n\nThis code will expire in 5 minutes.\n\nBest regards,\nJanSeva Team'
            html_message = f'''
            <div style="font-family: sans-serif; max-width: 500px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
                <h2 style="color: #4f46e5; margin-top: 0;">JanSeva Verification</h2>
                <p style="color: #334155;">Hello,</p>
                <p style="color: #334155;">Your verification code for JanSeva is:</p>
                <div style="background: #f1f5f9; padding: 15px; text-align: center; border-radius: 8px; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #1e293b;">
                    {code}
                </div>
                <p style="color: #64748b; font-size: 14px; margin-top: 20px;">This code will expire in 5 minutes. If you did not request this, please ignore this email.</p>
            </div>
            '''
            # Support HTTP APIs (Resend/Brevo) to bypass cloud SMTP port blocks
            resend_api_key = os.environ.get('RESEND_API_KEY')
            brevo_api_key = os.environ.get('BREVO_API_KEY') or os.environ.get('EMAIL_HOST_PASSWORD')
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER) or 'rackrhythm@gmail.com'

            # Force Brevo HTTP API if key is available
            if brevo_api_key and (brevo_api_key.startswith('xkeysib-') or brevo_api_key.startswith('xsmtpsib-')):
                import requests
                print("[EMAIL] Attempting delivery via Brevo HTTP API...")
                try:
                    resp = requests.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={
                            "api-key": brevo_api_key,
                            "Content-Type": "application/json"
                        },
                        json={
                            "sender": {"name": "JanSeva", "email": from_email},
                            "to": [{"email": target}],
                            "subject": subject,
                            "htmlContent": html_message
                        },
                        timeout=8
                    )
                    if resp.status_code in [200, 201, 202]:
                        print(f"[EMAIL SENT] Sent OTP {code} via Brevo HTTP API to {target}")
                        return True
                    else:
                        print(f"[EMAIL FAILED] Brevo API error: {resp.status_code} - {resp.text}. Falling back to SMTP...")
                except Exception as api_err:
                    print(f"[EMAIL FAILED] Brevo API exception: {api_err}. Falling back to SMTP...")

            elif resend_api_key:
                import requests
                print("[EMAIL] Attempting delivery via Resend HTTP API...")
                resp = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {resend_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": f"JanSeva <{from_email}>" if "onboarding@resend.dev" in from_email else from_email,
                        "to": [target],
                        "subject": subject,
                        "html": html_message
                    },
                    timeout=8
                )
                if resp.status_code in [200, 201, 202]:
                    print(f"[EMAIL SENT] Sent OTP {code} via Resend HTTP API to {target}")
                    return True
                else:
                    print(f"[EMAIL FAILED] Resend API error: {resp.status_code} - {resp.text}")
                    return False

            # Default: Fall back to SMTP
            print("[EMAIL] Attempting delivery via Django SMTP...")
            send_mail(
                subject,
                message,
                from_email,
                [target],
                fail_silently=False,
                html_message=html_message
            )
            print(f"[EMAIL SENT] Sent OTP {code} to {target}")
            return True
        except Exception as e:
            import traceback
            print(f"[EMAIL FAILED] Exception sending to {target}: {e}\n{traceback.format_exc()}")
            return False
    elif channel == 'sms':
        print(f"[SMS STUB] Sent OTP {code} to {target}")
        return True
    return False

@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    serializer = OTPRequestSerializer(data=request.data)
    if serializer.is_valid():
        target = serializer.validated_data['target']
        channel = serializer.validated_data['channel']
        
        if '@' in str(target):
            channel = 'email'
        
        otp_code = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timedelta(minutes=5)
        
        OTPRecord.objects.create(
            target=target,
            channel=channel,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        import threading
        threading.Thread(target=send_otp_message, args=(channel, target, otp_code), daemon=True).start()
        return Response({"status": "sent", "message": f"OTP sent via {channel}"}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    serializer = OTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        target = serializer.validated_data['target']
        otp_code = serializer.validated_data['otp_code']
        
        otp_record = OTPRecord.objects.filter(
            target=target, 
            otp_code=otp_code, 
            is_verified=False,
            expires_at__gt=timezone.now()
        ).last()
        
        if otp_record:
            otp_record.is_verified = True
            otp_record.save()
            return Response({"status": "verified", "message": "OTP verified successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "invalid_otp"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    data = serializer.validated_data
    phone = data.get('phone', '')
    email = data['email']
    public_username = data.get('public_username') or email.split('@')[0]
    full_name = data.get('full_name') or public_username
    gender = data.get('gender', '')
    role = data.get('role', 'citizen')
    department = data.get('department', '')
    state_str = data.get('state', '')
    city_str = data.get('city', '')
    pincode = data.get('pincode', '')
    
    email_verified = OTPRecord.objects.filter(target=email, is_verified=True, expires_at__gt=timezone.now() - timedelta(days=1)).exists()
    
    if not email_verified:
        return Response({"error": "Email must be verified via OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
    if CustomUser.objects.filter(username=public_username).exists():
        return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
        
    # TODO: Uncomment this phone uniqueness check for production
    # if phone and CustomUser.objects.filter(phone_number=phone).exists():
    #     return Response({"error": "Phone number already registered."}, status=status.HTTP_400_BAD_REQUEST)

    level_title = f"{department} Officer" if role == 'officer' and department else ('Officer' if role == 'officer' else 'Active Citizen')

    user = CustomUser.objects.create_user(
        username=public_username,
        email=email,
        password=data['password'],
        phone_number=phone,
        gender=gender,
        pin_code=pincode,
        state=state_str,
        city=city_str,
        is_phone_verified=False,
        role=role,
        level_title=level_title
    )
    user.stats = {
        "issuesReported": 0,
        "issuesResolved": 0,
        "upvotesGiven": 0,
        "verificationVotes": 0,
        "civicImpactScore": 10
    }
    user.badges = [{
        "id": "badge-welcome",
        "name": "Civic Pioneer",
        "icon": "🌟",
        "description": "Joined JanSeva community",
        "unlockedAt": timezone.now().isoformat()
    }]
    user.save()

    Profile.objects.create(
        user=user,
        public_username=public_username,
        full_name=full_name,
        pincode=pincode,
        is_email_verified=email_verified,
        number=phone
    )

    tokens = get_tokens_for_user(user)
    resp = Response({
        "user": CustomUserSerializer(user).data,
        "access": tokens['access']
    }, status=status.HTTP_201_CREATED)
    _set_refresh_cookie(resp, tokens['refresh'])
    return resp

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    data = serializer.validated_data
    username = data.get('username')
    phone = data.get('phone')
    password = data.get('password')
    
    from django.contrib.auth import authenticate
    user = None
    if username:
        user = authenticate(username=username, password=password)
        if not user:
            try:
                if '@' in username:
                    u = CustomUser.objects.filter(email=username).first()
                else:
                    u = CustomUser.objects.filter(Q(username=username) | Q(phone_number=username)).first()
                if u:
                    user = authenticate(username=u.username, password=password)
            except Exception:
                pass
    elif phone:
        try:
            u = CustomUser.objects.filter(phone_number=phone).first()
            if u:
                user = authenticate(username=u.username, password=password)
        except Exception:
            pass
            
    if user is not None:
        tokens = get_tokens_for_user(user)
        resp = Response({
            "user": CustomUserSerializer(user).data,
            "access": tokens['access']
        }, status=status.HTTP_200_OK)
        _set_refresh_cookie(resp, tokens['refresh'])
        return resp
    else:
        return Response({"error": "invalid_credentials"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_states(request):
    states = State.objects.all()
    return Response(StateSerializer(states, many=True).data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    state_id = request.query_params.get('state')
    cities = City.objects.all()
    if state_id:
        cities = cities.filter(state_id=state_id)
    return Response(CitySerializer(cities, many=True).data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_wards(request):
    city_id = request.query_params.get('city')
    wards = Ward.objects.all()
    if city_id:
        wards = wards.filter(city_id=city_id)
    return Response(WardSerializer(wards, many=True).data, status=status.HTTP_200_OK)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    if request.method == 'GET':
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def cookie_refresh(request):
    """Refresh access token using the HttpOnly janseva_refresh cookie.

    Returns: { "access": "<new_access>" }
    """
    refresh_token = request.COOKIES.get('janseva_refresh')
    if not refresh_token:
        return Response({"detail": "No refresh token cookie present."}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        token = RefreshToken(refresh_token)
        new_access = str(token.access_token)
        # Optionally: rotate refresh token here by issuing a new RefreshToken.for_user(user)
        return Response({"access": new_access}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """Logout endpoint: clears the HttpOnly janseva_refresh cookie on the client.

    This endpoint does not require a valid access token since its purpose is to ensure the
    cookie is removed from the browser. If you use token blacklisting, you can accept
    a refresh token and blacklist it here.
    """
    resp = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
    # Delete the cookie by name; ensure path matches how it was set
    try:
        resp.delete_cookie('janseva_refresh', path='/')
    except Exception:
        # Fallback: set an expired cookie
        resp.set_cookie('janseva_refresh', '', max_age=0, path='/')
    return resp

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def issue_list_create(request):
    if request.method == 'GET':
        category = request.query_params.get('category')
        status_param = request.query_params.get('status')
        pincode = request.query_params.get('pincode')
        
        issues = CivicIssue.objects.filter(is_hidden_from_map=False).order_by('-created_at')
        if category and category != 'all':
            issues = issues.filter(category=category)
        if status_param and status_param != 'all':
            issues = issues.filter(status=status_param)
        if pincode:
            issues = issues.filter(pin_code=pincode)
            
        serializer = CivicIssueSerializer(issues, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        data = request.data.copy()
        
        # Generate custom id like JS-101
        last_issue = CivicIssue.objects.all().order_by('-created_at').first()
        if last_issue and last_issue.id.startswith('JS-'):
            try:
                num = int(last_issue.id.split('-')[1])
                new_id = f"JS-{num + 1}"
            except ValueError:
                new_id = f"JS-{random.randint(100, 999)}"
        else:
            new_id = f"JS-101"
            
        data['id'] = new_id
        
        serializer = CivicIssueSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            issue = serializer.save(reporter=request.user)
            
            # Give user Civic Citizen XP
            request.user.civic_citizen_xp = (request.user.civic_citizen_xp or 0) + 50
            stats = request.user.stats or {}
            stats["issuesReported"] = stats.get("issuesReported", 0) + 1
            request.user.stats = stats
            request.user.save()
            
            # Send Notification
            NotificationItem.objects.create(
                user=request.user,
                title=f"Report #{issue.id} Submitted Successfully 🎉",
                message=f"Your issue \"{issue.title}\" has been AI verified and queued for municipal action.",
                notification_type="status",
                issue_id=issue.id,
                action_url=f"/issues/{issue.id}"
            )
            
            return Response(CivicIssueSerializer(issue, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def issue_detail(request, pk):
    try:
        issue = CivicIssue.objects.get(pk=pk)
    except CivicIssue.DoesNotExist:
        return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)
        
    if request.method == 'GET':
        serializer = CivicIssueSerializer(issue, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'DELETE':
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user != issue.reporter and request.user.role not in ['officer', 'corporator']:
            return Response({"error": "You do not have permission to delete this post."}, status=status.HTTP_403_FORBIDDEN)
            
        issue.delete()
        return Response({"status": "deleted"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upvote_issue(request, pk):
    try:
        issue = CivicIssue.objects.get(pk=pk)
    except CivicIssue.DoesNotExist:
        return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)
        
    if issue.upvoted_users.filter(id=request.user.id).exists():
        issue.upvoted_users.remove(request.user)
        issue.upvotes = max(0, issue.upvotes - 1)
        issue.save()
        return Response({"status": "upvote_removed", "upvotes": issue.upvotes}, status=status.HTTP_200_OK)
    else:
        issue.upvoted_users.add(request.user)
        issue.upvotes += 1
        issue.save()
        
        request.user.civic_citizen_xp = (request.user.civic_citizen_xp or 0) + 5
        stats = request.user.stats or {}
        stats["upvotesGiven"] = stats.get("upvotesGiven", 0) + 1
        request.user.stats = stats
        request.user.save()
        
        return Response({"status": "upvoted", "upvotes": issue.upvotes}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_issue(request, pk):
    try:
        issue = CivicIssue.objects.get(pk=pk)
    except CivicIssue.DoesNotExist:
        return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)
        
    vote = request.data.get('vote')
    if vote not in ["yes", "no"]:
        return Response({"error": "Invalid vote. Must be 'yes' or 'no'"}, status=status.HTTP_400_BAD_REQUEST)
        
    votes = issue.verification_votes or {"yes": 0, "no": 0, "users": {}}
    users_dict = votes.get("users", {})
    user_id_str = str(request.user.id)
    previous_vote = users_dict.get(user_id_str)
    
    if previous_vote == vote:
        return Response({"status": "no_change", "votes": votes}, status=status.HTTP_200_OK)
        
    if previous_vote == "yes":
        votes["yes"] = max(0, votes.get("yes", 0) - 1)
    elif previous_vote == "no":
        votes["no"] = max(0, votes.get("no", 0) - 1)
        
    if vote == "yes":
        votes["yes"] = votes.get("yes", 0) + 1
    elif vote == "no":
        votes["no"] = votes.get("no", 0) + 1
        
    users_dict[user_id_str] = vote
    votes["users"] = users_dict
    issue.verification_votes = votes
    
    if votes["yes"] >= 1 and issue.status == 'Pending Citizen Verification':
        issue.status = 'Verified Resolved'
        issue.is_hidden_from_map = True
        images = issue.images or {}
        if 'resolved' not in images:
            images['resolved'] = "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&auto=format&fit=crop&q=80"
            issue.images = images
        
        timeline = issue.timeline or []
        timeline.append({
            "stage": "Verified Resolved",
            "timestamp": timezone.now().isoformat(),
            "note": "Community verified the issue as resolved.",
            "actor": "Community"
        })
        issue.timeline = timeline
    
    issue.save()
    
    request.user.civic_citizen_xp = (request.user.civic_citizen_xp or 0) + 15
    stats = request.user.stats or {}
    stats["verificationVotes"] = stats.get("verificationVotes", 0) + 1
    request.user.stats = stats
    request.user.save()
    
    return Response({"status": "voted", "votes": {
        "yes": votes["yes"],
        "no": votes["no"],
        "userVoted": vote
    }, "issueStatus": issue.status}, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_issue_status(request, pk):
    if request.user.role not in ['officer', 'corporator']:
        return Response({"error": "Only officers or corporators can update issue status."}, status=status.HTTP_403_FORBIDDEN)
        
    try:
        issue = CivicIssue.objects.get(pk=pk)
    except CivicIssue.DoesNotExist:
        return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)
        
    new_status = request.data.get('status')
    note = request.data.get('note', '')
    
    if new_status not in ['Reported', 'AI Verified', 'Assigned', 'In Progress', 'Resolved', 'Pending Citizen Verification', 'Verified Resolved']:
        return Response({"error": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)
        
    # Implement Closed-Loop Resolution Logic
    if new_status == 'Resolved':
        new_status = 'Pending Citizen Verification'
        note = note or f"Officer marked as Resolved. Pending Community Verification."
        
    issue.status = new_status
    timeline = issue.timeline or []
    timeline.append({
        "stage": new_status,
        "timestamp": timezone.now().isoformat(),
        "note": note or f"Status updated to {new_status} by {request.user.get_full_name() or request.user.username}.",
        "actor": request.user.get_full_name() or request.user.username
    })
    issue.timeline = timeline
    
    if new_status == 'Verified Resolved':
        issue.is_hidden_from_map = True
        images = issue.images or {}
        if 'resolved' not in images:
            images['resolved'] = "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&auto=format&fit=crop&q=80"
            issue.images = images
            
    issue.save()
    
    NotificationItem.objects.create(
        user=issue.reporter,
        title=f"Ticket #{issue.id} Status: {new_status}",
        message=note or f"Officer {request.user.username} transitioned ticket to {new_status}.",
        notification_type="officer",
        issue_id=issue.id,
        action_url=f"/issues/{issue.id}"
    )
    
    return Response(CivicIssueSerializer(issue, context={'request': request}).data, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def comment_list_create(request, pk):
    try:
        issue = CivicIssue.objects.get(pk=pk)
    except CivicIssue.DoesNotExist:
        return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)
        
    if request.method == 'GET':
        comments = issue.comments.all().order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(issue=issue, author=request.user)
            issue.comments_count = issue.comments.count()
            issue.save()
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = request.user.notifications.all().order_by('-timestamp')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    try:
        notification = request.user.notifications.get(pk=pk)
    except NotificationItem.DoesNotExist:
        return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        
    notification.read = True
    notification.save()
    return Response({"status": "success"}, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    request.user.notifications.filter(read=False).update(read=True)
    return Response({"status": "success"}, status=status.HTTP_200_OK)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    token = request.data.get('token')
    if not token:
        return Response({"error": "No token provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request())
        
        email = idinfo.get('email')
        name = idinfo.get('name')
        avatar = idinfo.get('picture')
        
        if not email:
            return Response({"error": "Google token does not contain email"}, status=status.HTTP_400_BAD_REQUEST)
            
        user = CustomUser.objects.filter(email=email).first()
        
        if not user:
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            user = CustomUser.objects.create(
                username=username,
                email=email,
                role='citizen',
                avatar=avatar or 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400&auto=format&fit=crop&q=80',
                first_name=name.split(' ')[0] if name else '',
                last_name=' '.join(name.split(' ')[1:]) if name and ' ' in name else ''
            )
            user.set_unusable_password()
            user.save()
            
        tokens = get_tokens_for_user(user)
        
        resp = Response(tokens, status=status.HTTP_200_OK)
        resp.set_cookie(
            'janseva_refresh',
            tokens['refresh'],
            max_age=60*60*24*7, # 7 days
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            path='/'
        )
        return resp
        
    except ValueError as e:
        return Response({"error": "Invalid Google token", "details": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
