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
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Fonts/TomThumb.h>
#include <NewPing.h>

// Pins for board to sensor connection
#define TRIG_PIN_LEFT 5
#define ECHO_PIN_LEFT 2
#define TRIG_PIN_RIGHT 6
#define ECHO_PIN_RIGHT 3
#define SD_CS_PIN 10
// Constants for the program logic
#define DATA_FILENAME "data.csv"
#define PING_INTERVAL 50 // ms
#define SENSOR_INTERVAL 10 // ms
#define MAX_DISTANCE 200  // Adjust based on your needs
#define SCREEN_WIDTH 128  // OLED width (pixels)
#define SCREEN_HEIGHT 32  // OLED height (pixels)
#define SCREEN_ADDRESS 0x3C // OLED I2C Address (Hex)
// Constants for the loop logic
#define LIVE_DEBUG 0
#define INTERVAL_MAX 600 // span for collection

// Ultrasonics
NewPing sonarLeft(TRIG_PIN_LEFT, ECHO_PIN_LEFT, MAX_DISTANCE);
NewPing sonarRight(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT, MAX_DISTANCE);
// unsigned int leftDist_cm;
// unsigned int rightDist_cm;

// Initialize OLED (I2C address 0x3C for most displays)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Initialize objects
MPU6050 mpu; // MPU object
// File dataFile; // File object

// MPU-6050
unsigned long lastMPUTime = 0;
float accelX, accelY, accelZ, gyroX, gyroY, gyroZ;

// Looping
int count; // counter
int interval; // data interval

// Initialize the MPU-6050 sensors
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

// Verify the SD Hardware
bool verifySDHardware() {
    // Initialize test result
    bool test = true;
    // Initialize SD card with detailed error reporting
    Serial.println("Initializing SD card...");
    printOLED(&count, "Initializing SD card...");
    // SPI.beginTransaction(SPISettings(4e6, MSBFIRST, SPI_MODE0));
    // Test SD-Card
    if (!SD.begin(SD_CS_PIN)) {
      Serial.println("\nSD initialization failed!");
      printOLED(&count, "SD initialization failed!");
      Serial.println("Possible causes:");
      // New error checking method
      if (!SD.exists("/")) {
        Serial.println("- No card detected");
        printOLED(&count, "No card detected");
        test = false;
      } else {
        //SPI.beginTransaction(SPISettings(SPI_CLOCK_DIV8, MSBFIRST, SPI_MODE0));
        File testFile = SD.open("test.txt", FILE_WRITE);
        if (!testFile) {
          Serial.println("- Cannot create files (might be write-protected)");
          test = false;
        } else {
          SD.remove("test.txt");
          Serial.println("- Unknown error (card detected but initialization failed)");
          test = false;
        }
        testFile.close();
        // SD.end();
      }
    }
    // Return the boolean test of the SD Hardware
    return test;
}

// This will initialize the Data File for collections
void initDataFile() {
    // Ensure clean-up of data.csv
    if (SD.exists(DATA_FILENAME)) { 
      SD.remove(DATA_FILENAME);
    }
    if (SD.begin(SD_CS_PIN)) {
      // Create new CSV file
      File dataFile = SD.open(DATA_FILENAME, FILE_WRITE);
      
      if (dataFile) {
        dataFile.println("Timestamp(ms),AccelX(g),AccelY(g),AccelZ(g),GyroX(deg/s),GyroY(deg/s),GyroZ(deg/s),DistanceLeft(cm),DistanceRight(cm)");
        dataFile.close();
        Serial.println("CSV header written");
        printOLED(&count, "CSV header written");
        
      } else {
        Serial.print("Data File details: ");
        Serial.println(dataFile);
        Serial.println("Error opening " DATA_FILENAME);
        exit(0);
      }
      dataFile.close();
    }
    // SD.end();
}

