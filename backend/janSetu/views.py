from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import os
import firebase_admin
from firebase_admin import auth, credentials

from .models import CustomUser, OTPRecord
from .serializers import EmailOTPRequestSerializer, EmailOTPVerifySerializer, FirebaseVerifySerializer

# Initialize Firebase Admin SDK using the new service account key
try:
    if not firebase_admin._apps:
        cred_path = os.path.join(settings.BASE_DIR, 'firebase-key.json')
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Warning: Firebase Admin not fully configured. {e}")

@api_view(["GET"])
def hello_api(request):
    return Response({"message": "Hello from Django!", "status": "success"})

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}

@api_view(['POST'])
@permission_classes([AllowAny])
def email_request_otp(request):
    serializer = EmailOTPRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp_code = str(random.randint(100000, 999999))
        OTPRecord.objects.create(email=email, otp_code=otp_code)
        
        try:
            send_mail(
                'Your Login OTP',
                f'Your verification code is {otp_code}. It expires in 10 minutes.',
                settings.EMAIL_HOST_USER,  # This will automatically use the email you set in settings.py
                [email],
                fail_silently=False,
            )
            return Response({"message": "OTP sent to email"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Failed to send email", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def email_verify_otp(request):
    serializer = EmailOTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        time_threshold = timezone.now() - timedelta(minutes=10)
        
        otp_record = OTPRecord.objects.filter(
            email=email, otp_code=otp_code, is_verified=False, created_at__gte=time_threshold
        ).last()
        
        if otp_record:
            otp_record.is_verified = True
            otp_record.save()
            user, created = CustomUser.objects.get_or_create(username=email, email=email)
            tokens = get_tokens_for_user(user)
            return Response(tokens, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def firebase_verify(request):
    serializer = FirebaseVerifySerializer(data=request.data)
    if serializer.is_valid():
        id_token = serializer.validated_data['firebase_id_token']
        try:
            decoded_token = auth.verify_id_token(id_token)
            phone_number = decoded_token.get('phone_number')
            
            if not phone_number:
                return Response({"error": "Token does not contain a phone number"}, status=status.HTTP_400_BAD_REQUEST)
                
            user, created = CustomUser.objects.get_or_create(phone_number=phone_number)
            if created:
                user.username = f"user_{phone_number.replace('+', '')}"
                user.is_phone_verified = True
                user.save()
                
            tokens = get_tokens_for_user(user)
            return Response(tokens, status=status.HTTP_200_OK)
        except Exception as e:
            # For testing without a real firebase backend setup:
            # If the token is literally the word 'test_token_success' (sent by our UI when in Mock Mode), let it through.
            if id_token == 'test_token_success':
                user, _ = CustomUser.objects.get_or_create(phone_number="+910000000000", username="user_910000000000")
                tokens = get_tokens_for_user(user)
                return Response(tokens, status=status.HTTP_200_OK)
            return Response({"error": "Invalid Firebase token", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)