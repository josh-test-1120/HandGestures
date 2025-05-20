
import mysql.connector
from mysql.connector import errorcode

# These are the most commonly used elements for application views
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, resolve, NoReverseMatch
from django.http import JsonResponse, HttpResponse
from django import forms
from django.views.decorators.csrf import csrf_exempt

import json

import random
# This is to load from the .env file
from decouple import config


CONFIG = {
    "host": config('DB_HOST'),
    "user": config('DB_USER'),
    "password": config('DB_PASSWORD'),
    "database": config('DB_NAME')
}

connection = None
cursor = None
connection_error = ""
try:
     connection = mysql.connector.connect(**CONFIG)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        connection_error = "Something is wrong with the user name or password"
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        connection_error = "Database does not exist"
    else:
        connection_error = err
else:
    cursor = connection.cursor()


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
    query_string = """
        SELECT ParticipantCount,
            RowCount,
            CorrectCount
        FROM RunningData;
    """
    
    participants = 0
    data_points = 0
    prediction_accuracy = 0.0
    
    if cursor is not None:
        cursor.execute(query_string)
        result = next(iter(cursor.fetchall()), None)
        if result is not None:
            
            participants = result[0]
            data_points = result[1]
            if data_points != 0:
                prediction_accuracy = (result[2] / data_points) * 100
            else:
                prediction_accuracy = 0.0
    
    summary_data = {
        "participants": "{:,}".format(participants),
        "data_points": "{:,}".format(data_points),
        "prediction_accuracy": "{:,.2f}".format(prediction_accuracy),
    }
    
    return JsonResponse(summary_data)


def demo_page_update(request):
    query_string_top_accel = """
        SELECT AccelTotal
        FROM HandData
        ORDER BY AccelTotal DESC LIMIT 3;
    """
    
    query_string_top_rotation = """
        SELECT GyroTotal
        FROM HandData
        ORDER BY GyroTotal DESC LIMIT 3;
    """
    
    query_string_averages = """
        SELECT AverageXAccel,
            AverageYAccel,
            AverageZAccel,
            AverageXRotation,
            AverageYRotation,
            AverageZRotation
        FROM RunningData;
    """
    
    avg_accel_x = 0.0
    avg_accel_y = 0.0
    avg_accel_z = 0.0
    avg_rotation_x = 0.0
    avg_rotation_y = 0.0
    avg_rotation_z = 0.0
    max_accel = [0.0, 0.0, 0.0]
    max_rotation = [0.0, 0.0, 0.0]
    
    if cursor is not None:
        
        cursor.execute(query_string_top_accel)
        iter_results = iter(cursor.fetchall())
        max_accel = [next(iter_results, (0.0,))[0] for _ in range(len(max_accel))]
        
        cursor.execute(query_string_top_rotation)
        iter_results = iter(cursor.fetchall())
        max_rotation = [next(iter_results, (0.0,))[0] for _ in range(len(max_rotation))]
        
        cursor.execute(query_string_averages)
        result = next(iter(cursor.fetchall()), None)
        if result is not None:
            avg_accel_x = result[0]
            avg_accel_y = result[1]
            avg_accel_z = result[2]
            avg_rotation_x = result[3]
            avg_rotation_y = result[4]
            avg_rotation_z = result[5]
    
    demo_data = {
        "avg_x_accel": "average x acceleration: {:,.3f}".format(avg_accel_x),
        "avg_y_accel": "average y acceleration: {:,.3f}".format(avg_accel_y),
        "avg_z_accel": "average z acceleration: {:,.3f}".format(avg_accel_z),
        "avg_x_rot": "average x rotation: {:,.3f}".format(avg_rotation_x),
        "avg_y_rot": "average y rotation: {:,.3f}".format(avg_rotation_y),
        "avg_z_rot": "average z rotation: {:,.3f}".format(avg_rotation_z),
        "first_fastest_accel": "1st fastest acceleration outlier: {:,.3f}".format(max_accel[0]),
        "first_fastest_accel_explanation": "Explanation: n/a",
        "second_fastest_accel": "2nd fastest acceleration outlier: {:,.3f}".format(max_accel[1]),
        "second_fastest_accel_explanation": "Explanation: n/a",
        "third_fastest_accel": "3rd fastest acceleration outlier: {:,.3f}".format(max_accel[2]),
        "third_fastest_accel_explanation": "Explanation: n/a",
        "first_fastest_rot": "1st fastest rotation outlier: {:,.3f}".format(max_rotation[0]),
        "first_fastest_rot_explanation": "Explanation: n/a",
        "second_fastest_rot": "2nd fastest rotation outlier: {:,.3f}".format(max_rotation[1]),
        "second_fastest_rot_explanation": "Explanation: n/a",
        "third_fastest_rot": "3rd fastest rotation outlier: {:,.3f}".format(max_rotation[2]),
        "third_fastest_rot_explanation": "Explanation: n/a",
    }
    
    return JsonResponse(demo_data)


# TODO: consider if this needs to use CSRF tokens
# TODO: send data to the neural network once it's made.
@csrf_exempt
def live_demo_prediction(request):
    
    sample_predictions = [0.125, 0.2, 0.375, 0.3]
    
    if request.method == 'POST':
        data = json.loads(request.body)
        #print(*data, sep="\n")
        
        # replace below with neural network output once it's ready
        predictions_this_request = len(data)
        predictions = [None] * predictions_this_request
        
        for idx in range(predictions_this_request):
            sample_predictions_idx = (round(data[idx]["time"]) % 20) // 5
            prediction = {
                "Shaking": sample_predictions[(sample_predictions_idx + 0) % len(sample_predictions)],
                "Posture": sample_predictions[(sample_predictions_idx + 1) % len(sample_predictions)],
                "Fall": sample_predictions[(sample_predictions_idx + 2) % len(sample_predictions)],
                "Normal": sample_predictions[(sample_predictions_idx + 3) % len(sample_predictions)],
            }
            predictions[idx] = prediction
        
        return JsonResponse(dict(zip(range(predictions_this_request), predictions)))
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
