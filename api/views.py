from datetime import datetime
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
                "created_at": datetime.now().isoformat()
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
        channel_messages = messages_query.data if messages_query.data else []

    except APIError:
        return HttpResponse("Error fetching channel data", status=500)

    return render(request, "api/channel.html", {
        "channel": channel,
        "channel_messages": channel_messages,  # Renamed to avoid conflict
    })

@supabase_login_required
def messages_view(request, channel_id):
    if request.method == 'POST':
        content = request.POST.get('message')
        user_uuid = request.session['user_uuid']
        username = request.session['username']

        print("inserting in db")
        response = supabase_client.table('channel_messages').insert({
            "user_id": user_uuid,
            "channel_id": str(channel_id),
            "message": content,
            "created_at": datetime.now().isoformat(),
            "username": username
        }).execute()

        print(response)

        return redirect('messages', channel_id=channel_id)

    message_data = supabase_client.table('channel_messages').select('message, username, id').eq('channel_id', channel_id).execute()

    channel = supabase_client.table('channels').select('name').eq('id', channel_id).single().execute()
    channel_name = channel.data['name'] if channel.data else "Unknown Channel"

    context = {
        'messages': message_data.data,
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
        conversations = supabase_client.table("Conversations Table").select("id, user1_id, user2_id").or_(
            f"user1_id.eq.{user_uuid},user2_id.eq.{user_uuid}"
        ).execute()
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
        # Fetch conversation data
        conv_data = supabase_client.table("Conversations Table").select("*").eq("id", conversation_id).execute()
        
        if not conv_data.data or len(conv_data.data) == 0:
            return HttpResponse(f"No conversation found with ID: {conversation_id}. <a href='/api/dm/list/'>Back to DMs</a>")
            
        # Use first result if multiple found
        conv_record = conv_data.data[0] if isinstance(conv_data.data, list) else conv_data.data
        
        if user_uuid not in [conv_record.get('user1_id'), conv_record.get('user2_id')]:
            return HttpResponse("Not authorized to view this conversation. <a href='/api/dm/list/'>Back to DMs</a>")
            
        # Get messages
        base_messages = []
        msg_data = supabase_client.table("Messages Table").select("*").eq("conversation_id", conversation_id).execute()
        base_messages = msg_data.data if msg_data.data else []
        
        # Enrich messages with usernames
        chat_messages = []
        for message in base_messages:
            sender_id = message.get('sender_id')
            sender_query = supabase_client.table("users").select("username").eq("id", sender_id).single().execute()
            sender_name = sender_query.data.get('username', "Unknown") if sender_query.data else "Unknown"
            
            # Add username to message object for display
            message['username'] = sender_name
            chat_messages.append(message)
        
        # Get other user info
        other_user_id = conv_record.get('user2_id') if conv_record.get('user1_id') == user_uuid else conv_record.get('user1_id')
        user_data = supabase_client.table("users").select("username").eq("id", other_user_id).execute()
        other_user = user_data.data[0].get('username', "Unknown") if user_data.data else "Unknown User"
        
        # Process POST request (sending a message)
        if request.method == 'POST':
            content = request.POST.get('message')
            try:
                # Create message data with only the fields from your schema
                message_data = {
                    "conversation_id": conversation_id,
                    "sender_id": user_uuid,
                    "content": content,
                    "created_at": datetime.now().isoformat(),
                    "is_read": False
                }
                
                # Insert with only the fields that exist in the database
                supabase_client.table('Messages Table').insert(message_data).execute()
                return redirect('dm', conversation_id=conversation_id)
            except Exception as send_error:
                print(f"DEBUG: Error sending message: {str(send_error)}")
                return HttpResponse(f"Failed to send message: {str(send_error)}")
        
        return render(request, "api/dm.html", {
            "conversation_id": conversation_id,
            "chat_messages": chat_messages,
            "other_user": other_user
        })
            
    except Exception as e:
        print(f"DEBUG: Exception in dm_view: {str(e)}")
        return HttpResponse(f"Error: {str(e)}. <a href='/api/dm/list/'>Back to DMs</a>")

@supabase_login_required
def start_dm_view(request):
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        user_uuid = request.session['user_uuid']
        print(f"DEBUG: Starting DM process - Recipient Email: {recipient_email}, User UUID: {user_uuid}")
        
        try:
            print(f"DEBUG: Querying users table for {recipient_email}")
            recipient = supabase_client.table("users").select("id").eq("email", recipient_email).single().execute()
            print(f"DEBUG: Recipient Query Result: {recipient.data}")
            if not recipient.data:
                messages.error(request, "User not found")
                print(f"DEBUG: User not found for email: {recipient_email}")
                return redirect('start_dm')
            recipient_id = recipient.data['id']
            print(f"DEBUG: Recipient ID: {recipient_id}")
            if recipient_id == user_uuid:
                messages.error(request, "You cannot DM yourself")
                print(f"DEBUG: Self-DM attempt detected")
                return redirect('start_dm')
            
            print(f"DEBUG: Querying Conversations Table for users {user_uuid} and {recipient_id}")
            conv_query = supabase_client.table("Conversations Table").select("id").or_(
                f"and(user1_id.eq.{user_uuid},user2_id.eq.{recipient_id}),and(user1_id.eq.{recipient_id},user2_id.eq.{user_uuid})"
            ).execute()
            print(f"DEBUG: Conversation Query Result: {conv_query.data}")
            
            # Check if a conversation exists
            if conv_query.data and len(conv_query.data) > 0:
                conversation_id = conv_query.data[0]['id']
                print(f"DEBUG: Found existing Conversation ID: {conversation_id}")
                return redirect('dm', conversation_id=conversation_id)
            
            # If no conversation exists, create a new one
            print(f"DEBUG: Creating new conversation with user1_id: {user_uuid}, user2_id: {recipient_id}")
            new_conv = supabase_client.table("Conversations Table").insert({
                "user1_id": user_uuid,
                "user2_id": recipient_id,
                "created_at": datetime.now().isoformat()
            }).execute()
            print(f"DEBUG: New Conversation Result: {new_conv.data}")
            if not new_conv.data or len(new_conv.data) == 0:
                raise APIError("No data returned from conversation insert")
            conversation_id = new_conv.data[0]['id']
            print(f"DEBUG: New Conversation ID: {conversation_id}")
            return redirect('dm', conversation_id=conversation_id)
        
        except APIError as e:
            print(f"DEBUG: APIError occurred: {str(e)} - Full error details: {e}")
            messages.error(request, f"Failed to start DM: {str(e)}")
            return redirect('start_dm')
        except Exception as e:
            print(f"DEBUG: Unexpected error: {str(e)}")
            messages.error(request, f"Unexpected error: {str(e)}")
            return redirect('start_dm')
    return render(request, "api/start_dm.html")