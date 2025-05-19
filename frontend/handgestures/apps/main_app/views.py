
# These are the most commonly used elements for application views
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, resolve, NoReverseMatch
from django.http import JsonResponse, HttpResponse
from django import forms
from django.views.decorators.csrf import csrf_exempt

import json

import random

import mysql.connector
from mysql.connector import errorcode


CONFIG = {
    "host": "handsgestures-mysql-managed.mysql.database.azure.com",
    "user": "hgadmin",
    "password": "hand$g3$tur3$",
    "database": "handgestures"
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
        SELECT COUNT(DISTINCT participant),
            COUNT(*),
            (SELECT COUNT(*) FROM handdata WHERE label IS NOT NULL AND prediction IS NOT NULL),
            (SELECT COUNT(*) FROM handdata WHERE label = prediction)
        FROM handdata;
    """
    
    participants = None
    data_points = None
    prediction_accuracy = None
    
    database_read_successfully = False
    
    if cursor is not None:
        cursor.execute(query_string)
        result = next(iter(cursor.fetchall()), None)
        if result is not None:
            
            database_read_successfully = True
            
            participants = result[0]
            data_points = result[1]
            if result[2] != 0:
                prediction_accuracy = (result[3] / result[2]) * 100
            else:
                prediction_accuracy = 0.0
    
    if database_read_successfully:
        summary_data = {
            "participants": "{:,}".format(participants),
            "data_points": "{:,}".format(data_points),
            "prediction_accuracy": "{:,.2f}".format(prediction_accuracy),
        }
    else:
        summary_data = {
            "participants": "error",
            "data_points": "error",
            "prediction_accuracy": "error",
        }
    
    return JsonResponse(summary_data)


def demo_page_update(request):
    query_string = """
        WITH cte AS (
            SELECT *,
                SQRT(POW(accelx, 2) + POW(accely, 2) + POW(accelz, 2)) AS total_accel,
                SQRT(POW(gyrox, 2) + POW(gyroy, 2) + POW(gyroz, 2)) AS total_rotation
            FROM handdata
        )
        SELECT AVG(accelx),
            AVG(accely),
            AVG(accelz),
            AVG(gyrox),
            AVG(gyroy),
            AVG(gyroz),
            (SELECT total_accel FROM cte ORDER BY total_accel DESC LIMIT 0, 1) AS max_accel_1,
            (SELECT total_accel FROM cte ORDER BY total_accel DESC LIMIT 1, 1) AS max_accel_2,
            (SELECT total_accel FROM cte ORDER BY total_accel DESC LIMIT 2, 1) AS max_accel_3,
            (SELECT total_rotation FROM cte ORDER BY total_rotation DESC LIMIT 0, 1) AS max_rotation_1,
            (SELECT total_rotation FROM cte ORDER BY total_rotation DESC LIMIT 1, 1) AS max_rotation_2,
            (SELECT total_rotation FROM cte ORDER BY total_rotation DESC LIMIT 2, 1) AS max_rotation_3
        FROM cte;
    """
    
    avg_accel_x = None
    avg_accel_y = None
    avg_accel_z = None
    avg_rotation_x = None
    avg_rotation_y = None
    avg_rotation_z = None
    max_accel_1 = None
    max_accel_2 = None
    max_accel_3 = None
    max_rotation_1 = None
    max_rotation_2 = None
    max_rotation_3 = None
    
    database_read_successfully = False
    
    if cursor is not None:
        cursor.execute(query_string)
        result = next(iter(cursor.fetchall()), None)
        if result is not None:
            
            database_read_successfully = True
            
            avg_accel_x = result[0]
            avg_accel_y = result[1]
            avg_accel_z = result[2]
            avg_rotation_x = result[3]
            avg_rotation_y = result[4]
            avg_rotation_z = result[5]
            max_accel_1 = result[6]
            max_accel_2 = result[7]
            max_accel_3 = result[8]
            max_rotation_1 = result[9]
            max_rotation_2 = result[10]
            max_rotation_3 = result[11]
    
    if database_read_successfully:
        demo_data = {
            "avg_x_accel": "average x acceleration: {:,.3f}".format(avg_accel_x),
            "avg_y_accel": "average y acceleration: {:,.3f}".format(avg_accel_y),
            "avg_z_accel": "average z acceleration: {:,.3f}".format(avg_accel_z),
            "avg_x_rot": "average x rotation: {:,.3f}".format(avg_rotation_x),
            "avg_y_rot": "average y rotation: {:,.3f}".format(avg_rotation_y),
            "avg_z_rot": "average z rotation: {:,.3f}".format(avg_rotation_z),
            "first_fastest_accel": "1st fastest acceleration outlier: {:,.3f}".format(max_accel_1),
            "first_fastest_accel_explanation": "Explanation: n/a",
            "second_fastest_accel": "2nd fastest acceleration outlier: {:,.3f}".format(max_accel_2),
            "second_fastest_accel_explanation": "Explanation: n/a",
            "third_fastest_accel": "3rd fastest acceleration outlier: {:,.3f}".format(max_accel_3),
            "third_fastest_accel_explanation": "Explanation: n/a",
            "first_fastest_rot": "1st fastest rotation outlier: {:,.3f}".format(max_rotation_1),
            "first_fastest_rot_explanation": "Explanation: n/a",
            "second_fastest_rot": "2nd fastest rotation outlier: {:,.3f}".format(max_rotation_2),
            "second_fastest_rot_explanation": "Explanation: n/a",
            "third_fastest_rot": "3rd fastest rotation outlier: {:,.3f}".format(max_rotation_3),
            "third_fastest_rot_explanation": "Explanation: n/a",
        }
    else:
        demo_data = {
            "avg_x_accel": "error",
            "avg_y_accel": "error",
            "avg_z_accel": "error",
            "avg_x_rot": "error",
            "avg_y_rot": "error",
            "avg_z_rot": "error",
            "first_fastest_accel": "error",
            "first_fastest_accel_explanation": "error",
            "second_fastest_accel": "error",
            "second_fastest_accel_explanation": "error",
            "third_fastest_accel": "error",
            "third_fastest_accel_explanation": "error",
            "first_fastest_rot": "error",
            "first_fastest_rot_explanation": "error",
            "second_fastest_rot": "error",
            "second_fastest_rot_explanation": "error",
            "third_fastest_rot": "error",
            "third_fastest_rot_explanation": "error",
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