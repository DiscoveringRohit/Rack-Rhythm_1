from django.urls import path
from .views import (
    hello_api, health_check, request_otp, verify_otp, register_user, user_profile, user_login,
    get_states, get_cities, get_wards,
    issue_list_create, issue_detail, upvote_issue, verify_issue, update_issue_status, assign_officer_squad,
    comment_list_create, comment_detail, notification_list, mark_notification_read, mark_all_notifications_read,
    cookie_refresh, logout_view, google_login, merge_duplicate_issues, leaderboard_list,
    announcement_list_create, announcement_detail
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("hello/", hello_api, name="hello_api"),
    path("health/", health_check, name="health_check"),
    path("leaderboard/", leaderboard_list, name="leaderboard_list"),
    path("auth/leaderboard/", leaderboard_list, name="auth_leaderboard_list"),
    
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
    path("issues/merge/", merge_duplicate_issues, name="merge_duplicate_issues"),
    path("issues/duplicates/merge/", merge_duplicate_issues, name="merge_duplicate_issues_alias"),
    path("issues/<str:pk>/", issue_detail, name="issue_detail"),
    path("issues/<str:pk>/upvote/", upvote_issue, name="upvote_issue"),
    path("issues/<str:pk>/verify/", verify_issue, name="verify_issue"),
    path("issues/<str:pk>/status/", update_issue_status, name="update_issue_status"),
    path("issues/<str:pk>/assign/", assign_officer_squad, name="assign_officer_squad"),
    path("issues/<str:pk>/comments/", comment_list_create, name="comment_list_create"),
    path("comments/<int:pk>/", comment_detail, name="comment_detail"),
    
    # Notifications routes
    path("notifications/", notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", mark_all_notifications_read, name="mark_all_notifications_read"),

    # Announcements routes (Hyperlocal PIN targeted broadcasts)
    path("announcements/", announcement_list_create, name="announcements"),
    path("announcements/<int:pk>/", announcement_detail, name="announcement_detail"),
]