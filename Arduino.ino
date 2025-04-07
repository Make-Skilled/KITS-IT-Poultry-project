#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <ThingSpeak.h>

#define WIFI_SSID "Act"         
#define WIFI_PASSWORD "Madhumakeskilled"

// API Endpoints
#define SERVER_URL_EARLY "http://192.168.0.198:5000/api/sensor-data/early"
#define SERVER_URL_MID "http://192.168.0.198:5000/api/sensor-data/mid"
#define SERVER_URL_LATE "http://192.168.0.198:5000/api/sensor-data/late"
#define THINGSPEAK_API_KEY1 "0YLE00JTFZ2IAZZF"
#define CHANNEL_ID1 2839545

#define write_api_key2 "SJPIKXSQ27L3H5K2"
#define CHANNEL_ID2 2839570

// DHT11 Sensor Pins
#define DHTPIN1 5
#define DHTPIN2 18
#define DHTPIN3 19
#define DHTTYPE DHT11

// Gas Sensor Pins (Analog)
#define GAS_SENSOR_PIN1 34
#define GAS_SENSOR_PIN2 35
#define GAS_SENSOR_PIN3 32

// Relay Pins
#define FAN1_PIN 15
#define FAN2_PIN 2
#define FAN3_PIN 4

// Thresholds
const float TEMP_THRESHOLD = 30.0;

// Initialize DHT Sensors
DHT dht1(DHTPIN1, DHTTYPE);
DHT dht2(DHTPIN2, DHTTYPE);
DHT dht3(DHTPIN3, DHTTYPE);

// WiFi & ThingSpeak
WiFiClient client;

void setup() {
    Serial.begin(115200);
    
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi!");

    ThingSpeak.begin(client); // Initialize ThingSpeak

    // Start DHT Sensors
    dht1.begin();
    dht2.begin();
    dht3.begin();

    // Set relay pins as OUTPUT
    pinMode(FAN1_PIN, OUTPUT);
    pinMode(FAN2_PIN, OUTPUT);
    pinMode(FAN3_PIN, OUTPUT);

    // Ensure relays are OFF initially
    digitalWrite(FAN1_PIN, HIGH);
    digitalWrite(FAN2_PIN, HIGH);
    digitalWrite(FAN3_PIN, HIGH);
}

void sendSectionData(const char* baseUrl, float temp, float humidity, int gas) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        
        // Construct URL with query parameters
        String url = String(baseUrl) + 
                    "?temperature=" + String(temp) + 
                    "&humidity=" + String(humidity) + 
                    "&gas=" + String(gas);
        
        http.begin(client, url);
        
        Serial.print("Sending Data to API: ");
        Serial.println(url);

        int httpResponseCode = http.GET();
        if (httpResponseCode > 0) {
            Serial.print("API Response: ");
            Serial.println(http.getString());
        } else {
            Serial.print("Error Sending to API: ");
            Serial.println(httpResponseCode);
        }
        http.end();
    }
}

void loop() {
    // Read sensor values
    float temp1 = dht1.readTemperature();
    float hum1 = dht1.readHumidity();
    float temp2 = dht2.readTemperature();
    float hum2 = dht2.readHumidity();
    float temp3 = dht3.readTemperature();
    float hum3 = dht3.readHumidity();

    int gasValue1 = analogRead(GAS_SENSOR_PIN1);
    int gasValue2 = analogRead(GAS_SENSOR_PIN2);
    int gasValue3 = analogRead(GAS_SENSOR_PIN3);

    // Validate Sensor Readings
    if (isnan(temp1) || isnan(hum1) || isnan(temp2) || isnan(hum2) || isnan(temp3) || isnan(hum3)) {
        Serial.println("Failed to read from DHT sensor!");
        return;
    }

    // Print sensor readings
    Serial.println("\n=== Sensor Readings ===");
    Serial.print("temp1: "); Serial.println(temp1);
    Serial.print("temp2: "); Serial.println(temp2);
    Serial.print("temp3: "); Serial.println(temp3);
    Serial.print("hum1: "); Serial.println(hum1);
    Serial.print("hum2: "); Serial.println(hum2);
    Serial.print("hum3: "); Serial.println(hum3);
    Serial.print("gas1: "); Serial.println(gasValue1);
    Serial.print("gas2: "); Serial.println(gasValue2);
    Serial.print("gas3: "); Serial.println(gasValue3);

    // Send data to local server
    sendSectionData(SERVER_URL_EARLY, temp1, hum1, gasValue1);
    delay(1000);
    sendSectionData(SERVER_URL_MID, temp2, hum2, gasValue2);
    delay(1000);
    sendSectionData(SERVER_URL_LATE, temp3, hum3, gasValue3);
    delay(1000);

    // Update ThingSpeak Channel 1 (Early and Mid stage data)
    Serial.println("\nUpdating ThingSpeak Channel 1...");
    ThingSpeak.setField(1, temp1);
    ThingSpeak.setField(2, hum1);
    ThingSpeak.setField(3, gasValue1);
    ThingSpeak.setField(4, temp2);
    ThingSpeak.setField(5, hum2);
    ThingSpeak.setField(6, gasValue2);
    
    int x = ThingSpeak.writeFields(CHANNEL_ID1, THINGSPEAK_API_KEY1);
    if(x == 200){
        Serial.println("Channel 1 update successful");
    }
    else{
        Serial.println("Channel 1 update failed. HTTP error code " + String(x));
    }
    
    delay(15000); // Required delay between ThingSpeak updates

    // Update ThingSpeak Channel 2 (Late stage data)
    Serial.println("\nUpdating ThingSpeak Channel 2...");
    ThingSpeak.setField(1, temp3);
    ThingSpeak.setField(2, hum3);
    ThingSpeak.setField(3, gasValue3);
    
    // Read fan status before updating
    int fan1 = ThingSpeak.readIntField(CHANNEL_ID2, 4);
    int fan2 = ThingSpeak.readIntField(CHANNEL_ID2, 5);
    int fan3 = ThingSpeak.readIntField(CHANNEL_ID2, 6);
    
    // Set fan status fields
    ThingSpeak.setField(4, fan1);
    ThingSpeak.setField(5, fan2);
    ThingSpeak.setField(6, fan3);
    
    x = ThingSpeak.writeFields(CHANNEL_ID2, write_api_key2);
    if(x == 200){
        Serial.println("Channel 2 update successful");
    }
    else{
        Serial.println("Channel 2 update failed. HTTP error code " + String(x));
    }

    // Update fan states
    digitalWrite(FAN1_PIN, fan1 == 1 ? LOW : HIGH);
    digitalWrite(FAN2_PIN, fan2 == 1 ? LOW : HIGH);
    digitalWrite(FAN3_PIN, fan3 == 1 ? LOW : HIGH);

    delay(15000);  // Wait before next update cycle
}
