import datetime
from http.client import responses

import bcrypt
import uuid
import supabase
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, get_user_model
from gotrue.errors import AuthApiError
from postgrest import APIError
from django.contrib.auth.decorators import login_required

from .decorators import supabase_login_required
from .forms import registerform
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from supabase import create_client, Client
from django.contrib.auth.hashers import make_password
import os
from django.conf import settings


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






def profile_view(request):
    user_id = request.session.get('user_uuid')  # Récupérer l'UUID de l'utilisateur

    if not user_id:
        return redirect('login')  # Rediriger si l'utilisateur n'est pas connecté

    try:
        # Récupérer les données de l'utilisateur depuis Supabase
        response = supabase_client.table('users').select('*').eq('id', user_id).single().execute()

        # DEBUG: Afficher les données récupérées pour voir les clés disponibles
        print("DEBUG - User Data:", response.data)

        if response.data:
            user = response.data  # Récupérer les données utilisateur

            # Vérifier les noms de colonnes exacts et les adapter si besoin
            user_data = {
                'first_name': user.get('first name', "N/A"),  # No underscore, space instead
                'last_name': user.get('last name', "N/A"),  # No underscore, space instead
                'email': user.get('email', 'N/A'),
                'username': user.get('username', 'N/A'),
                'gender': user.get('gender', 'N/A'),
                'role': user.get('role', 'N/A'),
                'age': user.get('age', 'N/A'),  # If "age" exists, otherwise remove this
            }


            return render(request, 'api/profile.html', {'user': user_data})
        else:
            return render(request, 'api/profile.html', {'error': 'User not found'})

    except Exception as e:
        print(f"Error fetching profile data: {e}")
        return render(request, 'api/profile.html', {'error': 'An error occurred while fetching profile data'})









def edit_profile_view(request):
    user_id = request.session.get("user_uuid")  # Get user UUID from session

    if not user_id:
        messages.error(request, "You must be logged in to edit your profile.")
        return redirect("login")

    if request.method == "POST":
        field = request.POST.get("field")
        value = request.POST.get("value")

        if not field or not value:
            messages.error(request, "Invalid selection or empty value.")
            return redirect("edit-profile")

        supabase_fields = {
            "first_name": "first name",
            "last_name": "last name",
            "email": "email",
            "age": "age",
            "gender": "gender",
            "role": "role",
            "username": "username"
        }

        if field not in supabase_fields:
            messages.error(request, "Invalid field selection.")
            return redirect("edit-profile")

        db_field = supabase_fields[field]

        # Validation
        if field in ["first_name", "last_name"]:
            if not value.replace(" ", "").isalpha():
                messages.error(request, "Name should only contain letters.")
                return redirect("edit-profile")
        elif field == "age":
            if not value.isdigit() or int(value) <= 0:
                messages.error(request, "Enter a valid positive age.")
                return redirect("edit-profile")
            value = int(value)
        elif field == "username":
            if " " in value:
                messages.error(request, "Username should not contain spaces.")
                return redirect("edit-profile")
        elif field == "gender":
            if value not in ["Male", "Female", "Other"]:
                messages.error(request, "Invalid gender selection.")
                return redirect("edit-profile")
        elif field == "role":
            if value not in ["Admin", "User"]:
                messages.error(request, "Invalid role selection.")
                return redirect("edit-profile")

        try:
            update_response = supabase_client.table("users").update({db_field: value}).eq("id", user_id).execute()

            if field == "email":
                try:
                    auth_response = supabase_client.auth.update_user({"email": value})
                    if auth_response and "error" in auth_response:
                        messages.error(request, "Failed to update authentication email.")
                        return redirect("edit-profile")
                except Exception as e:
                    messages.error(request, f"Error updating email in authentication system: {str(e)}")
                    return redirect("edit-profile")

            if update_response.data:
                messages.success(request, f"{db_field.capitalize()} updated successfully!")
            else:
                messages.error(request, "Failed to update profile.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect("profile")

    return render(request, "api/profile_edit.html")






















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
            #if user_role == "admin" or "member":
               #return redirect("dashboard-admin")
            #else:
             #   return redirect("dashboard")

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
#im testin rn but later: messages_view(request, channel_id):
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
    message = supabase_client.table('channel_messages').select('message, username').eq('channel_id', channel_id).execute()

    channel = supabase_client.table('channels').select('name').eq('id', channel_id).single().execute()
    channel_name = channel.data['name'] if channel.data else "Unknown Channel"

    context = {
        'messages': message.data,
        'channel_id': channel_id,
        'channel_name': channel_name
    }
    return render(request, "api/messages.html", context)