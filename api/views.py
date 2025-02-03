import password
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import registerform
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from supabase import create_client
from django.contrib.auth.hashers import make_password

import os

# Load Supabase credentials
SUPABASE_URL = "https://rsdvkupcprtchpzuxgtd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzZHZrdXBjcHJ0Y2hwenV4Z3RkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgwODEyNDIsImV4cCI6MjA1MzY1NzI0Mn0.9SQn2rXp4j6p8Em_FVhEHukZdzpYqV4lF5T8PT_gVAc"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def register_view(request):
    if request.method == 'POST':
        form = registerform(request.POST)
        if form.is_valid():
            # Extract form data
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            hashed_password = make_password(password)

            # Insert user into Supabase
            response = supabase.table("users").insert({
                "username": username,
                "email": email,
                "password": hashed_password  # Hash this in a real application!
            }).execute()

            if response.data:
                return redirect('login')  # Redirect to login page after successful registration
            else:
                form.add_error(None, "Error registering user. Try again.")

    else:
        form = registerform()

    return render(request, 'api/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]

        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({"username": username, "email": email, "password": password})

        if response.user:
            request.session['user'] = response.user.id  # Store user session
            return redirect('dashboard')  # Redirect to dashboard
        else:
            return render(request, "api/login.html", {"error": "Invalid credentials."})

    return render(request, "api/login.html")

def logout_view(request):
    supabase.auth.sign_out()
    request.session.flush()  # Clear session
    return redirect('login')

def home_view(request):
    return render(request, "api/home.html")

@login_required
def dashboard_view(request):
    return render(request, 'api/dashboard.html', {'user': request.user})



