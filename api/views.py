import datetime
from http.client import responses
import openai
from django.conf import settings

#test pipeline3

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

from dotenv import load_dotenv
import os

# Load Supabase credentials
SUPABASE_URL = "https://rsdvkupcprtchpzuxgtd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzZHZrdXBjcHJ0Y2hwenV4Z3RkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgwODEyNDIsImV4cCI6MjA1MzY1NzI0Mn0.9SQn2rXp4j6p8Em_FVhEHukZdzpYqV4lF5T8PT_gVAc"

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
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
        user_id = request.session.get('user_uuid')

        if user_id:
            supabase_client.from_("user_activity").update({"status": "offline"}).eq("user_id", user_id).execute()

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

        users_query = supabase_client.table("users").select("id, username").neq("id", user_uuid).execute()
        users = users_query.data if users_query.data else []

        if not all_channel_ids:
            return render(request, "api/dashboard-admin.html", {"channels": [], "user_role": user_role, "users": users})  # No channels found

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
        joinable_channels = [ch for ch in all_channels if ch["id"] not in user_channel_ids and ch["created_by"] != user_uuid and not( ch["name"].startswith("GENERAL-"))]

        pending_requests = supabase_client.table("channels_requests") \
            .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
            .in_("channel_id", admin_channel_ids) \
            .eq("status", "pending") \
            .execute().data

        # Get join channel requests sent from an admin:
        admin_requests = supabase_client.table("channels_requests") \
            .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
            .eq("member_id", user_uuid) \
            .eq("status", "admin_request") \
            .execute().data

    except APIError:
        channels = []
        users = []

    return render(request, "api/dashboard-admin.html", {
        "user_id": user_uuid,
        "channels": channels,
        "user_role": user_role,
        "users": users,
        "joinable_channels": joinable_channels,
        "pending_requests": pending_requests,
        "admin_requests": admin_requests
    })

