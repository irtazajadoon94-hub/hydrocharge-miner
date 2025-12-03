/*
 * HydroCharge Miner - Arduino IoT Firmware
 * Real-time sensor monitoring and cloud connectivity
 * 
 * Hardware: Arduino Nano 33 IoT
 * Sensors: Flow (YF-S201), Pressure (MS5837), RPM (Hall Effect), Power (INA219)
 */

#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_INA219.h>

// WiFi credentials (set via Serial or config file)
char ssid[] = "YOUR_WIFI_SSID";
char pass[] = "YOUR_WIFI_PASSWORD";

// Cloud API endpoint
const char* serverUrl = "api.hydrocharge.io";
const int serverPort = 443;

// Sensor pins
const int FLOW_SENSOR_PIN = 2;
const int RPM_SENSOR_PIN = 3;
const int PIEZO_VOLTAGE_PIN = A0;

// Sensor objects
Adafruit_INA219 ina219;

// Flow sensor variables
volatile int flowPulseCount = 0;
float flowRate = 0.0;  // L/min
float totalVolume = 0.0;  // Liters

// RPM sensor variables
volatile int rpmPulseCount = 0;
int turbineRPM = 0;

// Power monitoring
float busVoltage = 0.0;
float current_mA = 0.0;
float power_mW = 0.0;

// Timing
unsigned long lastSampleTime = 0;
const unsigned long SAMPLE_INTERVAL = 1000;  // 1 second

// Bernoulli calculation constants
const float WATER_DENSITY = 1000.0;  // kg/m³
const float GRAVITY = 9.81;  // m/s²
const float PIPE_DIAMETER = 0.05;  // 50mm = 0.05m
const float HEAD_HEIGHT = 3.0;  // 3 meters vertical drop

// ============================================
// INTERRUPT SERVICE ROUTINES
// ============================================

void flowPulseCounter() {
  flowPulseCount++;
}

void rpmPulseCounter() {
  rpmPulseCount++;
}

// ============================================
// SETUP
// ============================================

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  Serial.println("🌊 HydroCharge Miner - Initializing...");
  
  // Initialize sensors
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP);
  pinMode(RPM_SENSOR_PIN, INPUT_PULLUP);
  pinMode(PIEZO_VOLTAGE_PIN, INPUT);
  
  // Attach interrupts
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowPulseCounter, FALLING);
  attachInterrupt(digitalPinToInterrupt(RPM_SENSOR_PIN), rpmPulseCounter, FALLING);
  
  // Initialize INA219 power monitor
  if (!ina219.begin()) {
    Serial.println("❌ Failed to find INA219 chip");
    while (1) delay(10);
  }
  Serial.println("✅ INA219 Power Monitor initialized");
  
  // Connect to WiFi
  connectWiFi();
  
  Serial.println("✅ HydroCharge Miner ready!");
  lastSampleTime = millis();
}

// ============================================
// MAIN LOOP
// ============================================

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL) {
    // Calculate flow rate (YF-S201: 7.5 pulses per liter)
    flowRate = (flowPulseCount / 7.5) * 60.0;  // L/min
    totalVolume += flowPulseCount / 7.5;
    flowPulseCount = 0;
    
    // Calculate turbine RPM (assuming 1 pulse per revolution)
    turbineRPM = rpmPulseCount * 60;  // RPM
    rpmPulseCount = 0;
    
    // Read piezo voltage (0-5V mapped to 0-1023)
    int piezoRaw = analogRead(PIEZO_VOLTAGE_PIN);
    float piezoVoltage = (piezoRaw / 1023.0) * 5.0;
    
    // Read power monitor
    busVoltage = ina219.getBusVoltage_V();
    current_mA = ina219.getCurrent_mA();
    power_mW = ina219.getPower_mW();
    
    // Calculate hydraulic power (Bernoulli)
    float flowRateLPS = flowRate / 60.0;  // Convert to L/s
    float hydraulicPower = WATER_DENSITY * GRAVITY * (flowRateLPS / 1000.0) * HEAD_HEIGHT;  // Watts
    
    // Calculate efficiency
    float totalPowerW = power_mW / 1000.0;
    float efficiency = (hydraulicPower > 0) ? (totalPowerW / hydraulicPower) * 100.0 : 0.0;
    
    // Print to Serial
    printSensorData(flowRate, turbineRPM, piezoVoltage, totalPowerW, hydraulicPower, efficiency);
    
    // Send to cloud
    sendDataToCloud(flowRate, turbineRPM, piezoVoltage, totalPowerW, hydraulicPower, efficiency);
    
    // Check for alerts
    checkAlerts(flowRate, turbineRPM, efficiency);
    
    lastSampleTime = currentTime;
  }
  
  delay(10);
}

