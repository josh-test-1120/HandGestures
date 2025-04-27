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
#include <avr/wdt.h>

// Pins for board to sensor connection
#define TRIG_PIN_LEFT 5
#define ECHO_PIN_LEFT 2
#define TRIG_PIN_RIGHT 6
#define ECHO_PIN_RIGHT 3
#define SD_CS_PIN 4
#define DATA_FILENAME "data1.csv"
#define PING_INTERVAL 50 // ms
#define MPU_INTERVAL 10 // ms

#define LIVE_DEBUG 1
#define LOOP_DELAY 500 // in milliseconds
#define LOOP_COUNT 25000 // span for collection

// Enum for Ultrasonic states
enum SonarState { IDLE, TRIGGERED, WAITING_ECHO, ECHO_RECEIVED };

// Initialize objects
MPU6050 mpu; // MPU object
//File dataFile; // File object

// Ultrasonic Sensors
SonarState leftState = IDLE, rightState = IDLE;
unsigned long leftEchoStart, rightEchoStart, lastPingTime;
float leftDist, rightDist;

// MPU-6050
unsigned long lastMPUTime = 0;
float accelX, accelY, accelZ, gyroX, gyroY, gyroZ;

// Looping
int count; // counter

void initMPU6050() {
    // Initialize MPU6050
    mpu.initialize();
    mpu.CalibrateGyro();  // Calibrate gyro
    // Set ranges (do after calibration)
    mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
    mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_250);
}

// Read the MPU-6050 sensors
void readMPU6050() {
  // Integer values for MPU sensors
  int16_t ax, ay, az, gx, gy, gz;
  // Get the data from sensors
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  // Scale factors (±2g = 16384 LSB/g, ±250°/s = 131 LSB/°/s)
  const float ACCEL_SCALE = 1.0 / 16384.0;
  const float GYRO_SCALE = 1.0 / 131.0;
  // Scale the acceleration values
  // Sensor	        Scale Factor  (FS = ±2g, ±250°/s) 	Formula
  // Accelerometer	16384 LSB/g	                        (raw - offset) / 16384.0
  accelX = ax * ACCEL_SCALE;
  accelY = ay * ACCEL_SCALE;
  accelZ = az * ACCEL_SCALE;
  // Scale the gyroscope values
  // Sensor	        Scale Factor  (FS = ±2g, ±250°/s) 	Formula
  // Gyroscope	    131 LSB/°/s	                        (raw - offset) / 131.0
  gyroX = gx * GYRO_SCALE;
  gyroY = gy * GYRO_SCALE;
  gyroZ = gz * GYRO_SCALE;
}

void triggerUltrasonic(uint8_t trigPin, SonarState *state) {
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  *state = TRIGGERED;
}

void checkEcho(uint8_t echoPin, SonarState *state, unsigned long *echoStart, float *distance) {
  // Add a timeout (e.g., 30ms max for HC-SR04)
  const unsigned long TIMEOUT_US = 30000UL;

  if (*state == TRIGGERED && digitalRead(echoPin) == HIGH) {
    *echoStart = micros();
    *state = WAITING_ECHO;
  }
  else if (*state == WAITING_ECHO) {
    if (digitalRead(echoPin) == LOW) {
      unsigned long duration = micros() - *echoStart;
      
      if (LIVE_DEBUG) {
        // Serial.print("Duration (us) from pin "); Serial.print(echoPin); Serial.print(": "); Serial.println(duration);
        Serial.println(duration);
      }

      *distance = duration / 58.0; // Convert to cm
      *state = ECHO_RECEIVED;
    }
    else if (micros() - *echoStart > TIMEOUT_US) {
      // Timeout: No ECHO pulse detected
      if (LIVE_DEBUG && count % 1000 == 0) {
        // Serial.print("Timeout on pin ");
        // Serial.println(echoPin);
      }
      *distance = 0.0; // Indicate failure
      *state = IDLE;
    }
  }

  if (LIVE_DEBUG && *state == ECHO_RECEIVED) {
    //Serial.println(*distance);
    //Serial.println("Distance from pin ");
    //Serial.print(echoPin);
    //Serial.print(": ");
    Serial.println(*distance);
    //Serial.println(" cm");
  }
}

