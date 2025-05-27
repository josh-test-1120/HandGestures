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

import os
from django.conf import settings
#this is to get the current date and time for uploading the file into the blob storage
from datetime import datetime
from django.views.decorators.http import require_http_methods

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
        connection_error = "MySQL connection error: " + str(err)
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
            RowCount
        FROM RunningData;
    """
    
    query_error = ""
    
    # TODO: get prediction_accuracy from server file once it exists
    participants = 0
    data_points = 0
    prediction_accuracy = 0.0
    
    if cursor is not None:
        try:
            cursor.execute(query_string)
            result = next(iter(cursor.fetchall()), None)
            if result is not None:
                
                participants = result[0]
                data_points = result[1]
                
        except Exception as mysql_exception:
            
            query_error = "MySQL query error: " + str(mysql_exception)
    
    summary_data = {
        "participants": "{:,}".format(participants),
        "data_points": "{:,}".format(data_points),
        "prediction_accuracy": "{:,.2f}".format(prediction_accuracy),
        "connection_error": connection_error,
        "query_error": query_error,
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
    
    query_error = ""
    
    avg_accel_x = 0.0
    avg_accel_y = 0.0
    avg_accel_z = 0.0
    avg_rotation_x = 0.0
    avg_rotation_y = 0.0
    avg_rotation_z = 0.0
    max_accel = [0.0, 0.0, 0.0]
    max_rotation = [0.0, 0.0, 0.0]
    
    if cursor is not None:
        try:
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
                
        except Exception as mysql_exception:
            
            query_error = "MySQL query error: " + str(mysql_exception)
    
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
        "connection_error": connection_error,
        "query_error": query_error,
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


def download_template(request):
    """
    Serves the template.CSV file for download; implemented 5-22-2025 (SCRUM Sprint 7)
    """
    #'all' multiple possible paths for the template file
    possible_paths = [
        os.path.join(settings.BASE_DIR, '..', '..', 'backend', 'template.CSV'),  # Two levels up
        os.path.join(settings.BASE_DIR, '..', 'backend', 'template.CSV'),       # One level up
        os.path.join(settings.BASE_DIR, 'backend', 'template.CSV'),             # Same level
        os.path.join(os.path.dirname(settings.BASE_DIR), 'backend', 'template.CSV'),  # Alternative approach
    ]
    
    template_path = None
    for path in possible_paths:
        if os.path.exists(path):
            template_path = path
            break
    
    if template_path is None:
        #in the case that the file is not found, create a simple template content
        template_content = "Timestamp(ms),AccelX(g),AccelY(g),AccelZ(g),GyroX(deg/s),GyroY(deg/s),GyroZ(deg/s),DistanceLeft(cm),DistanceRight(cm)\n"
        response = HttpResponse(template_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="template.csv"'
        return response
    
    try:
        with open(template_path, 'r') as file:
            response = HttpResponse(file.read(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="template.csv"'
            return response
    except (FileNotFoundError, IOError) as e:
        #Fallback: return the template content directly
        template_content = "Timestamp(ms),AccelX(g),AccelY(g),AccelZ(g),GyroX(deg/s),GyroY(deg/s),GyroZ(deg/s),DistanceLeft(cm),DistanceRight(cm)\n"
        response = HttpResponse(template_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="template.csv"'
        return response


@require_http_methods(["POST"])
def upload_contribution(request):
    """Handle CSV file upload to Azure blob storage"""
    try:
        #max file size (2 MB in bytes)
        MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
        
        if 'csv_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file provided'})
        
        csv_file = request.FILES['csv_file']
        container_name = request.POST.get('container', 'public-contributions')
        
        #CSV file type validation
        if not csv_file.name.lower().endswith('.csv'):
            return JsonResponse({'success': False, 'error': 'Invalid file type. Please upload a CSV file.'})
        
        #file size validation
        if csv_file.size > MAX_FILE_SIZE:
            size_mb = csv_file.size / (1024 * 1024)
            return JsonResponse({
                'success': False, 
                'error': f'File size exceeds 2 MB limit. Your file is {size_mb:.2f} MB.'
            })
        
        #creates unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"contribution_{timestamp}_{csv_file.name}"
        
        #Azure credentials from .env file
        storage_account_name = config('AZURE_STORAGE_ACCOUNT_NAME')
        storage_account_key = config('AZURE_STORAGE_ACCOUNT_KEY')
        
        #initializes Azure client (w/ error handling)
        try:
            from azure.storage.blob import BlobServiceClient
            blob_service_client = BlobServiceClient(
                account_url=f"https://{storage_account_name}.blob.core.windows.net",
                credential=storage_account_key
            )
        except ImportError:
            return JsonResponse({'success': False, 'error': 'Azure storage not configured'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Azure connection failed: {str(e)}'})
        
        #uploads to blob storage
        try:
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=filename
            )
            
            #resets file pointer and upload
            csv_file.seek(0)
            blob_client.upload_blob(csv_file.read(), overwrite=True)
            
            return JsonResponse({
                'success': True, 
                'message': 'File uploaded successfully',
                'filename': filename
            })
            
        except Exception as upload_error:
            return JsonResponse({'success': False, 'error': f'Upload failed: {str(upload_error)}'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'})
