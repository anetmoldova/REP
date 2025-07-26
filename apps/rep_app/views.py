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
from .utils.langchain_bot import llm, run_agent

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

@csrf_exempt
def chat_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        if "chat_history" not in request.session:
            request.session["chat_history"] = []

        history_msgs = []
        for msg in request.session["chat_history"]:
            if msg["role"] == "user":
                history_msgs.append(HumanMessage(content=msg["content"]))
            else:
                history_msgs.append(AIMessage(content=msg["content"]))

        # Summarize if too long
        if len(history_msgs) > 10:
            summary_text = summarize_messages(history_msgs)
            request.session["conversation_summary"] = summary_text
            history_msgs = history_msgs[-2:]  # keep only last 2

            if "conversation_log" not in request.session:
                request.session["conversation_log"] = []

            request.session["conversation_log"].insert(0, {
                "summary": summary_text,
                "title": user_message[:40] + "..." if len(user_message) > 40 else user_message
            })

            request.session["conversation_log"] = request.session["conversation_log"][:5]

        full_history = run_agent(user_message, history_msgs)
        bot_reply = full_history[-1].content

        request.session["chat_history"].append({"role": "user", "content": user_message})
        request.session["chat_history"].append({"role": "bot", "content": bot_reply})
        request.session.modified = True

        return JsonResponse({"response": bot_reply})

def summarize_messages(messages):
    from langchain.chains.summarize import load_summarize_chain
    text = "\n".join([f"{m.type.upper()}: {m.content}" for m in messages])
    chain = load_summarize_chain(llm, chain_type="stuff")
    summary = chain.run([Document(page_content=text)])
    return summary