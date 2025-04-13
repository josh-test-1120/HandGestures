# These are the most commonly used elements for application views
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, resolve, NoReverseMatch
from django.http import JsonResponse

# Import your models for this application
# from .models import Course, Description, Comment

# Import models from different applications
# from ..<different_app>.models import <table_name>

# Create your views here.
def index(request):
	return render(request, 'main_app/index.html')
	#pass

# API endpoints here.
def api_data(request):
	return JsonResponse({'status': 'success', 'message': 'API is working'})