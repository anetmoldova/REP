from django.shortcuts import render

# Create your views here.

def landing(request):
    return render(request, 'rep_app/landing.html')
