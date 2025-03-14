import datetime
from http.client import responses
from msilib.schema import CustomAction

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

from postgrest import APIError

from django.contrib.auth.hashers import make_password
import os


# Load Supabase credentials
SUPABASE_URL = "https://rsdvkupcprtchpzuxgtd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzZHZrdXBjcHJ0Y2hwenV4Z3RkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgwODEyNDIsImV4cCI6MjA1MzY1NzI0Mn0.9SQn2rXp4j6p8Em_FVhEHukZdzpYqV4lF5T8PT_gVAc"

# Initialize Supabase client
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def supabase_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'user_uuid' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

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
            response = supabase_client.auth.sign_up({"email": email, "password": password, "options":{"data":{"username":username}}})
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
                    "role": role}).execute()

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

            user_query = supabase_client.table("users").select("role").eq("email", email).single().execute()
            user_role = user_query.data["role"] if user_query.data else None

            if user_role == "admin":
               return redirect("dashboard-admin")
            else:
                return redirect("dashboard")

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
    try:
        channels_query = supabase_client.table("channels").select("id, name").execute()
        channels = channels_query.data if channels_query.data else []
    except APIError:
        channels = []

    return render(request, "api/dashboard-admin.html", {"user": request.user, "channels": channels})

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

        try:
            supabase_client.table('channel_messages').delete().eq('id', message_id).execute()
            messages.success(request, "Message deleted successfully")
            return redirect('messages', channel_id=request.POST.get('channel_id'))
        except APIError as e:
            messages.error(request, "Failed to delete message")
            return redirect('messages', channel_id=channel_id)

    return redirect('messages', channel_id=request.POST.get('channel_id'))

@supabase_login_required
def dm_list_view(request):
    user_uuid = request.session['user_uuid']
    try:
        # Fetch conversations where the user is either user1 or user2
        conversations = supabase_client.table("Conversations").select("id, user1_id, user2_id").or_(f"user1_id.eq.{user_uuid},user2_id.eq.{user_uuid}").execute()
        dm_list = []
        for conv in conversations.data:
            other_user_id = conv['user2_id'] if conv['user1_id'] == user_uuid else conv['user1_id']
            user_query = supabase_client.table("users").select("username").eq("id", other_user_id).single().execute()
            dm_list.append({
                "conversation_id": conv['id'],
                "other_user": user_query.data['username'] if user_query.data else "Unknown"
            })
    except APIError as e:
        messages.error(request, "Failed to load DMs")
        dm_list = []
    
    return render(request, "api/dm_list.html", {"dm_list": dm_list})

@supabase_login_required
def dm_view(request, conversation_id):
    user_uuid = request.session['user_uuid']
    try:
        # Verify user is part of this conversation
        conv_query = supabase_client.table("Conversations").select("user1_id, user2_id").eq("id", conversation_id).single().execute()
        if not conv_query.data or (user_uuid not in [conv_query.data['user1_id'], conv_query.data['user2_id']]):
            return HttpResponse("Unauthorized or conversation not found", status=403)

        # Fetch messages, including is_read status
        messages_query = supabase_client.table("Messages").select("id, content, username, created_at, is_read").eq("conversation_id", conversation_id).order("created_at").execute()
        messages = messages_query.data if messages_query.data else []

        # Get other user's username
        other_user_id = conv_query.data['user2_id'] if conv_query.data['user1_id'] == user_uuid else conv_query.data['user1_id']
        other_user = supabase_client.table("users").select("username").eq("id", other_user_id).single().execute().data['username']

        if request.method == 'POST':
            content = request.POST.get('message')
            try:
                supabase_client.table('Messages').insert({
                    "conversation_id": str(conversation_id),
                    "sender_id": user_uuid,
                    "content": content,
                    "created_at": datetime.datetime.now().isoformat(),
                    "username": request.session['username'],
                    "is_read": False  # Default to unread
                }).execute()
                return redirect('dm', conversation_id=conversation_id)
            except APIError as e:
                messages.error(request, "Failed to send message")

    except APIError as e:
        messages.error(request, "Failed to load conversation")
        return redirect('dm_list')

    return render(request, "api/dm.html", {
        "conversation_id": conversation_id,
        "messages": messages,
        "other_user": other_user
    })

@supabase_login_required
def start_dm_view(request):
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        user_uuid = request.session['user_uuid']
        print(f"Recipient Email: {recipient_email}, User UUID: {user_uuid}")  # Debug: Check form data and user

        try:
            # Find recipient by email
            recipient = supabase_client.table("users").select("id").eq("email", recipient_email).single().execute()
            print(f"Recipient Query Result: {recipient.data}")  # Debug: Check if recipient is found
            if not recipient.data:
                messages.error(request, "User not found")
                return redirect('start_dm')
            
            recipient_id = recipient.data['id']
            print(f"Recipient ID: {recipient_id}")  # Debug: Check recipient ID
            if recipient_id == user_uuid:
                messages.error(request, "You cannot DM yourself")
                return redirect('start_dm')

            # Check if conversation already exists
            conv_query = supabase_client.table("Conversations").select("id").or_(f"user1_id.eq.{user_uuid},user2_id.eq.{recipient_id}", f"user1_id.eq.{recipient_id},user2_id.eq.{user_uuid}").single().execute()
            print(f"Conversation Query Result: {conv_query.data}")  # Debug: Check if conversation exists
            if conv_query.data:
                conversation_id = conv_query.data['id']
                print(f"Existing Conversation ID: {conversation_id}")  # Debug: Check existing conversation ID
                return redirect('dm', conversation_id=conversation_id)

            # Create new conversation
            new_conv = supabase_client.table("Conversations").insert({
                "user1_id": user_uuid,
                "user2_id": recipient_id,
                "created_at": datetime.datetime.now().isoformat()
            }).execute()
            print(f"New Conversation Result: {new_conv.data}")  # Debug: Check new conversation data
            conversation_id = new_conv.data[0]['id']
            print(f"New Conversation ID: {conversation_id}")  # Debug: Check new conversation ID
            return redirect('dm', conversation_id=conversation_id)

        except APIError as e:
            print(f"APIError: {str(e)}")  # Debug: Log the error
            messages.error(request, "Failed to start DM")
            return redirect('start_dm')

    return render(request, "api/start_dm.html")
