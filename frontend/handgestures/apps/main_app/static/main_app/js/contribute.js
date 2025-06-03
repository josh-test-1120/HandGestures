/*
Contribute button functionality for live demo page
Handles modal display, template download, and Azure blob upload
Implemented 5-26-2025 SCRUM Sprint 7
*/

//CSV column validation function
function validateCSVColumns(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length === 0) {
        return { isValid: false, error: 'CSV file is empty', missingColumns: [] };
    }
    
    const header = lines[0].split(',');
    const requiredColumns = [
        'Timestamp(ms)',
        'AccelX(g)',
        'AccelY(g)', 
        'AccelZ(g)',
        'GyroX(deg/s)',
        'GyroY(deg/s)',
        'GyroZ(deg/s)',
        'DistanceLeft(cm)',
        'DistanceRight(cm)'
    ];
    
    const missingColumns = [];
    
    for (const column of requiredColumns) {
        if (header.indexOf(column) === -1) {
            missingColumns.push(column);
        }
    }
    
    return {
        isValid: missingColumns.length === 0,
        error: missingColumns.length > 0 ? 'Invalid CSV format detected' : null,
        missingColumns: missingColumns
    };
}

//Event: Contribute button event listener - show modal instead of direct download
document.addEventListener('DOMContentLoaded', function() {
    const contributeBtn = document.getElementById('contributeBtn');
    
    if (contributeBtn) {
        contributeBtn.addEventListener('click', function() {
            const contributeModal = new bootstrap.Modal(document.getElementById('contributeModal'));
            contributeModal.show();
        });
    }

    //Event: Download button in modal
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', function() {
            const link = document.createElement('a');
            link.href = '/download-template/';
            link.download = 'template.csv';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    //Event: Upload button in modal
    const uploadDataBtn = document.getElementById('uploadDataBtn');
    if (uploadDataBtn) {
        uploadDataBtn.addEventListener('click', function() {
            document.getElementById('contributeFileInput').click();
        });
    }

    //Event: Once file input is changed, validate file type and upload to Azure blob storage
    const contributeFileInput = document.getElementById('contributeFileInput');
    if (contributeFileInput) {
        contributeFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            //CSV file type validation
            if (!file.name.toLowerCase().endsWith('.csv')) {
                document.getElementById('uploadError').style.display = 'block';
                document.getElementById('uploadErrorMessage').textContent = 'Please select a valid CSV file.';
                return;
            }

            //hides previous messages
            document.getElementById('uploadSuccess').style.display = 'none';
            document.getElementById('uploadError').style.display = 'none';
            
            //reads and validate CSV content before uploading
            const reader = new FileReader();
            reader.onload = function(evt) {
                try {
                    //validates CSV columns
                    const validation = validateCSVColumns(evt.target.result);
                    if (!validation.isValid) {
                        document.getElementById('uploadError').style.display = 'block';
                        document.getElementById('uploadErrorMessage').textContent = 
                            `${validation.error}. Please download the template to ensure you have the correct CSV format.`;
                        return;
                    }
                    
                    //case: validation passes and proceeds with upload
                    proceedWithUpload(file);
                    
                } catch (err) {
                    document.getElementById('uploadError').style.display = 'block';
                    document.getElementById('uploadErrorMessage').textContent = 'Error reading CSV file: ' + err.message;
                }
            };
            reader.readAsText(file);
        });
    }
    
    //function to handle the actual upload after validation
    function proceedWithUpload(file) {
        //shows progress
        document.getElementById('uploadProgress').style.display = 'block';
        const progressBar = document.getElementById('uploadProgressBar');
        
        //creates FormData for file upload
        const formData = new FormData();
        formData.append('csv_file', file);
        formData.append('container', 'public-contributions');
        
        //CSRF token from meta tag
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        //simulates progress animation
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressBar.style.width = progress + '%';
        }, 200);

        //uploads to Azure blob storage
        fetch('/upload-contribution/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken || ''
            }
        })
        .then(response => {
            clearInterval(progressInterval);
            progressBar.style.width = '100%';
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('uploadProgress').style.display = 'none';
            
            if (data.success) {
                document.getElementById('uploadSuccess').style.display = 'block';
                //resets file input
                document.getElementById('contributeFileInput').value = '';
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            clearInterval(progressInterval);
            document.getElementById('uploadProgress').style.display = 'none';
            document.getElementById('uploadError').style.display = 'block';
            document.getElementById('uploadErrorMessage').textContent = error.message || 'Failed to upload data. Please try again.';
        });
    }
}); 