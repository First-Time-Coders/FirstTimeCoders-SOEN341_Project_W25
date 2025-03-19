import datetime
from http.client import responses


import bcrypt
import uuid
import supabase
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, get_user_model
from gotrue.errors import AuthApiError
from postgrest import APIError

from .decorators import supabase_login_required
from .forms import registerform
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from supabase import create_client, Client
from django.contrib.auth.hashers import make_password
import os


# Load Supabase credentials
SUPABASE_URL = "https://rsdvkupcprtchpzuxgtd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzZHZrdXBjcHJ0Y2hwenV4Z3RkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgwODEyNDIsImV4cCI6MjA1MzY1NzI0Mn0.9SQn2rXp4j6p8Em_FVhEHukZdzpYqV4lF5T8PT_gVAc"

# Initialize Supabase client
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        role = request.POST.get('role')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect('register')
        
        try:
            # Send registration request to Supabase
            response = (supabase_client.auth.sign_up({
                "email": email,
                "password": password,
                "options":{
                    "data":{
                        "username":username,
                        "role":role
                     }
                }
            }))
            user_data = response.user

            if user_data:
                user_uuid = user_data.id

                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8') #hash password
        
                supabase_client.table('users').insert({
                    "id": user_uuid,
                    "email": email,
                    "username": username,
                    "first name": first_name,
                    "last name": last_name,
                    "password": hashed,
                    "gender": gender,
                    "role": role
                }).execute()

        except AuthApiError as e:
            messages.error(request, "Failed register attempt")
            return redirect('register')

        except APIError as e:
            if "email" in str(e):  # Check for duplicate email constraint
                messages.error(request, "This email is already registered.")
            elif "username" in str(e):  # Check for duplicate username constraint
                messages.error(request, "This username is already registered.")
            else:
                messages.error(request, "A database error occurred. Please try again.")

            return redirect('register')

        return redirect('login')

    return render(request, 'api/register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST["email"]
        password = request.POST["password"]

        try:
            # Authenticate with Supabase
            response = supabase_client.auth.sign_in_with_password({"email": email, "password": password})
            user_data = response.user

            if not user_data or not response.user:
                messages.error(request, "Invalid login credentials")
                return redirect('login')

            request.session['access_token'] = response.session.access_token
            request.session['refresh_token'] = response.session.refresh_token
            request.session['user_uuid'] = user_data.id
            request.session['username'] = user_data.user_metadata.get('username', user_data.email)
            request.session['role'] = user_data.user_metadata.get('role', user_data.role)

            user_query = supabase_client.table("users").select("role").eq("email", email).single().execute()
            user_role = user_query.data["role"] if user_query.data else None


            return redirect("dashboard-admin")

        except AuthApiError as e:
            if "invalid_grant" in str(e):
                messages.error(request, "Invalid email or password.")
            else:
                messages.error(request, "Authentication failed. Please try again.")
            return redirect('login')

    return render(request, "api/login.html")

def logout_view(request):
    try:
        supabase_client.auth.sign_out()
    except AuthApiError as e:
        messages.error(request, "Failed to sign out")

    request.session.flush()  # Clear session
    return redirect('login')

def home_view(request):
    return render(request, "api/home.html")

@supabase_login_required
def dashboard_admin_view(request):
    user_role = request.session.get('role')

    try:
        user_uuid = request.session.get('user_uuid')

        user_channels_query = (
            supabase_client
            .table("channel_members")
            .select("channel_id")
            .eq("user_id", user_uuid)
            .execute()
        )

        user_channel_ids = [entry["channel_id"] for entry in
                            user_channels_query.data] if user_channels_query.data else []

        admin_channels_query = (
            supabase_client
            .table("channels")
            .select("id")
            .eq("created_by", user_uuid)
            .execute()
        )

        admin_channel_ids = [entry["id"] for entry in
                             admin_channels_query.data] if admin_channels_query.data else []


        #Fetch all general channels
        general_channels_query = (
            supabase_client
                .table("channels")
                .select("id")
                .like("name", "GENERAL-%")
                .execute()
        )

        general_channel_ids = [entry["id"] for entry in general_channels_query.data] if general_channels_query.data else []

        all_channel_ids = list(set(user_channel_ids + admin_channel_ids + general_channel_ids))

        if not all_channel_ids:
            return render(request, "api/dashboard-admin.html", {"channels": [], "user_role": user_role})  # No channels found

        channels_query = (
            supabase_client
            .table("channels")
            .select("id, name, created_by")
            .in_("id", all_channel_ids)
            .execute()
        )

        channels = channels_query.data if channels_query.data else []

        # Fetch all channels
        all_channels = supabase_client.table("channels").select("id, name, created_by").execute().data

        joinable_channels = [ch for ch in all_channels if ch["id"] not in user_channel_ids and ch["created_by"] != user_uuid]

    except APIError:
        channels = []

    return render(request, "api/dashboard-admin.html", {
        "user": request.user,
        "channels": channels,
        "user_role": user_role,
        "joinable_channels": joinable_channels
    })

@supabase_login_required
def dashboard_view(request):

    return render(request, 'api/dashboard.html', {'user': request.user})

@supabase_login_required
def create_channel(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        user_uuid = request.session['user_uuid']

        try:
            supabase_client.table('channels').insert({
                "name": name,
                "description": description,
                "created_by": user_uuid,
                "created_at": datetime.datetime.now().isoformat()
            }).execute()

            return redirect('dashboard-admin')

        except APIError as e:
            messages.error(request, "Failed to create channel")
            return redirect('create-channel')

    return render(request, 'api/create-channel.html')

@supabase_login_required
def delete_channel(request, channel_id):
    if request.method == 'POST':
        try:
            channel = supabase_client.table("channels").select("name").eq("id", channel_id).single().execute()
            if channel.data and channel.data['name'].startswith("GENERAL-"):
                messages.error(request, "General channels cannot be deleted.")
                return redirect('dashboard-admin')

            supabase_client.table('channels').delete().eq('id', channel_id).execute()
            messages.success(request, "Channel deleted successfully")
            return redirect('dashboard-admin')

        except APIError as e:
            messages.error(request, "Failed to delete channel")
            return redirect('dashboard-admin')

    return redirect('dashboard-admin')

@supabase_login_required
def view_channel(request, channel_id):
    try:
        is_member = supabase_client.table("channel_members").select("id").eq("user_id", request.session['user_uuid']).eq("channel_id", channel_id).execute()

        # Fetch the channel details
        channel_query = supabase_client.table("channels").select("name").eq("channel_id", channel_id).single().execute()
        channel = channel_query.data

        if not channel:
            return HttpResponse("Channel not found", status=404)

        # Fetch messages related to the channel
        messages_query = supabase_client.table("channel_messages").select("message, username, created_at").eq("channel_id", channel_id).order("created_at").execute()
        messages = messages_query.data if messages_query.data else []

    except APIError:
        return HttpResponse("Error fetching channel data", status=500)

    return render(request, "api/channel.html", {
        "channel": channel,
        "messages": messages,
    })

@supabase_login_required
def messages_view(request, channel_id):
    user_uuid = request.session['user_uuid']
    member_check = supabase_client.table("channel_members").select("id").eq("user_id", user_uuid).eq("channel_id", channel_id).execute()
    created_by_check = supabase_client.table("channels").select("created_by").eq("id", channel_id).single().execute()
    if not member_check.data and not created_by_check.data:
        return HttpResponse("Access Denied: You are not a member of this channel", status=403)

    if request.method == 'POST':
        content = request.POST.get('message')
        user_uuid = request.session['user_uuid']
        username = request.session['username']

        print("inserting in db")
        #create a try-catch if there's an issue
        response = supabase_client.table('channel_messages').insert({
            "user_id": user_uuid,
            "channel_id": str(channel_id),
            "message": content,
            "created_at": datetime.datetime.now().isoformat(),
            "username": username
        }).execute()

        print(response)

        return redirect('messages', channel_id=channel_id)

#used to fetch messages from a channel
    message = supabase_client.table('channel_messages').select('message, username, id').eq('channel_id', channel_id).execute()

    channel = supabase_client.table('channels').select('name').eq('id', channel_id).single().execute()
    channel_name = channel.data['name'] if channel.data else "Unknown Channel"

    context = {
        'messages': message.data,
        'channel_id': channel_id,
        'channel_name': channel_name
    }
    return render(request, "api/messages.html", context)

@supabase_login_required
def delete_message(request, message_id):
    if request.method == 'POST':
        channel_id = request.POST.get('channel_id')
        user_uuid = request.session.get('user_uuid')
        user_role = request.session.get('role')

        try:
            message_query = supabase_client.table("channel_messages").select("id", "user_id").eq("id", message_id).single().execute()
            message = message_query.data

            if not message:
                message.error(request, "Message not found")
                return redirect('messages', channel_id=channel_id)

            if user_role == 'admin' or (user_role == "member" and message["user_id"] == user_uuid):
                supabase_client.table('channel_messages').delete().eq('id', message_id).execute()
                messages.success(request, "Message deleted successfully")
            else:
                messages.error(request, "You do not have permission to delete this message.")

        except APIError as e:
            messages.error(request, "Failed to delete message")
            return redirect('messages', channel_id=channel_id)

    return redirect('messages', channel_id=request.POST.get('channel_id'))



@supabase_login_required
def add_member(request, channel_id):
    if request.method == "POST":
        username = request.POST.get("username")
        current_user_uuid = request.session['user_uuid']

        # Fetch the user_id from Supabase using the username
        user_response = supabase_client.table("users").select("id").eq("username", username).execute()

        if user_response.data is not None and len(user_response.data) > 0:
            user_id = user_response.data[0]['id']
            print(str(channel_id))
            print(request.user.id)

            # Add the user to the channel_members table
            response = supabase_client.table("channel_members").insert({
                "user_id": user_id,
                "channel_id": str(channel_id),
                "added_by": current_user_uuid
            }).execute()

            if response.data:
                return redirect("dashboard-admin")  # Redirect to dashboard
            else:
                return HttpResponse("Error adding member", status=400)
        else:
            return HttpResponse("User not found", status=404)

    return render(request, "api/add-member.html", {"channel_id": channel_id})

def leave_channel(request, channel_id):
    if request.method == 'POST':
        user_uuid = request.session['user_uuid']
        try:
            # Prevents leaving general channels
            channel = supabase_client.table("channels").select("name").eq("id", channel_id).single().execute()
            if channel.data and channel.data['name'].startswith("GENERAL-"):
                messages.error(request, "You cannot leave general channels.")
                return redirect('dashboard-admin')

            supabase_client.table("channel_members").delete().eq("user_id", user_uuid).eq("channel_id", channel_id).execute()
            messages.success(request, "You left the channel successfully.")
        except APIError:
            messages.error(request, "Error leaving the channel.")

    return redirect('dashboard-admin')

def request_join_channel(request, channel_id):
    return redirect('dashboard-admin')