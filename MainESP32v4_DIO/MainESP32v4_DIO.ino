/////////////////////////////////////////////////////////////////
//     ESP32 Thing Plus wifi+deepSleep A0 data Transmition     //
//      AG                                                     //
/////////////////////////////////////////////////////////////////
// Each iteration save the value on AO in the struct rtcData, then deep sleep 60s
// Send to wifi if rtcData is full (60 values, each hour)
// Reset switch restet also the value in rtcData
// Send incomplete data to wifi if onBoard switch 0 is pressed (add one iteration and one value to rtcData)
// Timers set a maximum time to wait wifi (5min)
// Timer track every iteration loop time to spend this time less in deep sleep.
// Warning: change device name 40  <=============

#include <WiFi.h>
#include "driver/adc.h"
#include <esp_wifi.h>
#include <esp_bt.h>
#include "driver/rtc_io.h"

#define uS_TO_S_FACTOR 1000000  /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP  60        // Time ESP32 will go to sleep (in seconds), 60s by default 

// WiFi network name and password:
const char * ssid = "OpenTeraHub";
const char * password = "CdRV1036!!";
const char* host = "192.168.4.1";  // Server address
const uint16_t port = 3000;  // Server port

// Main data structure to be recorded to  RTC mem and transmitted  
const int lengthData = 60*8; // 4h for data and 4h in backup
RTC_DATA_ATTR struct {
  uint16_t nbpts;
  uint16_t data[lengthData];
} rtcData;
float sensorValue = 0;

//Wifi Related
int timeWifi;
int waitWifi;
const int time2WaitWifi = 20e6; // only 20sec
bool wifiTranfered = false;
const char * device = "ESP32_030"; // <================================== HERE!

// Other
int LED_PIN = 13; // Onboard DEL
int powerDO_PIN = 25; // Onboard to power the FSR when ON (A1)
int slp_pin = 0; //Onboard slp swith
int slp_val = 0;
const int analogInPin = A0;  // ESP32 Analog Pin ADC0 = A0
int i;
int t_depart = millis();
int t_total;
bool wkupSW = false;

