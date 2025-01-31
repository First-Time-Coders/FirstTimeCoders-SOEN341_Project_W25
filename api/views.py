from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import registerform
from django.contrib.auth.decorators import login_required

def register_view(request):
    if request.method == 'POST':
        form = registerform(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = registerform()
    return render(request, 'api/register.html/', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
    return render(request, 'api/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def home_view(request):
    return render(request, "api/home.html")

@login_required
def dashboard_view(request):
    return render(request, 'api/dashboard.html', {'user': request.user})



