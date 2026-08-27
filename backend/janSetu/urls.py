from django.urls import path
from .views import (
    hello_api, request_otp, verify_otp, register_user, user_profile, user_login,
    get_states, get_cities, get_wards,
    issue_list_create, issue_detail, upvote_issue, verify_issue, update_issue_status, assign_officer_squad,
    comment_list_create, notification_list, mark_notification_read, mark_all_notifications_read,
    CookieTokenObtainPairView, cookie_refresh, logout_view, google_login
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("hello/", hello_api, name="hello_api"),
    
    # Address lookup routes
    path("address/states/", get_states, name="get_states"),
    path("address/cities/", get_cities, name="get_cities"),
    path("address/wards/", get_wards, name="get_wards"),
    
    # Authentication routes
    path("auth/login/", user_login, name="user_login"),
    path("auth/register/", register_user, name="register_user"),
    path("auth/profile/", user_profile, name="user_profile"),
    path("auth/send-otp/", request_otp, name="request_otp"),
    path("auth/verify-otp/", verify_otp, name="verify_otp"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/refresh/cookie/", cookie_refresh, name="token_refresh_cookie"),
    path("auth/google/", google_login, name="google_login"),
    path("auth/logout/", logout_view, name="auth_logout"),
    
    # Issues routes
    path("issues/", issue_list_create, name="issue_list_create"),
    path("issues/<str:pk>/", issue_detail, name="issue_detail"),
    path("issues/<str:pk>/upvote/", upvote_issue, name="upvote_issue"),
    path("issues/<str:pk>/verify/", verify_issue, name="verify_issue"),
    path("issues/<str:pk>/status/", update_issue_status, name="update_issue_status"),
    path("issues/<str:pk>/assign/", assign_officer_squad, name="assign_officer_squad"),
    path("issues/<str:pk>/comments/", comment_list_create, name="comment_list_create"),
    
    # Notifications routes
    path("notifications/", notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", mark_all_notifications_read, name="mark_all_notifications_read"),
]