from django.urls import path
from .views import register_view, dashboard_view, login_view, logout_view, home_view, dashboard_admin_view, \
    create_channel, view_channel, messages_view, delete_channel, delete_message, dm_list_view, dm_view, start_dm_view

urlpatterns = [
    path('register/', register_view, name='register'),
    path('create-channel/', create_channel, name='create-channel'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard-admin/', dashboard_admin_view, name='dashboard-admin'),
    path('messages/<uuid:channel_id>', messages_view, name='messages'),
    path("channel/<uuid:channel_id>/", view_channel, name="channel-detail"),
    path("", home_view, name="home"),
    path('delete-channel/<uuid:channel_id>/', delete_channel, name='delete-channel'),
    path('delete-message/<uuid:message_id>/', delete_message, name='delete-message'),
    path('dm/list/', dm_list_view, name='dm_list'),
    path('dm/start/', start_dm_view, name='start_dm'),  # Moved this pattern before the generic one
    path('dm/<str:conversation_id>/', dm_view, name='dm'),
]