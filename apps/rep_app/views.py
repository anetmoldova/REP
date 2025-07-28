# views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.forms import AuthenticationForm
from .models import ChatSession, ChatMessage
import json
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(temperature=0.5)

# === PUBLIC PAGES ===
def landing(request):
    return render(request, 'rep_app/landing.html')

def signup(request):
    # Add signup logic or render template
    return render(request, 'rep_app/signup.html')

def login_page(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'rep_app/login.html')

# === MAIN APP PAGES ===
@login_required
def dashboard(request):
    return render(request, 'rep_app/dashboard.html')

@login_required
def chatbot_view(request):
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'rep_app/chatbot.html', {
        'sessions': sessions,
        'active_session_id': None,
    })

# === CHATBOT ENDPOINTS ===
@csrf_exempt
@login_required
def start_session(request):
    if request.method == 'POST':
        session = ChatSession.objects.create(user=request.user, summary="New conversation")
        return JsonResponse({
            'session_id': session.id,
            'summary': session.summary,
        })

@csrf_exempt
@login_required
def chat_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message')
        session_id = data.get('session_id')
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        # Save user message
        ChatMessage.objects.create(session=session, is_user=True, content=message)

        # Construct prompt
        history = list(session.messages.order_by('timestamp'))[-10:]
        prompt = "\n".join([
            f"User: {m.content}" if m.is_user else f"Bot: {m.content}"
            for m in history
        ]) + f"\nUser: {message}"

        # Get response from LLM
        response = llm([HumanMessage(content=prompt)]).content
        ChatMessage.objects.create(session=session, is_user=False, content=response)

        # Update summary
        session.summary = message[:50] + ('...' if len(message) > 50 else '')
        session.save()

        return JsonResponse({'response': response})

@login_required
def get_session_summary(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    return JsonResponse({'summary': session.summary or ''})