from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .utils.langchain_bot import llm, run_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
import json
from django.views.decorators.http import require_POST
from .models import ChatSession, ChatMessage


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
    # Always create a new session when loading the chatbot
    new_session = ChatSession.objects.create(user_id=request.user.username)

    # Get all past sessions for this user (incl. the new one)
    sessions = ChatSession.objects.filter(user_id=request.user.username).order_by('-created_at')

    return render(request, 'rep_app/chatbot.html', {
        "sessions": sessions,
        "active_session_id": new_session.id,  # Pass to template
    })

@csrf_exempt
@login_required
def chat_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message")
        session_id = data.get("session_id")

        try:
            session = ChatSession.objects.get(id=session_id, user_id=request.user.username)
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Invalid session"}, status=400)

        # Run bot + store messages
        messages = run_agent(user_message, session)
        bot_reply = messages[-1].content

        # Prepare full history for frontend
        formatted = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "ai"
            formatted.append({"role": role, "content": msg.content})

        return JsonResponse({
            "response": bot_reply,
            "history": formatted
        })

    return JsonResponse({"error": "Invalid request"}, status=400)

def summarize_messages(messages):
    text = "\n".join([f"{m.type.upper()}: {m.content}" for m in messages])
    chain = load_summarize_chain(llm, chain_type="stuff")
    summary = chain.invoke([Document(page_content=text)])
    return summary

@csrf_exempt
@require_POST
@login_required
def start_new_session(request):
    session = ChatSession.objects.create(user_id=request.user.username)
    return JsonResponse({"session_id": session.id})
