from django.urls import path
from .views import register_view, dashboard_view, login_view, logout_view, home_view, dashboard_admin_view, create_channel, view_channel

urlpatterns = [
    path('register/', register_view, name='register'),
    path('create-channel/', create_channel, name='create-channel'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard-admin/', dashboard_admin_view, name='dashboard-admin'),
    path("channel/<uuid:channel_id>/", view_channel, name="channel-detail"),
    path("", home_view, name="home"),

]