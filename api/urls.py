from django.urls import path
from . import views
from .views import profile_view
from .views import edit_profile_view
from .views import register_view, dashboard_view, login_view, logout_view, home_view, dashboard_admin_view, \
    create_channel, view_channel, messages_view, delete_channel

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
    path('profile/', profile_view, name='profile'),  # Profile page view
    path('edit-profile/', edit_profile_view, name='edit-profile'),  # Edit profile view
    path('profile/', views.profile_view, name='profile'),
    ]