/**
 * Shared JavaScript functions for charts in demo.html and live_demo.html
 * Created 5-5-2025 
 */


//parse CSV text to arrays
function parseCSV(text, data) {
  //split lines and extract header indices
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(',');
  const idx = {
    time: header.indexOf('Timestamp(ms)'),
    ax: header.indexOf('AccelX(g)'),
    ay: header.indexOf('AccelY(g)'),
    az: header.indexOf('AccelZ(g)'),
    gx: header.indexOf('GyroX(deg/s)'),
    gy: header.indexOf('GyroY(deg/s)'),
    gz: header.indexOf('GyroZ(deg/s)'),
    distLeft: header.indexOf('DistanceLeft(cm)'),
    distRight: header.indexOf('DistanceRight(cm)')
  };
  let t0 = null;
  //initialize arrays for each column in CSV
  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(',');
    if (row.length < header.length) continue;
    const t = parseInt(row[idx.time]);
    if (t0 === null) t0 = t;
    //convert timestamp to seconds and fill arrays
    data.time.push(((t - t0) / 1000).toFixed(2));
    data.accel.x.push(parseFloat(row[idx.ax]));
    data.accel.y.push(parseFloat(row[idx.ay]));
    data.accel.z.push(parseFloat(row[idx.az]));
    data.gyro.x.push(parseFloat(row[idx.gx]));
    data.gyro.y.push(parseFloat(row[idx.gy]));
    data.gyro.z.push(parseFloat(row[idx.gz]));
    
    //handles zero values for ultrasonic sensors
    const leftDist = parseFloat(row[idx.distLeft]);
    const rightDist = parseFloat(row[idx.distRight]);
    data.ultrasonicLeft.push(leftDist === 0 ? null : leftDist);
    data.ultrasonicRight.push(rightDist === 0 ? null : rightDist);
  }
}

function parsePredictions(text, data) {
  //add predictions to data
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(',');
  const idx = {
    time: header.indexOf('Timestamp(ms)'),
    shaking: header.indexOf('Shaking'),
    posture: header.indexOf('Posture'),
    fall: header.indexOf('Fall'),
    normal: header.indexOf('Normal'),
  };
  //add predictions to data
  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(',');
    if (row.length < header.length) continue;
    data.prediction.shaking.push(parseFloat(row[idx.shaking]));
    data.prediction.posture.push(parseFloat(row[idx.posture]));
    data.prediction.fall.push(parseFloat(row[idx.fall]));
    data.prediction.normal.push(parseFloat(row[idx.normal]));
  }
}

