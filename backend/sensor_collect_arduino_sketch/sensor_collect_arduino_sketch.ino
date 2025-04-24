/*
 * Hands Gesture Sensor Collection Sketch
 * Collects data from these sensors:
 * MPU-6050 (Accelerometer and Gyroscope)
 * HC-SR04 (Ultrasonics)
 * SPI (SD-Card)
 *
 *
 * by Joshua Summers
 */

#include <MPU6050.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>

// Pins for board to sensor connection
#define TRIG_PIN_LEFT 9
#define ECHO_PIN_LEFT 10
#define TRIG_PIN_RIGHT 5
#define ECHO_PIN_RIGHT 6
#define SD_CS_PIN 4
#define DATA_FILENAME "data.csv"

// Initialize variables
MPU6050 mpu; // MPU object
File dataFile; // File object
int count; // counter

// Setup Function (one startup)
void setup() {
    // Start the serial console session
    Serial.begin(115200); // Ensure maximum speed of serial communications at 115.2K (UART max)
    // Initialize I2C sensors
    Wire.begin();
    // Initialize MPU6050
    mpu.initialize();
    mpu.CalibrateGyro();  // Calibrate gyro
    // Set ranges (do after calibration)
    mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
    mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_250);

    // Initialize HC-SR04 Left
    pinMode(TRIG_PIN_LEFT, OUTPUT);
    pinMode(ECHO_PIN_LEFT, INPUT);

    // Initialize HC-SR04 Right
    pinMode(TRIG_PIN_RIGHT, OUTPUT);
    pinMode(ECHO_PIN_RIGHT, INPUT);

    // Initialize SD card with detailed error reporting
    Serial.println("Initializing SD card...");
    // Test SD-Card
    if (!SD.begin(SD_CS_PIN)) {
      Serial.println("\nSD initialization failed!");
      Serial.println("Possible causes:");
      // New error checking method
      if (!SD.exists("/")) {
        Serial.println("- No card detected");
      } else {
        File testFile = SD.open("test.txt", FILE_WRITE);
        if (!testFile) {
          Serial.println("- Cannot create files (might be write-protected)");
        } else {
          testFile.close();
          SD.remove("test.txt");
          Serial.println("- Unknown error (card detected but initialization failed)");
        }
      }
      while(1);
    }
    Serial.println("initialization done.");

    // Ensure clean-up of data.csv
    if (SD.exists("data.csv")) { 
      SD.remove("data.csv");
    }
    // Create new CSV file
    dataFile = SD.open("data.csv", FILE_WRITE);
    if (dataFile) {
      dataFile.println("Timestamp(ms),AccelX(g),AccelY(g),AccelZ(g),GyroX(deg/s),GyroY(deg/s),GyroZ(deg/s),DistanceLeft(cm),DistanceRight(cm)");
      dataFile.close();
      Serial.println("CSV header written");
    } else {
      Serial.println(dataFile);
      Serial.println("Error opening file!");
    }
    // Initialize counter
    count = 0;
}

// Runs continually (final delay creates interval)
void loop() {
    // Get MPU-6050 Data
    // Get raw sensor data (accel + gyro)
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    // Get scaled values
    float axt = ax / 16384.0;
    float ayt = ay / 16384.0;
    float azt = az / 16384.0;
    float gxt = gx / 131.0;
    float gyt = gy / 131.0;
    float gzt = gz / 131.0;
    
    // Get HC-SR04 Data Left
    long duration_left, distance_left;
    digitalWrite(TRIG_PIN_LEFT, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN_LEFT, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN_LEFT, LOW);
    // Get the values and calculate distance
    duration_left = pulseIn(ECHO_PIN_LEFT, HIGH);
    distance_left = duration_left * 0.034 / 2;  // Convert to cm

    // Get HC-SR04 Data Right
    long duration_right, distance_right;
    digitalWrite(TRIG_PIN_RIGHT, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN_RIGHT, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN_RIGHT, LOW);
    // Get the values and calculate distance
    duration_right = pulseIn(ECHO_PIN_RIGHT, HIGH);
    distance_right = duration_right * 0.034 / 2;  // Convert to cm

    // Open CSV file and append data
    dataFile = SD.open("data.csv", FILE_WRITE);
    if (dataFile && count <= 500) { // temporary capture of only 500 rows
      dataFile.print(millis()); dataFile.print(",");
      dataFile.print(axt, 3); dataFile.print(",");
      dataFile.print(ayt, 3); dataFile.print(",");
      dataFile.print(azt, 3); dataFile.print(",");
      dataFile.print(gxt, 3); dataFile.print(",");
      dataFile.print(gyt, 3); dataFile.print(",");
      dataFile.print(gzt, 3); dataFile.print(",");
      dataFile.print(distance_left, 1); dataFile.println();
      dataFile.print(distance_right, 1); dataFile.println();
      dataFile.close();
      if (count % 100 == 0) Serial.println("Wrote 100 rows into CSV. Continuing... ");
      if (count >= 500) Serial.println("Wrote 500 rows into CSV: ");
      count++;
    }
    // 5 microsecond delay
    delay(500);
}