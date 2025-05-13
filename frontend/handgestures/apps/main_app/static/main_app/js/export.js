/*
Logic for exporting 'data export' table data to CSV file on live demo page.
Also contains logic for logging data to the table from the live demo page.
Implemented 5-12-2025 (SCRUM Sprint 6)
*/

//variables stored as references to DOM elements
const logDataBtn = document.getElementById('logDataBtn');
const exportCSVBtn = document.getElementById('exportCSVBtn');
const exportTableBody = document.querySelector('.card table tbody');

//variable to store table rows in memory for easy CSV export
let exportTableRows = [];

//gets the latest data point from all charts based on the timestamp that 'log data' button is clicked
function getLatestDataAllCharts() {
    
    //initialize row object to store data in 'data export' table
    let row = {
        timestamp: null,
        accelX: null,
        accelY: null,
        accelZ: null,
        gyroX: null,
        gyroY: null,
        gyroZ: null,
        distance: null
    };
    
    //Accelerometer
    const accLen = accelerometerChart.data.labels.length;
    if (accLen > 0) {
        row.timestamp = accelerometerChart.data.labels[accLen - 1];
        row.accelX = accelerometerChart.data.datasets[0].data[accLen - 1];
        row.accelY = accelerometerChart.data.datasets[1].data[accLen - 1];
        row.accelZ = accelerometerChart.data.datasets[2].data[accLen - 1];
    }
    //Gyroscope
    const gyroLen = gyroscopeChart.data.labels.length;
    if (gyroLen > 0) {
        row.timestamp = gyroscopeChart.data.labels[gyroLen - 1];
        row.gyroX = gyroscopeChart.data.datasets[0].data[gyroLen - 1];
        row.gyroY = gyroscopeChart.data.datasets[1].data[gyroLen - 1];
        row.gyroZ = gyroscopeChart.data.datasets[2].data[gyroLen - 1];
    }
    //Ultrasonic
    const ultraLen = ultrasonicChart.data.labels.length;
    if (ultraLen > 0) {
        row.timestamp = ultrasonicChart.data.labels[ultraLen - 1];
        row.distance = ultrasonicChart.data.datasets[0].data[ultraLen - 1];
    }
    return row;
}

//add row(s) to export table
function addRowsToTable(row) {
    //save to memory for CSV export
    exportTableRows.push(row);

    //adds to table in DOM
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td>${row.timestamp}</td>
        <td>${row.accelX}</td>
        <td>${row.accelY}</td>
        <td>${row.accelZ}</td>
        <td>${row.gyroX}</td>
        <td>${row.gyroY}</td>
        <td>${row.gyroZ}</td>
        <td>${row.distance}</td>
    `;
    exportTableBody.appendChild(tr);
}

//Log Data event listener (adds data to the table from all charts based on the timestamp log data button is clicked)
logDataBtn.addEventListener('click', function() {
    const row = getLatestDataAllCharts();
    if (!row.timestamp) {
        alert('No data to log!');
        return;
    }
    addRowsToTable(row);
});

//export CSV event listener
exportCSVBtn.addEventListener('click', function() {
    if (exportTableRows.length === 0) {
        alert('No data to export!');
        return;
    }
    //CSV header
    let csvContent = 'Timestamp,AccelX,AccelY,AccelZ,GyroX,GyroY,GyroZ,Distance\n';
    exportTableRows.forEach(row => {
        csvContent += `${row.timestamp},${row.accelX},${row.accelY},${row.accelZ},${row.gyroX},${row.gyroY},${row.gyroZ},${row.distance}\n`;
    });


    /*
    download as CSV via blob (binary large object)
    Blob is a built-in object in JavaScript that represents immutable binary data.
    It is used to store various types of data.
    */
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'exported_data.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});
