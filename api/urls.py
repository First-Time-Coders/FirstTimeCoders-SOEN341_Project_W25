from django.urls import path
from .views import register_view, dashboard_view, login_view, logout_view, home_view, dashboard_admin_view, \
    create_channel, view_channel, messages_view, delete_channel, add_member, delete_message, dm_list_view, dm_view, \
    start_dm_view, leave_channel, request_join_channel, notification_view, approve_request, reject_request, \
    join_channel, ai_chat_view, edit_profile_view
from .views import profile_view
from . import views


urlpatterns = [
    path('register/', register_view, name='register'),
    path('create-channel/', create_channel, name='create-channel'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard-admin/', dashboard_admin_view, name='dashboard-admin'),
    path('messages/<uuid:channel_id>', messages_view, name='messages'),
    path("channel/<uuid:channel_id>/", view_channel, name="channel-detail"),
    path('ai-chat/', ai_chat_view, name='ai-chat'),
    path("", home_view, name="home"),
    path('delete-channel/<uuid:channel_id>/', delete_channel, name='delete-channel'),
    path('delete-message/<uuid:message_id>/', delete_message, name='delete-message'),
    path('add-member/<uuid:channel_id>/', add_member, name='add-member'),
    path('dm/list/', dm_list_view, name='dm_list'),
    path('dm/start/', start_dm_view, name='start_dm'),  # Moved this pattern before the generic one
    path('dm/<str:conversation_id>/', dm_view, name='dm'),
    path('leave-channel/<uuid:channel_id>/', leave_channel, name='leave-channel'),
    path('request-join-channel/<uuid:channel_id>/', request_join_channel, name='request-join-channel'),
    path('notifications/', notification_view, name='notifications'),
    path('approve-request/<uuid:request_id>/', approve_request, name='approve-request'),
    path('join-channel/<uuid:request_id>/', join_channel, name='join-channel'),
    path('reject-request/<uuid:request_id>/', reject_request, name='reject-request'),
    path('profile/', profile_view, name='profile'),  # Profile page view
    path('edit-profile/', edit_profile_view, name='edit-profile'),  # Edit profile view
    path('channel/<uuid:channel_id>/remove-user/', views.remove_user_from_channel, name='remove-user-from-channel'),
    path('channel/<uuid:channel_id>/remove-user/', views.remove_user_from_channel, name='remove-user-from-channel'),
]