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

from .models import CustomUser, OTPRecord
from .serializers import OTPRequestSerializer, OTPVerifySerializer

@api_view(["GET"])
def hello_api(request):
    return Response({"message": "Hello from Django!", "status": "success"})

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}

@api_view(['POST'])
@permission_classes([AllowAny])
def email_request_otp(request):
    serializer = OTPRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        phone_number = serializer.validated_data['phone_number']
        
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
    serializer = OTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']
        time_threshold = timezone.now() - timedelta(minutes=10)
        
        otp_record = OTPRecord.objects.filter(
            email=email, otp_code=otp_code, is_verified=False, created_at__gte=time_threshold
        ).last()
        
        if otp_record:
            otp_record.is_verified = True
            otp_record.save()
            
            # Create user if they don't exist, otherwise get them by email
            user, created = CustomUser.objects.get_or_create(username=email, defaults={'email': email, 'phone_number': phone_number})
            
            # If user existed but phone number changed, update it as per user's request
            if not created and user.phone_number != phone_number:
                user.phone_number = phone_number
                user.save()
                
            tokens = get_tokens_for_user(user)
            return Response(tokens, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)