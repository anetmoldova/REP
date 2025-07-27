"""
URL configuration for rep_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from apps.rep_app.views import landing, signup, login_page, dashboard, chatbot, chat_api, start_new_session
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.shortcuts import redirect

class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have successfully logged out.")
        return super().dispatch(request, *args, **kwargs)
    
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name='landing'),
    path('signup/', signup, name='signup'),
    path('login/', login_page, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('chatbot/', chatbot, name='chatbot'),
    path('chat-api/', chat_api, name='chat_api'),
    path("start-session/", start_new_session, name="start_session"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
