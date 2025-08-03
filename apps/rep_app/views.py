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
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import os

# Import the SQL agent from langchain_bot
from .utils.langchain_bot import get_agent_response, llm

def get_llm_response(prompt):
    """Get response from the SQL agent with fallback"""
    try:
        response = get_agent_response(prompt)
        return response
    except Exception as e:
        print(f"SQL Agent error: {e}")
        # Fallback to simple LLM if SQL agent fails
        try:
            fallback_response = llm([HumanMessage(content=prompt)]).content
            return fallback_response
        except Exception as fallback_error:
            print(f"Fallback LLM error: {fallback_error}")
            return f"I'm having trouble connecting to my services right now. Please try again later. (Error: {str(e)})"

# === PUBLIC PAGES ===
def landing(request):
    return render(request, 'rep_app/landing.html')

def signup(request):
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
        print("🧪 New session created:", session.id, "user:", request.user)
        return JsonResponse({
            'session_id': session.id,
            'summary': session.summary,
        })

@csrf_exempt
@login_required
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message')
            session_id = data.get('session_id')
            
            if not message or not session_id:
                return JsonResponse({'response': 'Missing message or session_id'}, status=400)
            
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)

            # Save user message
            ChatMessage.objects.create(session=session, is_user=True, content=message)

            # Get response from SQL agent (which will automatically choose the right tool)
            response = get_agent_response(message, session)
            ChatMessage.objects.create(session=session, is_user=False, content=response)

            # Generate session summary (if it's default or empty)
            if not session.summary or session.summary.strip() == "New conversation":
                try:
                    summary_prompt = (
                        "Summarize the following chat in one sentence for use as a session label:\n\n"
                        f"User: {message}\nAssistant: {response}"
                    )
                    summary_result = get_agent_response(summary_prompt).strip()
                    session.summary = summary_result[:200] or message[:50]
                except Exception as e:
                    print(f"Summary generation error: {e}")
                    session.summary = message[:50] + ('...' if len(message) > 50 else '')

                session.save()

            return JsonResponse({
                'response': response,
                'summary': session.summary
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'response': 'An error occurred. Please try again.'}, status=500)

@login_required
def get_session_summary(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    return JsonResponse({'summary': session.summary or ''})

@require_http_methods(["DELETE"])
@login_required
def delete_session(request, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id, user=request.user)
        session.delete()
        return JsonResponse({"status": "deleted"})
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)
    
@login_required
def session_messages(request, session_id):
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        messages = session.messages.order_by('timestamp')
        data = [
            {'is_user': m.is_user, 'content': m.content}
            for m in messages
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        print(f"Error loading session messages: {e}")
        return JsonResponse([], safe=False)