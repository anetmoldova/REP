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
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.utils
import psycopg2
from psycopg2.extras import RealDictCursor

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

def get_database_connection():
    """Get PostgreSQL database connection"""
    try:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "4321"),
            database=os.getenv("POSTGRES_DB", "rep_db"),
            user=os.getenv("POSTGRES_USER", "vanhieuvu"),
            password=os.getenv("POSTGRES_PASSWORD", "nanuk§2")
        )
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_dashboard_data():
    """Fetch data for dashboard visualizations"""
    connection = get_database_connection()
    if not connection:
        return None
    
    try:
        # Query 1: Average monthly rent by region
        query1 = """
        SELECT 
            gl.region_name,
            AVG(CAST(mv.value AS DECIMAL)) as avg_monthly_rent,
            COUNT(*) as property_count
        FROM metrics_vals mv
        JOIN geo_location gl ON mv.geo_loc_id = gl.id
        WHERE mv.metric = 'monthly_price'
        GROUP BY gl.region_name, gl.id
        ORDER BY avg_monthly_rent DESC
        """
        
        # Query 2: Property sizes by region
        query2 = """
        SELECT 
            gl.region_name,
            AVG(CAST(mv.value AS DECIMAL)) as avg_area_m2,
            COUNT(*) as property_count
        FROM metrics_vals mv
        JOIN geo_location gl ON mv.geo_loc_id = gl.id
        WHERE mv.metric = 'usable_area_m2'
        GROUP BY gl.region_name, gl.id
        ORDER BY avg_area_m2 DESC
        """
        
        # Query 3: Price per square meter
        query3 = """
        SELECT 
            gl.region_name,
            AVG(CAST(price.value AS DECIMAL) / CAST(area.value AS DECIMAL)) as price_per_m2
        FROM metrics_vals price
        JOIN metrics_vals area ON price.url = area.url AND price.geo_loc_id = area.geo_loc_id
        JOIN geo_location gl ON price.geo_loc_id = gl.id
        WHERE price.metric = 'monthly_price' AND area.metric = 'usable_area_m2'
        GROUP BY gl.region_name, gl.id
        ORDER BY price_per_m2 DESC
        """
        
        # Query 4: Total properties by region
        query4 = """
        SELECT 
            gl.region_name,
            COUNT(DISTINCT mv.url) as total_properties
        FROM metrics_vals mv
        JOIN geo_location gl ON mv.geo_loc_id = gl.id
        WHERE mv.metric = 'monthly_price'
        GROUP BY gl.region_name, gl.id
        ORDER BY total_properties DESC
        """
        
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query1)
            rent_data = pd.DataFrame(cursor.fetchall())
            
            cursor.execute(query2)
            area_data = pd.DataFrame(cursor.fetchall())
            
            cursor.execute(query3)
            price_per_m2_data = pd.DataFrame(cursor.fetchall())
            
            cursor.execute(query4)
            property_count_data = pd.DataFrame(cursor.fetchall())
        
        connection.close()
        
        return {
            'rent_data': rent_data,
            'area_data': area_data,
            'price_per_m2_data': price_per_m2_data,
            'property_count_data': property_count_data
        }
        
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        connection.close()
        return None

