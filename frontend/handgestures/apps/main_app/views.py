from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, resolve, NoReverseMatch
from django.http import JsonResponse, HttpResponse
from django import forms
from django.views.decorators.csrf import csrf_exempt
from .models.LSTMCNN import CNNLSTM
from .models.Preprocess import ProcessCWTSingle

import json
import csv

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
from django.db import connections #import for Django's Database Backend
from django.db.utils import OperationalError, DatabaseError, InterfaceError
import mysql.connector.errorcode as errorcode

#uses Django's Database Backend instead of raw MySQL connector (Implemented 6-8-2025) 
def get_mysql_connection():
    try:
        connection = connections['mysql']
        cursor = connection.cursor()
        return connection, cursor, ""
    except OperationalError as err:
        #for handling specific MySQL error codes
        error_message = str(err)
        
        #access denied (authentication) errors
        if "Access denied" in error_message or "authentication" in error_message.lower():
            return None, None, "Something is wrong with the user name or password"
        
        #database doesn't exist errors
        elif "Unknown database" in error_message or "database does not exist" in error_message.lower():
            return None, None, "Database does not exist"
        
        #connection/SSL errors
        elif "Lost connection" in error_message or "SSL" in error_message or "EOF occurred" in error_message:
            return None, None, f"MySQL connection/SSL error: {str(err)}"
        
        #host/network errors
        elif "Can't connect" in error_message or "timeout" in error_message.lower():
            return None, None, f"MySQL network error: {str(err)}"
        
        #generic operational error
        else:
            return None, None, f"MySQL operational error: {str(err)}"
            
    except DatabaseError as err:
        return None, None, f"MySQL database error: {str(err)}"
        
    except InterfaceError as err:
        return None, None, f"MySQL interface error: {str(err)}"
        
    except Exception as err:
        return None, None, f"Database connection error: {str(err)}"


# Import your models for this application
# from .models import Course, Description, Comment

# Import models from different applications
# from ..<different_app>.models import <table_name>


def load_model():
    model_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static',
        'main_app',
        'data',
        'NeuroTech-1.pt'
    )
    # Label File location
    labels_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static',
        'main_app',
        'data',
        'label_map.json'
    )
    # Initial device state
    device = torch.device("cpu")
    # Load the file to get the labels
    with open(labels_file_path, 'r') as f:
        label_dict = json.load(f)
    # Initialize the model, so we can send it the weights
    model = CNNLSTM(input_channels=6, num_classes=len(label_dict)).to(device)
    # Load the data weights into the model
    model.load_state_dict(torch.load(model_file_path, weights_only=False, map_location=device))
    
    model.eval()
    
    return model

def preprocess_cwt():
    """
    This function will preprocess a dataset with CWT,
    so that it can be used in model evaluation and predictions

    Returns:
        dict: This is a dictionary of the probabilities for the labels
    """
    # Label File location
    labels_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static',
        'main_app',
        'data',
        'label_map.json'
    )
    # Initial device state
    device = torch.device("cpu")
    
    # Get label data
    with open(labels_file_path, 'r') as f:
        label_dict = json.load(f)
    # Reverse label dict
    id_to_label_name = {v: k for k, v in label_dict.items()}
    index_to_label_id = {i: lid for i, lid in enumerate(sorted(label_dict.values()))}
    label_id_to_index = {lid: i for i, lid in index_to_label_id.items()}
    
    # Set the file path for the CSV
    csv_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static',
        'main_app',
        'data',
        'tonic',
        'standing',
        'Josh59.csv'
    )
    
    # Proprocess the single file for inference
    cwt_processor = ProcessCWTSingle()
    result = cwt_processor.predict_from_csv(
        csv_path=csv_file_path,
        model=live_demo_prediction.loaded_model,
        label_dict=label_dict,
        index_to_label_id=index_to_label_id,
        label_id_to_index=label_id_to_index,
        id_to_label_name=id_to_label_name
    )
    # Get the probabilities and return them
    probabilities = result.get('probabilities', None)
    return probabilities

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
    
    connection, cursor, connection_error = get_mysql_connection()
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
    
    connection, cursor, connection_error = get_mysql_connection()
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