def notification_view(request):
    try:
        user_uuid = request.session.get('user_uuid')

        # Fetch channels created by admin:
        admin_channels = supabase_client.table("channels").select("id").eq("created_by", user_uuid).execute().data
        admin_channel_ids = [c["id"] for c in admin_channels]

        # Get pending requests directed to the creator:
        pending_requests = supabase_client.table("channels_requests") \
            .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
            .in_("channel_id", admin_channel_ids) \
            .eq("status", "pending") \
            .execute().data

        # Get join channel requests sent from an admin:
        admin_requests = supabase_client.table("channels_requests") \
            .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
            .eq("member_id", user_uuid) \
            .eq("status", "admin_request") \
            .execute().data

        return render(request, "api/notifications.html", {
            "user": request.user,
            "pending_requests": pending_requests,
            "admin_requests": admin_requests
        })

    except APIError:
        channels = []

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
            response = supabase_client.table('channels').insert({
                "name": name,
                "description": description,
                "created_by": user_uuid,
                "created_at": datetime.now().isoformat()
            }).execute()

            if response.data:
                messages.success(request, "Channel created successfully!")
                return redirect('dashboard-admin')

        except APIError as e:
            messages.error(request, "Failed to create channel")
            return redirect('dashboard-admin')

    return redirect('dashboard-admin')

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

    if not user_uuid:
        return HttpResponse("Unauthorized: Please log in.", status=401)

    try:
        member_check = supabase_client.table("channel_members").select("id").eq("user_id", user_uuid).eq("channel_id", channel_id).execute()
        created_by_check = supabase_client.table("channels").select("created_by").eq("id", channel_id).single().execute()

        if not member_check.data and not created_by_check.data:
            return HttpResponse("Access Denied: You are not a member of this channel", status=403)

        user_channels_query = supabase_client.table("channel_members").select("channel_id").eq("user_id",user_uuid).execute()
        user_channel_ids = [entry["channel_id"] for entry in user_channels_query.data] if user_channels_query.data else []

        admin_channels_query = supabase_client.table("channels").select("id").eq("created_by", user_uuid).execute()
        admin_channel_ids = [entry["id"] for entry in admin_channels_query.data] if admin_channels_query.data else []

        general_channels_query = supabase_client.table("channels").select("id").like("name", "GENERAL-%").execute()
        general_channel_ids = [entry["id"] for entry in general_channels_query.data] if general_channels_query.data else []

        all_channel_ids = list(set(user_channel_ids + admin_channel_ids + general_channel_ids))

        channels_query = supabase_client.table("channels").select("id, name, created_by").in_("id",all_channel_ids).execute()
        channels = channels_query.data if channels_query.data else []

        channel_query = supabase_client.table('channels').select('name').eq('id', channel_id).single().execute()
        channel_name = channel_query.data['name'] if channel_query.data else "Unknown Channel"

        message_query = supabase_client.table('channel_messages').select('*').eq('channel_id', channel_id).execute()
        messages = message_query.data if message_query.data else []

        users = supabase_client.table("channel_members").select("user_id").eq("channel_id", channel_id).execute()
        user_ids = [user["user_id"] for user in users.data]
        channel_data = supabase_client.table("channels").select("created_by").eq("id", channel_id).single().execute()
        creator_id = channel_data.data["created_by"]
        user_ids.append(creator_id)
        members = supabase_client.table("users").select("id, username").in_("id", user_ids).execute()
        channel_members = [{"user_id": member["id"], "username": member["username"]} for member in members.data]

        print("DEBUG: Channel Members:", channel_members)

        chat_messages = []
        for message in messages:
            sender_id = message.get('user_id')
            sender_query = supabase_client.table("users").select("username").eq("id", sender_id).single().execute()
            sender_name = sender_query.data.get('username', "Unknown") if sender_query.data else "Unknown"
            message['username'] = sender_name
            chat_messages.append(message)


        if request.method == 'POST':
            content = request.POST.get('message')
            quoted_message_id = request.POST.get('quoted_message_id')
            quoted_author = request.POST.get('quoted_author')
            quoted_content = request.POST.get('quoted_content')

            try:
                message_data = {
                    "channel_id": str(channel_id),
                    "user_id": user_uuid,
                    "message": content,
                    "created_at": datetime.now().isoformat(),
                    "username": request.session.get('username'),
                }

                if quoted_message_id:
                    message_data = {
                        "quoted_message_id": quoted_message_id,
                        "quoted_author": quoted_author,
                        "quoted_content": quoted_content
                    }

                supabase_client.table('channel_messages').insert({
                    "channel_id": str(channel_id),
                    "user_id": user_uuid,
                    "message": content,
                    "created_at": datetime.now().isoformat(),
                    "quoted_message_id": quoted_message_id,
                    "quoted_author": quoted_author,
                    "quoted_content": quoted_content
                }).execute()
                return redirect('messages', channel_id=channel_id)

            except Exception as send_error:
                print(f"DEBUG: Error sending message: {str(send_error)}")
                return HttpResponse(f"Failed to send message: {str(send_error)}")

        context = {
            'messages': chat_messages,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'channels': channels,
            'user_role': request.session.get('role'),
            'channel_members': channel_members,
            'user_id': user_uuid,
        }
        return render(request, "api/messages.html", context)

    except Exception as e:
        print(f"DEBUG: Exception in messages_view: {str(e)}")
        return HttpResponse(f"Error: {str(e)}. <a href='/api/dashboard-admin/'>Back to Dashboard</a>")


@supabase_login_required
def delete_message(request, message_id):
    if request.method == 'POST':
        message_type = request.POST.get('message_type')
        user_uuid = request.session.get('user_uuid')
        user_role = request.session.get('role')

        print("DEBUG: conversation_id:", request.POST.get('conversation_id'), "channel_id:", request.POST.get('channel_id'))

        try:
            if message_type == "channel":
                channel_id = request.POST.get('channel_id')
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

                return redirect('messages', channel_id=request.POST.get('channel_id'))

            elif message_type == "dm":
                conversation_id = request.POST.get('conversation_id')
                message_query = supabase_client.table("Messages Table").select("id", "sender_id").eq("id", message_id).single().execute()
                message = message_query.data

                if not message:
                    messages.error(request, "Message not found")
                    return redirect('dm', conversation_id=conversation_id)

                if user_role == 'admin' or (user_role == "member" and message["sender_id"] == user_uuid):
                    supabase_client.table('Messages Table').delete().eq('id', message_id).execute()
                    messages.success(request, "Message deleted successfully")
                else:
                    messages.error(request, "You do not have permission to delete this message.")

                return redirect('dm', conversation_id=request.POST.get('conversation_id'))

            else:
                messages.error(request, "Invalid message type.")
                return redirect('dashboard-admin')  # fallback redirect

        except APIError as e:
            messages.error(request, "Failed to delete message")
            if message_type == 'channel':
                return redirect('messages', channel_id=request.POST.get('channel_id'))
            elif message_type == 'dm':
                return redirect('dm', conversation_id=request.POST.get('conversation_id'))

    return redirect('dashboard-admin')