// void checkEcho(uint8_t echoPin, SonarState *state, unsigned long *echoStart, float *distance) {
//   if (*state == TRIGGERED && digitalRead(echoPin) == HIGH) {
//     *echoStart = micros();
//     *state = WAITING_ECHO;
//   }
//   else if (*state == WAITING_ECHO && digitalRead(echoPin) == LOW) {
//     if (LIVE_DEBUG) {
//       Serial.print("This is the duration from the ");
//       Serial.print(echoPin);
//       Serial.print(": ");
//       Serial.println(*echoStart);
//     }
//     *distance = (micros() - *echoStart) / 58.0; // Convert to cm
//     *state = ECHO_RECEIVED;
//   }
//   if (LIVE_DEBUG) {
//     Serial.print("This is the distance from the ");
//     Serial.print(echoPin);
//     Serial.print(": ");
//     Serial.println(*distance);
//   }
// }

bool verifySDHardware() {
    // delay(100);
    // SPI.beginTransaction(SPISettings(4e6, MSBFIRST, SPI_MODE0));
    // Initialize test result
    bool test = true;
    // Initialize SD card with detailed error reporting
    Serial.println("Initializing SD card..."); Serial.flush();
    // noInterrupts();          // Disable interrupts during SD access
    // SPI.beginTransaction(SPISettings(4e6, MSBFIRST, SPI_MODE0));
    // Test SD-Card
    if (!SD.begin(SD_CS_PIN)) {
      Serial.println("\nSD initialization failed!");  Serial.flush();
      Serial.println("Possible causes:");  Serial.flush();
      // New error checking method
      if (!SD.exists("/")) {
        Serial.println("- No card detected");  Serial.flush();
        test = false;
      } else {
        File testFile = SD.open("test.txt", FILE_WRITE);
        if (!testFile) {
          Serial.println("- Cannot create files (might be write-protected)");  Serial.flush();
          test = false;
        } else {
          SD.remove("test.txt");
          Serial.println("- Unknown error (card detected but initialization failed)");  Serial.flush();
          test = false;
        }
        testFile.close();
      }
    }
    // File dataFile = SD.open(DATA_FILENAME, FILE_WRITE);
    // Serial.println("Files on SD card:");
    // File file = dataFile.openNextFile();

    // while (file) {
    //   if (file.isDirectory()) {
    //     Serial.print("DIR: ");
    //   } else {
    //     Serial.print("FILE: ");
    //   }
    //   Serial.print(file.name());
    //   Serial.print("\tSize: ");
    //   Serial.println(file.size());
    //   file = dataFile.openNextFile();
    // }
    // file.close();
    // dataFile.close();

    return test;
}

void initDataFile() {
    Serial.flush(); 
    // noInterrupts();          // Disable interrupts during SD access
    //SPI.beginTransaction(SPISettings(4e6, MSBFIRST, SPI_MODE0));
    delay(100);
    // SPI.beginTransaction(SPISettings(4e6, MSBFIRST, SPI_MODE0));
    // Ensure clean-up of data.csv
    if (SD.exists(DATA_FILENAME)) { 
      SD.remove(DATA_FILENAME);
    }

    //Serial.println(SD.begin(SD_CS_PIN));
    
    // Create new CSV file
    File dataFile = SD.open(DATA_FILENAME, FILE_WRITE);
    
    if (dataFile) {
      dataFile.println("Timestamp(ms),AccelX(g),AccelY(g),AccelZ(g),GyroX(deg/s),GyroY(deg/s),GyroZ(deg/s),DistanceLeft(cm),DistanceRight(cm)");
      dataFile.close();
      Serial.println("CSV header written"); Serial.flush();
    } else {
      Serial.print("Data File details: ");
      Serial.flush();
      Serial.println(dataFile);
      Serial.flush();
      Serial.println("Error opening " DATA_FILENAME);
      Serial.flush();
      exit(0);
    }
    //SPI.endTransaction();
    // interrupts();
    // SPI.endTransaction();
}