//Chart.js setup
function setupCharts(data) {
  //Accelerometer
  const accCtx = document.getElementById('accelerometerChart').getContext('2d');
  const accelerometerChart = new Chart(accCtx, {
    type: 'line',
    data: {
      labels: data.time,
      datasets: [
        { label: 'Accel X', data: data.accel.x, borderColor: 'rgba(52, 152, 219, 1)', backgroundColor: 'rgba(52, 152, 219, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Accel Y', data: data.accel.y, borderColor: 'rgba(39, 174, 96, 1)', backgroundColor: 'rgba(39, 174, 96, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Accel Z', data: data.accel.z, borderColor: 'rgba(231, 76, 60, 1)', backgroundColor: 'rgba(231, 76, 60, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Time (s)' }, ticks: { stepSize: 5, callback: v => v + 's' } },
        y: { beginAtZero: true }
      }
    }
  });

  //Gyroscope
  const gyroCtx = document.getElementById('gyroscopeChart').getContext('2d');
  const gyroscopeChart = new Chart(gyroCtx, {
    type: 'line',
    data: {
      labels: data.time,
      datasets: [
        { label: 'Gyro X', data: data.gyro.x, borderColor: 'rgba(155, 89, 182, 1)', backgroundColor: 'rgba(155, 89, 182, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Gyro Y', data: data.gyro.y, borderColor: 'rgba(241, 196, 15, 1)', backgroundColor: 'rgba(241, 196, 15, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Gyro Z', data: data.gyro.z, borderColor: 'rgba(26, 188, 156, 1)', backgroundColor: 'rgba(26, 188, 156, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Time (s)' }, ticks: { stepSize: 5, callback: v => v + 's' } },
        y: { beginAtZero: true }
      }
    }
  });

  //Ultrasonic
  const ultrasonicCtx = document.getElementById('ultrasonicChart').getContext('2d');
  const ultrasonicChart = new Chart(ultrasonicCtx, {
    type: 'line',
    data: {
      labels: data.time,
      datasets: [
        { 
          label: 'Left Distance (cm)', 
          data: data.ultrasonicLeft, 
          borderColor: 'rgba(39, 174, 96, 1)', 
          backgroundColor: 'rgba(39, 174, 96, 0.2)', 
          borderWidth: 1, 
          pointRadius: 2, 
          tension: 0.4 
        },
        { 
          label: 'Right Distance (cm)', 
          data: data.ultrasonicRight, 
          borderColor: 'rgba(231, 76, 60, 1)', 
          backgroundColor: 'rgba(231, 76, 60, 0.2)', 
          borderWidth: 1, 
          pointRadius: 2, 
          tension: 0.4 
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { 
          type: 'linear', 
          title: { 
            display: true, 
            text: 'Time (s)' 
          }, 
          ticks: { 
            stepSize: 5, 
            callback: v => v + 's' 
          }
        },
        y: { 
          beginAtZero: true,
          suggestedMax: 200,
          title: {
            display: true,
            text: 'Distance (cm)'
          }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          align: 'center'
        }
      }
    }
  });

  //Predictions
  const PredictionCtx = document.getElementById('predictionChart').getContext('2d');
  const predictionChart = new Chart(PredictionCtx, {
    type: 'line',
    data: {
      labels: data.time,
      datasets: [
        { label: 'Shaking', data: data.prediction.shaking, borderColor: 'rgba(255, 255, 0, 1)', backgroundColor: 'rgba(255, 255, 0, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Posture Change', data: data.prediction.posture, borderColor: 'rgba(255, 127, 0, 1)', backgroundColor: 'rgba(255, 127, 0, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Fall', data: data.prediction.fall, borderColor: 'rgba(255, 0, 0, 1)', backgroundColor: 'rgba(255, 0, 0, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
        { label: 'Normal', data: data.prediction.normal, borderColor: 'rgba(0, 255, 0, 1)', backgroundColor: 'rgba(0, 255, 0, 0.2)', borderWidth: 1, pointRadius: 2, tension: 0.4 },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Time (s)' }, ticks: { stepSize: 5, callback: v => v + 's' } },
        y: { beginAtZero: true }
      }
    }
  });

  //Helper functions to update value displays
  function updateAccValues(x, y, z) {
    document.getElementById('acc-x-value').textContent = x !== undefined ? x.toFixed(3) : '-';
    document.getElementById('acc-y-value').textContent = y !== undefined ? y.toFixed(3) : '-';
    document.getElementById('acc-z-value').textContent = z !== undefined ? z.toFixed(3) : '-';
  }

  function updateGyroValues(x, y, z) {
    document.getElementById('gyro-x-value').textContent = x !== undefined ? x.toFixed(3) : '-';
    document.getElementById('gyro-y-value').textContent = y !== undefined ? y.toFixed(3) : '-';
    document.getElementById('gyro-z-value').textContent = z !== undefined ? z.toFixed(3) : '-';
  }

  function updateUltrasonicValues(left, right) {
    document.getElementById('ultrasonic-left-value').textContent = left !== undefined ? left.toFixed(1) : '-';
    document.getElementById('ultrasonic-right-value').textContent = right !== undefined ? right.toFixed(1) : '-';
  }

  function updatePredictionValues(shaking, posture, fall, normal) {
    document.getElementById('shaking-percent').textContent = shaking !== undefined ? shaking.toFixed(3) : '-';
    document.getElementById('posture-percent').textContent = posture !== undefined ? posture.toFixed(3) : '-';
    document.getElementById('fall-percent').textContent = fall !== undefined ? fall.toFixed(3) : '-';
    document.getElementById('normal-percent').textContent = normal !== undefined ? normal.toFixed(3) : '-';
  }

  //Chart.js hover events for Accelerometer/Gyroscope/Ultrasonic
  accelerometerChart.options.onHover = function(event, chartElement) {
    if (chartElement.length > 0) {
      const idx = chartElement[0].index;
      updateAccValues(
        accelerometerChart.data.datasets[0].data[idx],
        accelerometerChart.data.datasets[1].data[idx],
        accelerometerChart.data.datasets[2].data[idx]
      );
    } else {
      updateAccValues();
    }
  };

  gyroscopeChart.options.onHover = function(event, chartElement) {
    if (chartElement.length > 0) {
      const idx = chartElement[0].index;
      updateGyroValues(
        gyroscopeChart.data.datasets[0].data[idx],
        gyroscopeChart.data.datasets[1].data[idx],
        gyroscopeChart.data.datasets[2].data[idx]
      );
    } else {
      updateGyroValues();
    }
  };

  ultrasonicChart.options.onHover = function(event, chartElement) {
    if (chartElement.length > 0) {
      const idx = chartElement[0].index;
      updateUltrasonicValues(
        ultrasonicChart.data.datasets[0].data[idx],
        ultrasonicChart.data.datasets[1].data[idx]
      );
    } else {
      updateUltrasonicValues();
    }
  };

  predictionChart.options.onHover = function(event, chartElement) {
    if (chartElement.length > 0) {
      const idx = chartElement[0].index;
      updatePredictionValues(
        predictionChart.data.datasets[0].data[idx],
        predictionChart.data.datasets[1].data[idx],
        predictionChart.data.datasets[2].data[idx],
        predictionChart.data.datasets[3].data[idx]
      );
    } else {
      updatePredictionValues();
    }
  };

  return { accelerometerChart, gyroscopeChart, ultrasonicChart, predictionChart };
} 