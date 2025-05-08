# These are the most commonly used elements for application views
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, resolve, NoReverseMatch
from django.http import JsonResponse, HttpResponse

import random

# Import your models for this application
# from .models import Course, Description, Comment

# Import models from different applications
# from ..<different_app>.models import <table_name>

# Create your views here.
def index(request):
    return render(request, 'main_app/index.html')


# API endpoints here.
def api_data(request):
    return JsonResponse({'status': 'success', 'message': 'API is working'})


def summary(request):
    return render(request, 'main_app/summary.html')


def structure(request):
    return render(request, 'main_app/structure.html')

def machine_learning(request):
    return render(request, 'main_app/machine_learning.html')


def demo(request):
    return render(request, 'main_app/demo.html')


def live_demo(request):
    return render(request, 'main_app/live_demo.html')


def contact(request):
    return render(request, 'main_app/contact.html')


def summary_page_update(request):
    summary_data = {
        "participants": "{:,}".format(123),
        "data_points": "{:,}".format(12345),
        "prediction_accuracy": (percent_str := str(90.12345))[:percent_str.find(".") + 3] + "%",
    }
    
    return JsonResponse(summary_data)


def demo_page_update(request):
    demo_data = {
        "avg_resting_accel": "average resting acceleration: {:,}".format(0.00),
        "avg_walking_accel": "average walking acceleration: {:,}".format(3.12),
        "avg_running_accel": "average running acceleration: {:,}".format(7.54),
        "avg_resting_rot": "average resting rotation: {:,}".format(0.00),
        "avg_walking_rot": "average walking rotation: {:,}".format(1.23),
        "avg_running_rot": "average running rotation: {:,}".format(2.34),
        "first_fastest_accel": "1st fastest acceleration outlier: {:,}".format(12.12),
        "first_fastest_accel_explanation": "Explanation: A bug flew in the user's face.",
        "second_fastest_accel": "2nd fastest acceleration outlier: {:,}".format(11.12),
        "second_fastest_accel_explanation": "Explanation: The user was waving to someone.",
        "third_fastest_accel": "3rd fastest acceleration outlier: {:,}".format(10.12),
        "third_fastest_accel_explanation": "Explanation: The user was having a seizure.",
        "first_fastest_rot": "1st fastest rotation outlier: {:,}".format(12.54),
        "first_fastest_rot_explanation": "Explanation: The user was shaking his arm due to nervous energy.",
        "second_fastest_rot": "2nd fastest rotation outlier: {:,}".format(11.54),
        "second_fastest_rot_explanation": "Explanation: The user was making the \"sorta\" gesture.",
        "third_fastest_rot": "3rd fastest rotation outlier: {:,}".format(10.54),
        "third_fastest_rot_explanation": "Explanation: The user was having a seizure.",
    }
    
    return JsonResponse(demo_data)
