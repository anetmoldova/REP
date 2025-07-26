from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Create your views here.

def landing(request):
    image_filename = 'rep_app/preview_landing_page_v2.png'  # You can change this dynamically
    return render(request, 'rep_app/landing.html', {'landing_image': image_filename})

def login_page(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            from django.contrib import messages
            messages.error(request, 'Invalid username or password.')
    return render(request, 'rep_app/login.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            User.objects.create_user(username=username, email=email, password=password)
            return redirect('login')
    return render(request, 'rep_app/signup.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    return render(request, 'rep_app/dashboard.html')

@login_required
def chatbot(request):
    return render(request, 'rep_app/chatbot.html')