@supabase_login_required
def dm_list_view(request):
    user_uuid = request.session['user_uuid']

    # Fetch channels created by admin:
    admin_channels = supabase_client.table("channels").select("id").eq("created_by", user_uuid).execute().data
    admin_channel_ids = [c["id"] for c in admin_channels]

    # Get pending requests directed to the creator:
    pending_requests = supabase_client.table("channels_requests") \
        .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
        .in_("channel_id", admin_channel_ids) \
        .eq("status", "pending") \
        .execute().data

    # Get join channel requests sent from an admin:
    admin_requests = supabase_client.table("channels_requests") \
        .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
        .eq("member_id", user_uuid) \
        .eq("status", "admin_request") \
        .execute().data
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

    return render(request, "api/dm_list.html", {
        "dm_list": dm_list,
        "pending_requests": pending_requests,
        "admin_requests": admin_requests})

@supabase_login_required
def dm_view(request, conversation_id):
    user_uuid = request.session['user_uuid']

    # Fetch channels created by admin:
    admin_channels = supabase_client.table("channels").select("id").eq("created_by", user_uuid).execute().data
    admin_channel_ids = [c["id"] for c in admin_channels]

    # Get pending requests directed to the creator:
    pending_requests = supabase_client.table("channels_requests") \
        .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
        .in_("channel_id", admin_channel_ids) \
        .eq("status", "pending") \
        .execute().data

    # Get join channel requests sent from an admin:
    admin_requests = supabase_client.table("channels_requests") \
        .select("id, channel_id, user_id, requested_at, status, user:user_id(username), channel:channel_id(name)") \
        .eq("member_id", user_uuid) \
        .eq("status", "admin_request") \
        .execute().data

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
            quoted_message_id = request.POST.get('quoted_message_id')
            quoted_author = request.POST.get('quoted_author')
            quoted_content = request.POST.get('quoted_content')

            try:
                # Create message data with quote information if present
                message_data = {
                    "conversation_id": conversation_id,
                    "sender_id": user_uuid,
                    "content": content,
                    "created_at": datetime.now().isoformat(),
                    "is_read": False
                }

                # Add quote data if replying to a message
                if quoted_message_id:
                    message_data["quoted_message_id"] = quoted_message_id
                    message_data["quoted_author"] = quoted_author
                    message_data["quoted_content"] = quoted_content

                # Insert with the fields that exist in the database
                supabase_client.table('Messages Table').insert(message_data).execute()
                return redirect('dm', conversation_id=conversation_id)
            except Exception as send_error:
                print(f"DEBUG: Error sending message: {str(send_error)}")
                return HttpResponse(f"Failed to send message: {str(send_error)}")

        return render(request, "api/dm.html", {
            "conversation_id": conversation_id,
            "chat_messages": chat_messages,
            "other_user": other_user,
            "dm_list": dm_list,
            "pending_requests": pending_requests,
            "admin_requests": admin_requests
        })

    except Exception as e:
        print(f"DEBUG: Exception in dm_view: {str(e)}")
        return HttpResponse(f"Error: {str(e)}. <a href='/api/dm/list/'>Back to DMs</a>")

@supabase_login_required
def start_dm_view(request):
    if request.method == 'POST':
        recipient_username = request.POST.get('recipient_username')
        user_uuid = request.session['user_uuid']
        print(f"DEBUG: Starting DM process - Recipient Email: {recipient_username}, User UUID: {user_uuid}")

        try:
            print(f"DEBUG: Querying users table for {recipient_username}")
            recipient = supabase_client.table("users").select("id").eq("username", recipient_username).single().execute()
            print(f"DEBUG: Recipient Query Result: {recipient.data}")
            if not recipient.data:
                messages.error(request, "User not found")
                print(f"DEBUG: User not found for email: {recipient_username}")
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

