import bcrypt
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import registerform
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import supabase
from supabase import create_client, Client
from django.contrib.auth.hashers import make_password
import os

# Load Supabase credentials
SUPABASE_URL = "https://rsdvkupcprtchpzuxgtd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzZHZrdXBjcHJ0Y2hwenV4Z3RkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgwODEyNDIsImV4cCI6MjA1MzY1NzI0Mn0.9SQn2rXp4j6p8Em_FVhEHukZdzpYqV4lF5T8PT_gVAc"

# Initialize Supabase client
supabase_client = supabase.create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        role = request.POST.get('role')

        if not email or not password:
            return JsonResponse({"error": "Missing email or password"}, status=400)

        # Send registration request to Supabase
        response = supabase_client.auth.sign_up({"email": email, "password": password})

        if "error" in response:
            return JsonResponse({"error": response["error"]["message"]}, status=400)

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8') #hash password

        db_response = (supabase_client.table('users').insert(
            {"email": email,
              "username": username,
              "first name": first_name,
              "last name": last_name,
              "password": hashed,
              "gender": gender,
              "role": role}).execute())

        if "error" in db_response and db_response["error"]:
            return JsonResponse({"error": db_response["error"]["message"]}, status=400)

        return redirect('login')

    return render(request, 'api/register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST["email"]
        password = request.POST["password"]

        # Authenticate with Supabase
        response = supabase_client.auth.sign_in_with_password({"email": email, "password": password})

        if response:
            request.session['user'] = response.user.id  # Store user session
            return redirect('dashboard')  # Redirect to dashboard
        else:
            return render(request, "api/login.html", {"error": "Invalid credentials."})

    return render(request, "api/login.html")

def logout_view(request):
    supabase_client.auth.sign_out()
    request.session.flush()  # Clear session
    return redirect('login')

def home_view(request):
    return render(request, "api/home.html")

#@login_required
def dashboard_view(request):
    return render(request, 'api/dashboard.html', {'user': request.user})