def create_dashboard_charts(data):
    """Create Plotly charts for dashboard"""
    if not data:
        return {}
    
    charts = {}
    
    # Chart 1: Average Monthly Rent by Region
    if not data['rent_data'].empty:
        fig1 = px.bar(
            data['rent_data'], 
            x='region_name', 
            y='avg_monthly_rent',
            title='',
            labels={'avg_monthly_rent': 'Average Monthly Rent (CZK)', 'region_name': 'Region'},
            color='avg_monthly_rent',
            color_continuous_scale='viridis',
            text='avg_monthly_rent'
        )
        fig1.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1
        )
        fig1.update_layout(
            height=350,
            margin=dict(l=60, r=40, t=20, b=80),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            xaxis=dict(
                showgrid=False,
                tickangle=45,
                tickfont=dict(size=11)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickfont=dict(size=11)
            ),
            title_font_size=16,
            title_font_color='#896F8C'
        )
        charts['rent_chart'] = plotly.utils.PlotlyJSONEncoder().encode(fig1)
    
    # Chart 2: Average Property Size by Region
    if not data['area_data'].empty:
        fig2 = px.bar(
            data['area_data'], 
            x='region_name', 
            y='avg_area_m2',
            title='',
            labels={'avg_area_m2': 'Average Area (m²)', 'region_name': 'Region'},
            color='avg_area_m2',
            color_continuous_scale='plasma',
            text='avg_area_m2'
        )
        fig2.update_traces(
            texttemplate='%{text:.1f}',
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1
        )
        fig2.update_layout(
            height=350,
            margin=dict(l=60, r=40, t=20, b=80),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            xaxis=dict(
                showgrid=False,
                tickangle=45,
                tickfont=dict(size=11)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickfont=dict(size=11)
            ),
            title_font_size=16,
            title_font_color='#896F8C'
        )
        charts['area_chart'] = plotly.utils.PlotlyJSONEncoder().encode(fig2)
    
    # Chart 3: Price per Square Meter
    if not data['price_per_m2_data'].empty:
        fig3 = px.bar(
            data['price_per_m2_data'], 
            x='region_name', 
            y='price_per_m2',
            title='',
            labels={'price_per_m2': 'Price per m² (CZK)', 'region_name': 'Region'},
            color='price_per_m2',
            color_continuous_scale='inferno',
            text='price_per_m2'
        )
        fig3.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1
        )
        fig3.update_layout(
            height=350,
            margin=dict(l=60, r=40, t=20, b=80),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            xaxis=dict(
                showgrid=False,
                tickangle=45,
                tickfont=dict(size=11)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickfont=dict(size=11)
            ),
            title_font_size=16,
            title_font_color='#896F8C'
        )
        charts['price_per_m2_chart'] = plotly.utils.PlotlyJSONEncoder().encode(fig3)
    
    # Chart 4: Property Distribution by Region
    if not data['property_count_data'].empty:
        fig4 = px.pie(
            data['property_count_data'], 
            values='total_properties', 
            names='region_name',
            title='',
            hole=0.4
        )
        fig4.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=12,
            marker=dict(line=dict(color='white', width=2))
        )
        fig4.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=11),
            title_font_size=16,
            title_font_color='#896F8C'
        )
        charts['property_count_chart'] = plotly.utils.PlotlyJSONEncoder().encode(fig4)
    
    return charts

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
    data = get_dashboard_data()
    charts = create_dashboard_charts(data)
    
    # Get available regions for filters
    available_regions = []
    if data and not data['rent_data'].empty:
        available_regions = data['rent_data']['region_name'].tolist()
    
    # Get selected filter from request
    selected_region = request.GET.get('region', '')
    
    # Apply filter if selected
    if selected_region and selected_region != 'all':
        filtered_data = filter_data_by_region(data, selected_region)
        filtered_charts = create_dashboard_charts(filtered_data)
        charts = filtered_charts
        data = filtered_data

    kpis = {}
    if data and not data['rent_data'].empty:
        kpis['total_properties'] = data['rent_data']['property_count'].sum()
        kpis['avg_rent'] = round(data['rent_data']['avg_monthly_rent'].mean(), 0)
        kpis['max_rent'] = round(data['rent_data']['avg_monthly_rent'].max(), 0)
        kpis['min_rent'] = round(data['rent_data']['avg_monthly_rent'].min(), 0)

    return render(request, 'rep_app/dashboard.html', {
        'charts': charts,
        'kpis': kpis,
        'data_available': data is not None,
        'available_regions': available_regions,
        'selected_region': selected_region
    })

def filter_data_by_region(data, region_name):
    """Filter data by selected region"""
    if not data:
        return data
    
    filtered_data = {}
    
    # Filter rent data
    if not data['rent_data'].empty:
        filtered_data['rent_data'] = data['rent_data'][data['rent_data']['region_name'] == region_name]
    
    # Filter area data
    if not data['area_data'].empty:
        filtered_data['area_data'] = data['area_data'][data['area_data']['region_name'] == region_name]
    
    # Filter price per m2 data
    if not data['price_per_m2_data'].empty:
        filtered_data['price_per_m2_data'] = data['price_per_m2_data'][data['price_per_m2_data']['region_name'] == region_name]
    
    # Filter property count data
    if not data['property_count_data'].empty:
        filtered_data['property_count_data'] = data['property_count_data'][data['property_count_data']['region_name'] == region_name]
    
    return filtered_data

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