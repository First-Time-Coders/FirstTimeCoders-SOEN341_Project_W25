import bcrypt
import supabase
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from gotrue.errors import AuthApiError
from postgrest import APIError
from django.contrib.auth.models import User
from .forms import registerform
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
            response = supabase_client.auth.sign_up({"email": email, "password": password})

            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8') #hash password
        
            db_response = (supabase_client.table('users').insert({
                "email": email,
                "username": username,
                "first name": first_name,
                "last name": last_name,
                "password": hashed,
                "gender": gender,
                "role": role}).execute())

            django_user = User.objects.create_user(username=username, email=email, password=password, first_name = first_name, last_name = last_name)

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

            if user_data:
                user_query = supabase_client.table("users").select("role").eq("email", email).single().execute()
                user_role = user_query.data["role"] if user_query.data else None

                django_user, create = User.objects.get_or_create(username=user_data.id, defaults={'email': email})

                login(request, django_user)

                if user_role == "admin":
                    return redirect("dashboard-admin")  # Replace with actual URL
                else:
                    return redirect("dashboard")
            else:
                messages.error(request, "Failed login attempt")
                return redirect('login')

        except AuthApiError as e:
            if "invalid_grant" in str(e):  # Supabase returns "invalid_grant" for wrong credentials
                messages.error(request, "Invalid email or password.")
            else:
                messages.error(request, "Authentication failed. Please try again.")
            return redirect('login')

    return render(request, "api/login.html")

def logout_view(request):
    supabase_client.auth.sign_out()
    logout(request)
    request.session.flush()  # Clear session
    return redirect('login')

def home_view(request):
    return render(request, "api/home.html")

@login_required
def dashboard_admin_view(request):

    return render(request, "api/dashboard-admin.html", {'user': request.user})

@login_required
def dashboard_view(request):
    return render(request, 'api/dashboard.html', {'user': request.user})

def create_channel(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        try:
            response = supabase_client.table('channels').insert({
                "name": name,
                "description": description,
            }).execute()

            return redirect('dashboard')

        except APIError as e:
            messages.error(request, "Failed to create channel")
            return redirect('create_channel')

    return render(request, 'api/create_channel.html')