def demo_csv_data_update(request): #(added 6-5-2025 SCRUM Sprint 9)
    """
    Calculate averages and max values from the specific CSV file loaded in demo.html
    This replaces database queries with direct CSV file processing
    """
    
    #path to the CSV file that's loaded in demo.html
    csv_file_path = os.path.join(
        settings.BASE_DIR, 
        'apps', 
        'main_app', 
        'static', 
        'main_app', 
        'data',
        'tonic',
        'standing',
        'Josh59.csv'
    )
    
    file_error = ""
    data_points = 0
    
    #initializes variables with default values
    accel_x_values = []
    accel_y_values = []
    accel_z_values = []
    gyro_x_values = []
    gyro_y_values = []
    gyro_z_values = []
    
    try:
        with open(csv_file_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                try:
                    #extracts values from CSV
                    accel_x = float(row.get('AccelX(g)', 0))
                    accel_y = float(row.get('AccelY(g)', 0))
                    accel_z = float(row.get('AccelZ(g)', 0))
                    gyro_x = float(row.get('GyroX(deg/s)', 0))
                    gyro_y = float(row.get('GyroY(deg/s)', 0))
                    gyro_z = float(row.get('GyroZ(deg/s)', 0))
                    
                    accel_x_values.append(accel_x)
                    accel_y_values.append(accel_y)
                    accel_z_values.append(accel_z)
                    gyro_x_values.append(gyro_x)
                    gyro_y_values.append(gyro_y)
                    gyro_z_values.append(gyro_z)
                    
                    data_points += 1
                    
                except (ValueError, KeyError) as e:
                    continue #skips invalid rows
                    
    except FileNotFoundError:
        file_error = f"CSV file not found: {csv_file_path}"
    except Exception as e:
        file_error = f"Error reading CSV file: {str(e)}"
    
    #calculates averages (same logic as Jack's version for demo_page_update)
    avg_accel_x = sum(accel_x_values) / len(accel_x_values) if accel_x_values else 0.0
    avg_accel_y = sum(accel_y_values) / len(accel_y_values) if accel_y_values else 0.0
    avg_accel_z = sum(accel_z_values) / len(accel_z_values) if accel_z_values else 0.0
    avg_rotation_x = sum(gyro_x_values) / len(gyro_x_values) if gyro_x_values else 0.0
    avg_rotation_y = sum(gyro_y_values) / len(gyro_y_values) if gyro_y_values else 0.0
    avg_rotation_z = sum(gyro_z_values) / len(gyro_z_values) if gyro_z_values else 0.0
    
    #calculates max absolute values (same logic as Jack's version for demo_page_update)
    max_accel_x = max([abs(x) for x in accel_x_values]) if accel_x_values else 0.0
    max_accel_y = max([abs(y) for y in accel_y_values]) if accel_y_values else 0.0
    max_accel_z = max([abs(z) for z in accel_z_values]) if accel_z_values else 0.0
    max_gyro_x = max([abs(x) for x in gyro_x_values]) if gyro_x_values else 0.0
    max_gyro_y = max([abs(y) for y in gyro_y_values]) if gyro_y_values else 0.0
    max_gyro_z = max([abs(z) for z in gyro_z_values]) if gyro_z_values else 0.0
    
    #formats response
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
        "file_error": file_error,
        "data_points": data_points,
    }
    
    return JsonResponse(demo_data)




# TODO: consider if this needs to use CSRF tokens
# TODO: send data to the neural network once it's made.
@csrf_exempt
def live_demo_prediction(request):
    # Default get request
    if request.method == 'GET':

        results = preprocess_cwt()
        print(results)
        
        return JsonResponse(results)
    
    # This needs to be updated. This is a TODO
    elif request.method == 'POST':
        data = json.loads(request.body)    
        
        
        # # replace below with neural network output once it's ready
        # predictions_this_request = len(data)
        # predictions = [None] * predictions_this_request
        
        # for idx in range(predictions_this_request):
        #     if not (
        #         all([(isinstance(v, float) or isinstance(v, int)) for v in data[idx].values()])
        #         and set(data[idx]) == {"time", "accelx", "accely", "accelz", "gyrox", "gyroy", "gyroz", "distanceLeft", "distanceRight"}
        #     ):
        #         return JsonResponse({'error': 'Invalid data'}, status=400)
            
        #     current_data = data[idx]
            
        #     data_list = torch.tensor([[[
        #         current_data["time"],
        #         current_data["accelx"],
        #         current_data["accely"],
        #         current_data["accelz"],
        #         current_data["gyrox"],
        #         current_data["gyroy"],
        #         current_data["gyroz"],
        #         current_data["distanceLeft"],
        #         current_data["distanceRight"],
        #     ]]], dtype=torch.float32)
            
        #     prediction = list(map(float, nn.functional.softmax(live_demo_prediction.loaded_model(data_list)[0], dim=-1)))
            
        #     prediction_dict = {
        #         "Normal": prediction[label_map["normal"]],
        #         "Tremor": prediction[label_map["tremor"]],
        #         "Tonic": prediction[label_map["tonic"]],
        #         "Postural": prediction[label_map["postural"]],
        #     }
            
        #     # print(prediction_dict)
            
        #     predictions[idx] = prediction_dict
        
        return JsonResponse(dict(zip(range(predictions_this_request), predictions)))
    
    else: return JsonResponse({'error': 'Invalid request'}, status=400)

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


@csrf_exempt
def calculate_dynamic_thresholds(request):
    """Calculate dynamic thresholds for major spike detection only, avoiding false positives from normal variations"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        import numpy as np
        data = json.loads(request.body)
        
        thresholds = {}
        
        #accelerometer data
        for axis, values in data.get('accel', {}).items():
            if values:
                signal = np.array(values)
                mean_val = np.mean(signal)
                std_val = np.std(signal)
                
                #uses 4 standard deviations for major spike detection only
                #also ensures minimum threshold of 10% of mean to avoid tiny variations
                threshold_range = max(4.0 * std_val, abs(mean_val) * 0.1)
                
                thresholds[f'Accel {axis.upper()}'] = {
                    'min': float(mean_val - threshold_range),
                    'max': float(mean_val + threshold_range)
                }
        
        #gyroscope data
        for axis, values in data.get('gyro', {}).items():
            if values:
                signal = np.array(values)
                mean_val = np.mean(signal)
                std_val = np.std(signal)
                
                #gyro uses 3.5 standard deviations
                threshold_range = 3.5 * std_val
                
                thresholds[f'Gyro {axis.upper()}'] = {
                    'min': float(mean_val - threshold_range),
                    'max': float(mean_val + threshold_range)
                }
        
        #processes ultrasonic data using percentiles 
        for sensor, values in data.get('ultrasonic', {}).items():
            if values:
                signal = np.array(values)
                
                #uses 1st and 99th percentiles for major spike detection only
                #captures only extreme outliers in distance measurements
                percentile_low = np.percentile(signal, 1)
                percentile_high = np.percentile(signal, 99)
                
                sensor_name = 'Left Distance (cm)' if sensor == 'left' else 'Right Distance (cm)'
                thresholds[sensor_name] = {
                    'min': float(percentile_low),
                    'max': float(percentile_high)
                }
        
        return JsonResponse({'thresholds': thresholds})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
