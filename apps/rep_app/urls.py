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
from apps.rep_app.views import landing, signup, login_page, dashboard, chat_api, chatbot_view, start_session, chat_api, get_session_summary, delete_session
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .utils.langchain_bot import ask_agent

class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have successfully logged out.")
        return super().dispatch(request, *args, **kwargs)
    
def chat_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")
        session_id = data.get("session_id", "")

        try:
            bot_response = ask_agent(user_message)
        except Exception as e:
            bot_response = f"Error: {str(e)}"

        return JsonResponse({"response": bot_response})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name='landing'),
    path('signup/', signup, name='signup'),
    path('login/', login_page, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('chatbot/', chatbot_view, name='chatbot'),  # ✅ keep only this
    path('chat/start/', start_session, name='start_session'),  # ✅ use this one
    path('chat/api/', chat_api, name='chat_api'),
    path('chat/session-summary/<int:session_id>/', get_session_summary, name='get_session_summary'),
    path("chat/delete-session/<uuid:session_id>/", delete_session, name="delete_session"),
    path("chat/", chatbot_view, name="chatbot"),
    path("chat/start-session/", start_session, name="start_session"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
