from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

class SafeJWTAuthentication(JWTAuthentication):
    """Custom JWT Authentication that returns None on expired/invalid tokens 
    instead of throwing HTTP 401 exceptions for AllowAny endpoints.
    """
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, AuthenticationFailed):
            return None