void writeToSDCard(float leftDist, float rightDist, float ax, float ay, float az, float gx, float gy, float gz) {
  // Get the current timestamp
  unsigned long currentTS = millis();
  // WatchDog Reset
  wdt_reset();
  Serial.flush();
  // Open the Data File
  File dataFile = SD.open(DATA_FILENAME, FILE_WRITE);
  // Write a new row to the file
  if (dataFile && count <= LOOP_COUNT) { // temporarily capture only 500 rows
      dataFile.print(currentTS); dataFile.print(",");
      dataFile.print(ax, 3); dataFile.print(",");
      dataFile.print(ay, 3); dataFile.print(",");
      dataFile.print(az, 3); dataFile.print(",");
      dataFile.print(gx, 3); dataFile.print(",");
      dataFile.print(gy, 3); dataFile.print(",");
      dataFile.print(gz, 3); dataFile.print(",");
      dataFile.print(leftDist, 1); dataFile.print(",");
      dataFile.print(rightDist, 1); dataFile.println();
      dataFile.close();
      if (count >= LOOP_COUNT) Serial.println("Wrote 25000 rows into CSV: ");
      if (count % 1000 == 0) Serial.println("Wrote 1000 rows into CSV. Continuing... ");
      if (count % 1000 == 0) {
        Serial.print("This is the left distance: ");
        Serial.println(leftDist);
        Serial.print("This is the right distance: ");
        Serial.println(rightDist);
      }
      // Output Debug
      //Serial.flush();
      if (LIVE_DEBUG && count % 1000 == 0) {
        //Serial.flush();
        //Serial.println("Timestamp(ms), AccelX(g), AccelY(g), AccelZ(g), GyroX(deg/s), GyroY(deg/s), GyroZ(deg/s), DistanceLeft(cm), DistanceRight(cm)");
        // Serial.print(currentTS); Serial.print(", "); Serial.print(ax, 3); Serial.print(", "); Serial.print(ay, 3); Serial.print(", "); Serial.print(az, 3); Serial.print(", "); Serial.flush();
        // Serial.print(gx, 3); Serial.print(", "); Serial.print(gy, 3); Serial.print(", "); Serial.print(gz, 3); Serial.print(", "); Serial.print(leftDist, 3); Serial.flush();
        // Serial.print(", "); Serial.println(rightDist, 3); Serial.flush();
      }
      count++;
  }
}

// Setup Function (one startup)
void setup() {
    // Start the serial console session
    Serial.begin(9600);
    //Serial.begin(115200); // Ensure maximum speed of serial communications at 115.2K (UART max)
    // Initialize I2C sensors
    Wire.begin();
    // Initalize MPU-6050 sensor
    initMPU6050();
    // Initlaize the SD-Card Hardware
    bool sdReady = verifySDHardware();
    if (sdReady) Serial.println("initialization done.");
    else exit(0);
    //delay(50);
    // Initialize HC-SR04 Left
    pinMode(TRIG_PIN_LEFT, OUTPUT);
    pinMode(ECHO_PIN_LEFT, INPUT);
    // Initialize HC-SR04 Right
    pinMode(TRIG_PIN_RIGHT, OUTPUT);
    pinMode(ECHO_PIN_RIGHT, INPUT);
    // Initalize distances
    leftDist, rightDist = 0;
    // Initialize Data File
    initDataFile();
    // Initialize WatchDog
    wdt_enable(WDTO_2S);
    // Initialize counter
    count = 1;
}