//Setup
void setup() {
  //Start timer
  t_depart = millis();

  //Initilize hardware:
  Serial.begin(115200); // Serial port to display status and help debug
  Serial.println();
  pinMode(powerDO_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(slp_pin, INPUT);
}

//Main loop
void loop() {
  // Record one point
  rtc_gpio_hold_dis(GPIO_NUM_25); //Enable the DO vcc
  rtc_gpio_hold_dis(GPIO_NUM_13); //Enable the LED DO
  rtc_gpio_hold_dis(GPIO_NUM_0); //Enable the SLP DI
  digitalWrite(LED_PIN, HIGH); // Set the LED to High
  digitalWrite(powerDO_PIN, HIGH); // Set the DO vcc to High
  adc_power_on(); // added because we turn it off after
  sensorValue = analogRead(analogInPin); // Read analog input 
  adc_power_off();  // turn it off right after reading it
  digitalWrite(powerDO_PIN, LOW); // Set the DO vcc to Low
  digitalWrite(LED_PIN, LOW); // Set the LED to Low
  slp_val = digitalRead(slp_pin); //Read the value on the reset switch
  rtc_gpio_isolate(GPIO_NUM_25); //Disable the DO vcc
  rtc_gpio_isolate(GPIO_NUM_13); //Disable the LED DO
  rtc_gpio_isolate(GPIO_NUM_0); //Disable the SLP DI
  rtcData.data[rtcData.nbpts] = sensorValue; // store the data point to next available space in rtcData

  Serial.print("Nb pts recorded: ");
  Serial.println(rtcData.nbpts + 1);
  Serial.print("last rtcData: "); // much faster, less wakeup time.
  Serial.print(rtcData.data[rtcData.nbpts]);
  Serial.println();
  rtcData.nbpts++;

  //if rtcData is full, open wifi, transmit and restart (wipe rtcData)
  if (rtcData.nbpts >= lengthData/2) {  //lengthData/2 the other half is for backup if transfert failed
     //fill empty values with 9999:
    for (i = 0 ; i < lengthData - rtcData.nbpts; i++) {
      rtcData.data[i+rtcData.nbpts] = 9999;
    }   
    if(rtcData.nbpts%5 == 0 || rtcData.nbpts == lengthData/2 || rtcData.nbpts >= lengthData){ 
      // Connect to the WiFi network (see function below loop)
      uint16_t data2send[rtcData.nbpts];
      for (i = 0 ; i < rtcData.nbpts; i++) {
        data2send[i] = rtcData.data[i];
      }       
      ConnectWIFI((uint8_t*) &data2send, rtcData.nbpts*sizeof(uint16_t));   //ConnectWIFI((uint8_t*) &rtcData.data, lengthData*sizeof(uint16_t));
      if (wifiTranfered){
        // Reset Structure
        rtcData.nbpts = 0;
        memset(rtcData.data, 0, sizeof(rtcData.data));
      } 
    }
    if (rtcData.nbpts >= lengthData){
      // Shift the structure, one point is lost 
      for (int i = 0; i <= lengthData-1; i++){
        rtcData.data[i] = rtcData.data[i+1];
      }
      rtcData.nbpts = rtcData.nbpts-1;
    }
  }

  //check if slp_switch pressed
  if (slp_val == 1) {
    //Check time wasted in the loop to substract it (We want one point each 60s as much as pos
    t_total = millis() - t_depart;
    Serial.print("Sleep for: ");
    Serial.println((TIME_TO_SLEEP * 1e3 - t_total) / 1e3);
    Serial.println();
    esp_sleep_enable_timer_wakeup((TIME_TO_SLEEP * 1e3 - t_total) * uS_TO_S_FACTOR / 1e3);
  }
  else {
    Serial.println("Slp_switch pressed, infinite sleep");
    Serial.println();
  }
  //Start the deep sleep
  esp_wifi_stop();
  esp_bt_controller_disable();
  esp_deep_sleep_start();
  
}

//WIFI function
void ConnectWIFI(const uint8_t *data, size_t length) {   
  esp_wifi_start(); // added because it's disable at the end of iteration
  // Connect to WiFi network
  WiFi.begin(ssid, password);

  Serial.println();
  Serial.println("Wait for WiFi... ");
  timeWifi = millis();
  while (WiFi.status() != WL_CONNECTED && waitWifi * 1e3 < time2WaitWifi) {
    waitWifi = millis() - timeWifi;
    Serial.print(waitWifi / 1e3);
    Serial.println("s");
    Serial.write(13);
    digitalWrite(LED_PIN, LOW);
    delay(480);
    digitalWrite(LED_PIN, HIGH);
    delay(20);
    digitalWrite(LED_PIN, LOW);
  }
  if (WiFi.status() == WL_CONNECTED){
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());

    Serial.print("Connecting to ");
    Serial.print(host);
    Serial.print(':');
    Serial.println(port);

    // Use WiFiClient class to create TCP connections
    WiFiClient client;
    client.setNoDelay(true);
    if (!client.connect(host, port)) {
      Serial.println("Connection failed. Data not send");
      delay(1000);
      wifiTranfered = false;
    }
    else{
      Serial.println("Connected! Sending data...");
  
      // Send greetings, used as folder id in the Pie
      client.print(device);
      delay(500);
      // Send data structure
      client.write(data, length);
      delay(min(max(2000,waitWifi/2), 10000)); // adapt the wait with the connection quality
      client.flush();
      // Close connection
      Serial.println("Closing connection");
      Serial.println();
      client.stop();
      wifiTranfered = true;
    }
  }
  else {
    // Wifi is not found
    Serial.println("Wifi not found, delay expired, data lost");
    Serial.println();
    wifiTranfered = false;
  }
}