// ============================================
// FUNCTIONS
// ============================================

void connectWiFi() {
  Serial.print("🔌 Connecting to WiFi: ");
  Serial.println(ssid);
  
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.print(".");
  }
  
  Serial.println("\n✅ WiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void printSensorData(float flow, int rpm, float piezo, float power, float hydro, float eff) {
  Serial.println("\n========== HYDROCHARGE READINGS ==========");
  Serial.print("💧 Flow Rate: "); Serial.print(flow); Serial.println(" L/min");
  Serial.print("⚙️  Turbine RPM: "); Serial.println(rpm);
  Serial.print("⚡ Piezo Voltage: "); Serial.print(piezo); Serial.println(" V");
  Serial.print("🔋 Total Power: "); Serial.print(power); Serial.println(" W");
  Serial.print("🌊 Hydraulic Power: "); Serial.print(hydro); Serial.println(" W");
  Serial.print("📊 Efficiency: "); Serial.print(eff); Serial.println(" %");
  Serial.println("==========================================\n");
}

void sendDataToCloud(float flow, int rpm, float piezo, float power, float hydro, float eff) {
  WiFiSSLClient client;
  
  if (client.connect(serverUrl, serverPort)) {
    // Create JSON payload
    StaticJsonDocument<256> doc;
    doc["device_id"] = WiFi.macAddress();
    doc["timestamp"] = millis();
    doc["flow_rate"] = flow;
    doc["turbine_rpm"] = rpm;
    doc["piezo_voltage"] = piezo;
    doc["power_output"] = power;
    doc["hydraulic_power"] = hydro;
    doc["efficiency"] = eff;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Send HTTP POST
    client.println("POST /api/v1/data HTTP/1.1");
    client.print("Host: "); client.println(serverUrl);
    client.println("Content-Type: application/json");
    client.print("Content-Length: "); client.println(jsonString.length());
    client.println();
    client.println(jsonString);
    
    Serial.println("☁️  Data sent to cloud");
    client.stop();
  } else {
    Serial.println("❌ Cloud connection failed");
  }
}

void checkAlerts(float flow, int rpm, float eff) {
  // Alert: Low flow rate
  if (flow < 10.0) {  // Below 10 L/min
    Serial.println("🚨 ALERT: Flow rate low - check intake!");
    sendAlert("LOW_FLOW", flow);
  }
  
  // Alert: Turbine stopped
  if (rpm < 100) {
    Serial.println("🚨 ALERT: Turbine RPM critical - piezo backup?");
    sendAlert("LOW_RPM", rpm);
  }
  
  // Alert: Low efficiency
  if (eff < 60.0 && eff > 0) {
    Serial.println("🚨 ALERT: Efficiency below 60% - maintenance needed");
    sendAlert("LOW_EFFICIENCY", eff);
  }
  
  // Alert: High efficiency (celebrate!)
  if (eff > 85.0) {
    Serial.println("💎 OPTIMAL: Efficiency above 85% - perfect flow!");
  }
}

void sendAlert(String alertType, float value) {
  WiFiSSLClient client;
  
  if (client.connect(serverUrl, serverPort)) {
    StaticJsonDocument<128> doc;
    doc["device_id"] = WiFi.macAddress();
    doc["alert_type"] = alertType;
    doc["value"] = value;
    doc["timestamp"] = millis();
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    client.println("POST /api/v1/alerts HTTP/1.1");
    client.print("Host: "); client.println(serverUrl);
    client.println("Content-Type: application/json");
    client.print("Content-Length: "); client.println(jsonString.length());
    client.println();
    client.println(jsonString);
    
    client.stop();
  }
}