// Runs continually (final delay creates interval)
void loop() {
    // // Get MPU-6050 Data
    // // Get raw sensor data (accel + gyro)
    // int16_t ax, ay, az, gx, gy, gz;
    // mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    // // Get scaled values
    // float axt = ax / 16384.0;
    // float ayt = ay / 16384.0;
    // float azt = az / 16384.0;
    // float gxt = gx / 131.0;
    // float gyt = gy / 131.0;
    // float gzt = gz / 131.0;
    
    // // Get HC-SR04 Data Left
    // long duration_left, distance_left;
    // digitalWrite(TRIG_PIN_LEFT, LOW);
    // delayMicroseconds(2);
    // digitalWrite(TRIG_PIN_LEFT, HIGH);
    // delayMicroseconds(10);
    // digitalWrite(TRIG_PIN_LEFT, LOW);
    // // Get the values and calculate distance
    // duration_left = pulseIn(ECHO_PIN_LEFT, HIGH);
    // if (LIVE_DEBUG) {
    //   Serial.print("This is the duration from left ultrasonics: ");
    //   Serial.println(duration_left);
    // }
    // distance_left = duration_left * 0.034 / 2;  // Convert to cm
    // //delay(50);  // Short pause before next sensor

    // // Get HC-SR04 Data Right
    // long duration_right, distance_right;
    // digitalWrite(TRIG_PIN_RIGHT, LOW);
    // delayMicroseconds(2);
    // digitalWrite(TRIG_PIN_RIGHT, HIGH);
    // delayMicroseconds(10);
    // digitalWrite(TRIG_PIN_RIGHT, LOW);
    // // Get the values and calculate distance
    // duration_right = pulseIn(ECHO_PIN_RIGHT, HIGH);
    // if (LIVE_DEBUG) {
    //   Serial.print("This is the duration from right ultrasonics: ");
    //   Serial.println(duration_right);
    // }
    // distance_right = duration_right * 0.034 / 2;  // Convert to cm

    // // Open CSV file and append data
    // dataFile = SD.open(DATA_FILENAME, FILE_WRITE);
    // if (dataFile && count <= LOOP_COUNT) { // temporary capture of only 500 rows
    //   dataFile.print(millis()); dataFile.print(",");
    //   dataFile.print(axt, 3); dataFile.print(",");
    //   dataFile.print(ayt, 3); dataFile.print(",");
    //   dataFile.print(azt, 3); dataFile.print(",");
    //   dataFile.print(gxt, 3); dataFile.print(",");
    //   dataFile.print(gyt, 3); dataFile.print(",");
    //   dataFile.print(gzt, 3); dataFile.print(",");
    //   dataFile.print(distance_left, 1); dataFile.print(",");
    //   dataFile.print(distance_right, 1); dataFile.println();
    //   dataFile.close();
    //   if (count >= LOOP_COUNT) Serial.println("Wrote 500 rows into CSV: ");
    //   count++;
    //   if (count % 100 == 0) Serial.println("Wrote 100 rows into CSV. Continuing... ");
    // }
    // // Output Debug
    // if (LIVE_DEBUG) {
    //   Serial.println("Timestamp(ms), AccelX(g), AccelY(g), AccelZ(g), GyroX(deg/s), GyroY(deg/s), GyroZ(deg/s), DistanceLeft(cm), DistanceRight(cm)");
    //   Serial.print(millis()); Serial.print(", "); Serial.print(axt, 3); Serial.print(", "); Serial.print(ayt, 3); Serial.print(", "); Serial.print(azt, 3); Serial.print(", ");
    //   Serial.print(gxt, 3); Serial.print(", "); Serial.print(gyt, 3); Serial.print(", "); Serial.print(gzt, 3); Serial.print(", "); Serial.print(distance_left, 3); 
    //   Serial.print(", "); Serial.println(distance_right, 3);
    // }
    //     // 5 millisecond delay
    // delay(LOOP_DELAY);
  // Get current milliseconds
  unsigned long currentTime = millis();

  //--- Step 1: Read MPU-6050 (Non-Blocking) ---
  if (currentTime - lastMPUTime >= MPU_INTERVAL) {
    readMPU6050();  // Update accel/gyro variables
    lastMPUTime = currentTime;
    // Write to SD-Card in this interval (should be the shortest)
    writeToSDCard(leftDist, rightDist, accelX, accelY, accelZ, gyroX, gyroY, gyroZ);
  }

  //--- Step 2: Trigger HC-SR04 Sensors ---
  if (leftState == IDLE && rightState == IDLE && currentTime - lastPingTime >= PING_INTERVAL) {
    triggerUltrasonic(TRIG_PIN_LEFT, &leftState);
    triggerUltrasonic(TRIG_PIN_RIGHT, &rightState);
    leftState = rightState = TRIGGERED;
  }

  //--- Step 3: Wait for ECHO Pulses ---
  checkEcho(ECHO_PIN_LEFT, &leftState, &leftEchoStart, &leftDist);
  checkEcho(ECHO_PIN_RIGHT, &rightState, &rightEchoStart, &rightDist);
}