@supabase_login_required
# views.py
def add_member(request, channel_id):
    if request.method == "POST":
        username = request.POST.get("username")
        current_user_uuid = request.session.get('user_uuid')

        # Fetch user_id from Supabase using the provided username
        user_response = supabase_client.table("users").select("id").eq("username", username).execute()

        if user_response.data and len(user_response.data) > 0:
            user_id = user_response.data[0]['id']

            # Send a request to that user
            response = supabase_client.table("channels_requests").insert({
                "user_id": current_user_uuid,
                "member_id": user_id,
                "channel_id": str(channel_id),
                "status": "admin_request"
            }).execute()

    return redirect('dashboard-admin')

def leave_channel(request, channel_id):
    if request.method == 'POST':
        user_uuid = request.session['user_uuid']
        try:
            # Prevents leaving general channels
            channel = supabase_client.table("channels").select("name").eq("id", channel_id).single().execute()
            if channel.data and channel.data['name'].startswith("GENERAL-"):
                return redirect('dashboard-admin')

            supabase_client.table("channel_members").delete().eq("user_id", user_uuid).eq("channel_id", channel_id).execute()
        except APIError:
            messages.error(request, "Error leaving the channel.")

    return redirect('dashboard-admin')

def request_join_channel(request, channel_id):
    if request.method == 'POST':
        user_uuid = request.session['user_uuid']

        supabase_client.table("channels_requests").insert({
            "user_id": user_uuid,
            "channel_id": str(channel_id),
            "status": "pending",
        }).execute()
    return redirect('dashboard-admin')

def approve_request(request, request_id):
    # Automatically add user to channel_members
    user_uuid = request.session['user_uuid']
    req = supabase_client.table("channels_requests").select("channel_id, user_id").eq("id", str(request_id)).single().execute().data
    supabase_client.table("channel_members").insert({
        "channel_id": req["channel_id"],
        "user_id": req["user_id"],
        "added_by": user_uuid
    }).execute()
    supabase_client.table("channels_requests").delete().eq("id", str(request_id)).execute()
    return redirect('notifications')

def join_channel(request, request_id):
    # Automatically add user to channel_members
    admin_id = request.session['user_uuid']
    req = supabase_client.table("channels_requests").select("channel_id, member_id").eq("id", str(request_id)).single().execute().data
    supabase_client.table("channel_members").insert({
        "channel_id": req["channel_id"],
        "user_id": req["member_id"],
        "added_by": admin_id
    }).execute()
    supabase_client.table("channels_requests").delete().eq("id", str(request_id)).execute()
    return redirect('notifications')

def reject_request(request, request_id):
    supabase_client.table("channels_requests").delete().eq("id", str(request_id)).execute()
    return redirect('notifications')

#new feature
@supabase_login_required
def ai_chat_view(request):
    user_id = request.session['user_uuid']
    username = request.session['username']

    # Fetch user AI chat history
    history_query = supabase_client \
        .table("ai_messages") \
        .select("message, response") \
        .eq("user_id", user_id) \
        .order("created_at", desc=False) \
        .execute()

    message_history = history_query.data or []

    conversation_history = []
    for pair in message_history:
        conversation_history.append({"role": "user", "content": pair["message"]})
        if pair["response"]:
            conversation_history.append({"role": "assistant", "content": pair["response"]})

    if request.method == "POST":
        prompt = request.POST.get("message")

        try:
            # Send the request to OpenAI API for chat completion
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # You can replace this with any model of your choice
                messages=conversation_history + [{"role": "user", "content": prompt}]
            )

            ai_response = response['choices'][0]['message']['content']

            # Save both the prompt and AI response in the Supabase database
            supabase_client.table("ai_messages").insert({
                "user_id": user_id,
                "message": prompt,
                "response": ai_response,
                "created_at": datetime.now().isoformat()
            }).execute()

            return redirect("ai-chat")

        except Exception as e:
            return render(request, "api/ai_chat.html", {
                "messages": message_history,
                "error": str(e)
            })

    # Render AI chat page with the history
    context = {
        "messages": message_history,
    }
    return render(request, "api/ai_chat.html", context)