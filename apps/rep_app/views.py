from django.shortcuts import render

# Create your views here.

def landing(request):
    image_filename = 'rep_app/preview_landing_page_v2.png'  # You can change this dynamically
    return render(request, 'rep_app/landing.html', {'landing_image': image_filename})

def signup(request):
    return render(request, 'rep_app/signup.html')

def login_page(request):
    return render(request, 'rep_app/login.html')
