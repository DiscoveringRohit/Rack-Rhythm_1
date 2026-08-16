from django.urls import path
from .views import hello_api, email_request_otp, email_verify_otp, firebase_verify
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("hello/", hello_api, name="hello_api"),
    path("auth/login/email/request-otp/", email_request_otp, name="email_request_otp"),
    path("auth/login/email/verify-otp/", email_verify_otp, name="email_verify_otp"),
    path("auth/login/mobile/firebase-verify/", firebase_verify, name="firebase_verify"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]