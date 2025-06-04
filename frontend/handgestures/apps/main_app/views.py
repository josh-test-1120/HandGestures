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

import torch
import torch.nn as nn


class SeizureLSTM(nn.Module):
    def __init__(self, input_size=8, hidden_size=64, num_layers=2, num_classes=4):
        super(SeizureLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # Last time step
        out = self.fc(out)
        return out


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


def load_model():
    import __main__
    setattr(__main__, "SeizureLSTM", SeizureLSTM)

    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static',
        'main_app',
        'data',
        'NeuroTech-1.pt'
    )
    
    loaded_model = torch.load(file_path, weights_only=False)
    loaded_model.eval()
    
    return loaded_model


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
    
    participants = 0
    data_points = 0
    
    if cursor is not None:
        try:
            cursor.execute(query_string)
            result = next(iter(cursor.fetchall()), None)
            if result is not None:
                
                participants = result[0]
                data_points = result[1]
                
        except Exception as mysql_exception:
            
            query_error = "MySQL query error: " + str(mysql_exception)
    
    # Prediction accuracy is found in a server file and loaded in JavaScript
    summary_data = {
        "participants": "{:,}".format(participants),
        "data_points": "{:,}".format(data_points),
        "connection_error": connection_error,
        "query_error": query_error,
    }
    
    return JsonResponse(summary_data)


def demo_page_update(request):
    query_string = """
        WITH MaxValues(MaxAccelX, MaxAccelY, MaxAccelZ, MaxGyroX, MaxGyroY, MaxGyroZ) AS (
            SELECT MAX(ABS(AccelX)),
                MAX(ABS(AccelY)),
                MAX(ABS(AccelZ)),
                MAX(ABS(GyroX)),
                MAX(ABS(GyroY)),
                MAX(ABS(GyroZ))
            FROM handdata
        )
        SELECT MaxAccelX,
            MaxAccelY,
            MaxAccelZ,
            MaxGyroX,
            MaxGyroY,
            MaxGyroZ,
            AverageXAccel,
            AverageYAccel,
            AverageZAccel,
            AverageXRotation,
            AverageYRotation,
            AverageZRotation
        FROM MaxValues JOIN RunningData;
    """
    
    query_error = ""
    
    max_accel_x = 0.0
    max_accel_y = 0.0
    max_accel_z = 0.0
    max_gyro_x = 0.0
    max_gyro_y = 0.0
    max_gyro_z = 0.0
    avg_accel_x = 0.0
    avg_accel_y = 0.0
    avg_accel_z = 0.0
    avg_rotation_x = 0.0
    avg_rotation_y = 0.0
    avg_rotation_z = 0.0
    
    if cursor is not None:
        try:
            cursor.execute(query_string)
            result = next(iter(cursor.fetchall()), None)
            if result is not None:
                
                max_accel_x = result[0]
                max_accel_y = result[1]
                max_accel_z = result[2]
                max_gyro_x = result[3]
                max_gyro_y = result[4]
                max_gyro_z = result[5]
                avg_accel_x = result[6]
                avg_accel_y = result[7]
                avg_accel_z = result[8]
                avg_rotation_x = result[9]
                avg_rotation_y = result[10]
                avg_rotation_z = result[11]
                
        except Exception as mysql_exception:
            
            query_error = "MySQL query error: " + str(mysql_exception)
    
    demo_data = {
        "avg_x_accel": "average x acceleration: {:,.3f}".format(avg_accel_x),
        "avg_y_accel": "average y acceleration: {:,.3f}".format(avg_accel_y),
        "avg_z_accel": "average z acceleration: {:,.3f}".format(avg_accel_z),
        "avg_x_rot": "average x rotation: {:,.3f}".format(avg_rotation_x),
        "avg_y_rot": "average y rotation: {:,.3f}".format(avg_rotation_y),
        "avg_z_rot": "average z rotation: {:,.3f}".format(avg_rotation_z),
        "first_fastest_accel": "fastest x acceleration: {:,.3f}".format(max_accel_x),
        "second_fastest_accel": "fastest y acceleration: {:,.3f}".format(max_accel_y),
        "third_fastest_accel": "fastest z acceleration: {:,.3f}".format(max_accel_z),
        "first_fastest_rot": "fastest x rotation: {:,.3f}".format(max_gyro_x),
        "second_fastest_rot": "fastest y rotation: {:,.3f}".format(max_gyro_y),
        "third_fastest_rot": "fastest z rotation: {:,.3f}".format(max_gyro_z),
        "connection_error": connection_error,
        "query_error": query_error,
    }
    
    return JsonResponse(demo_data)


# TODO: consider if this needs to use CSRF tokens
# TODO: send data to the neural network once it's made.
@csrf_exempt
def live_demo_prediction(request):
    
    label_map = {
        "normal": 0,
        "tremor": 1,
        "tonic": 2,
        "postural": 3
    }
    
    sample_predictions = [0.125, 0.2, 0.375, 0.3]
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # replace below with neural network output once it's ready
        predictions_this_request = len(data)
        predictions = [None] * predictions_this_request
        
        for idx in range(predictions_this_request):
            if not (
                all([(isinstance(v, float) or isinstance(v, int)) for v in data[idx].values()])
                and set(data[idx]) == {"time", "accelx", "accely", "accelz", "gyrox", "gyroy", "gyroz", "distanceLeft", "distanceRight"}
            ):
                return JsonResponse({'error': 'Invalid data'}, status=400)
            
            current_data = data[idx]
            
            data_list = torch.tensor([[[
                current_data["time"],
                current_data["accelx"],
                current_data["accely"],
                current_data["accelz"],
                current_data["gyrox"],
                current_data["gyroy"],
                current_data["gyroz"],
                current_data["distanceLeft"],
                current_data["distanceRight"],
            ]]], dtype=torch.float32)
            
            prediction = list(map(float, live_demo_prediction.loaded_model(data_list)[0]))
            
            prediction_dict = {
                "Normal": prediction[label_map["normal"]],
                "Tremor": prediction[label_map["tremor"]],
                "Tonic": prediction[label_map["tonic"]],
                "Postural": prediction[label_map["postural"]],
            }
            
            # print(prediction_dict)
            
            predictions[idx] = prediction_dict
        
        return JsonResponse(dict(zip(range(predictions_this_request), predictions)))
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

live_demo_prediction.loaded_model = load_model()


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