// Countdown before data collection for 128x32 OLED
void countdownOLED(int seconds) {
  for (int i = seconds; i > 0; i--) {
    display.clearDisplay();
    display.setTextSize(1); // Smaller size to fit in limited height
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(28, 4); // Centered horizontally (approx)
    display.print("Starting in");

    display.setTextSize(2); // Larger for the countdown number
    display.setCursor(56, 16); // Centered number
    display.print(i);
    
    display.display();
    delay(1000);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(38, 12); // Roughly center "Starting!"
  display.println("Starting!");
  display.display();
  delay(1000); // brief pause after countdown
}


// This is the function that will write the sensor data to the SD card
void writeToSDCard(float leftDist, float rightDist, float ax, float ay, float az, float gx, float gy, float gz) {
// void writeToSDCard() {
  // Get the current timestamp
  unsigned long currentTS = millis();
  // Open the Data File
  File dataFile = SD.open(DATA_FILENAME, FILE_WRITE);
  // Write a new row to the file
  if (dataFile && interval <= INTERVAL_MAX) { // temporarily capture only 500 rows
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
      if (LIVE_DEBUG && interval >= INTERVAL_MAX) Serial.println("Wrote 3000 rows into CSV: ");
      if (LIVE_DEBUG && (interval % 1000 == 0)) Serial.println("Wrote 1000 rows into CSV. Continuing... ");
  }
  // Close file and end SD session
  dataFile.close();
  // SD.end();
}

// Initialize the OLED screen for Data Collection
void initOLED_SD() {
  display.clearDisplay();
  //display.setFont(&TomThumb);
  display.setFont();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  //display.setCursor(0, 5);
  display.setCursor(0, 0);
  display.println("Collecting Data...");
  display.display();
}

// Initialize the OLED screen for MPU Real-time collection
void updateOLED_MPU(unsigned int leftDist, unsigned int rightDist) {
  display.clearDisplay();
  display.setFont(&TomThumb);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 5);
  display.println("MPU Data...");
  display.print("AX:");
  display.print(accelX, 1);  // 1 decimal
  display.print(" AY:");
  display.print(accelX, 1);
  display.print(" AZ:");
  display.println(accelZ, 1);

  display.setCursor(0, 12);
  display.print("GX:");
  display.print(gyroX, 1);  // 1 decimal
  display.print(" GY:");
  display.print(gyroY, 1);
  display.print(" GZ:");
  display.println(gyroZ, 1);

  display.setCursor(0, 19);
  display.print("L:");
  display.print(leftDist, 1);  // 1 decimal
  display.print(" R:");
  display.println(rightDist, 1);
  display.display();
}

// Update the OLED with the Data interval processed
void updateOLED_SD() {
  // --- DRAW TO OLED ---
  //display.clearDisplay();
  initOLED_SD();
  // display.setFont(&TomThumb);
  display.setFont();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  // display.setCursor(0, 12);
  display.setCursor(0, 10);
  display.print("Data Interval: ");
  display.println(interval);
  display.display();
}

// Finish the SD collection message
void finishOLED_SD() {
  //display.clearDisplay();
  //display.setFont(&TomThumb);
  display.setFont();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 20);
  display.print("Collection Complete");
  display.display();
}

// Generic printOLED for tiny text
void printOLED(int *line, char *text) {
  // Handle overflow to clear screen and restart
  if (*line + 6 > 32) {
    display.clearDisplay();
    *line = 5;
    delay(500);
  }
  display.setFont(&TomThumb);
  display.setCursor(0, *line);
  //display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.println(text);
  display.display();
  *line += 7;
}

// Setup Function (one startup)
void setup() {
    // Start the serial console session
    Serial.begin(115200); // Ensure maximum speed of serial communications at 115.2K (UART max)
    // Initialize I2C sensors
    Wire.begin();
    // Initialize OLED
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
      Serial.println("SSD1306 allocation failed");
      exit(0);
    }
    // Show the message that the system is booting
    else {
      display.clearDisplay();
      display.setFont(&TomThumb);
      display.setCursor(0,5);
      //display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);
      display.println("System Booting!");
      display.display();
      count = 5 + 7;
    }
    delay(5); // Small delay
    // Initalize MPU-6050 sensor
    initMPU6050();
    delay(5); // Small delay
    // Initlaize the SD-Card Hardware
    bool sdReady = verifySDHardware();
    if (sdReady) {
      Serial.println("initialization done.");
      printOLED(&count, "Initialization complete");
    }
    else exit(0);
    // Initialize interval
    interval = 1;
    // Finish initialization of hardware
    initDataFile();
    // System initialization complete
    printOLED(&count, "System Initialized!");
    delay(10000);
    countdownOLED(3);
    // Update OLED for collection
    initOLED_SD();
    delay(5); // Small delay
}

// Runs continually (final delay creates interval)
void loop() {
  // Only process for the length of the interval max
  if (interval <= INTERVAL_MAX) {
    // Step 1: Read MPU sensor
    readMPU6050();  // Update accel/gyro variables
    // Step 2: Get distances (blocking mode)
    unsigned int leftDist_cm = sonarLeft.ping_cm();
    unsigned int rightDist_cm = sonarRight.ping_cm();
    // Step 3: Write to SD-Card
    writeToSDCard(leftDist_cm, rightDist_cm, accelX, accelY, accelZ, gyroX, gyroY, gyroZ);
    // writeToSDCard();
    // Step 4: Update OLED screen with interval
    if (interval % 50 == 0) updateOLED_SD();
    // Update OLED that collection is finished
    if (interval == INTERVAL_MAX) finishOLED_SD();
  }
  else {
    SD.end();
    exit(0);
  }
  // Update counter
  interval++;
  // Delay of sensors
  delay(SENSOR_INTERVAL);
}