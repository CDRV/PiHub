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
const int time2WaitWifi = 30e6; // only 30sec
bool wifiTranfered = false;
const char * device = "ESP32_00A"; // <================================== HERE!

// Other
int LED_PIN = 13; // Onboard DEL
int powerDO_PIN = 25; // Onboard to power the FSR when ON (A1)
const int analogInPin = A0;  // ESP32 Analog Pin ADC0 = A0
int i;
int t_depart = millis();
int t_total;
bool wkupSW = false;

//Setup
void setup() {
  // reduce CPU speed for battery consumption
  setCpuFrequencyMhz(80);
  //Start timer
  t_depart = millis();

  // Initilize hardware:
  Serial.begin(115200); // Serial port to display status and help debug
  Serial.println();
  pinMode(LED_PIN, OUTPUT);
  pinMode(powerDO_PIN, OUTPUT);
  delay(500);

  //Allow wakup by switch on board (GPIO 0)
  esp_sleep_wakeup_cause_t wakeup_reason;
  wakeup_reason = esp_sleep_get_wakeup_cause();
  switch (wakeup_reason)
  {
    case ESP_SLEEP_WAKEUP_EXT0 : Serial.println("Wakeup caused by switch 0"); wkupSW = true; break;
    case ESP_SLEEP_WAKEUP_TIMER : Serial.println("Wakeup caused by timer"); break;
    default : Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason); break;
  }
}

//Main loop
void loop() {
  // Light ON
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(powerDO_PIN, HIGH);
  // Read analog input and store it to next available space in rtcData
  adc_power_on(); // added because we turn it off after
  sensorValue = analogRead(analogInPin);
  adc_power_off();  // turn it off right after reading it
  digitalWrite(powerDO_PIN, LOW);
  rtc_gpio_isolate(GPIO_NUM_25);
  rtcData.data[rtcData.nbpts] = sensorValue;

  Serial.print("Nb pts recorded: ");
  Serial.println(rtcData.nbpts + 1);
  Serial.print("rtcData: ");
  for (i = 0 ; i < lengthData ; i++) {
    Serial.print(rtcData.data[i]);
    Serial.print("  ");
  }
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
  else if (wkupSW == true) {
    if (rtcData.nbpts >= lengthData){
      // Reset Structure
      rtcData.nbpts = 0;
      memset(rtcData.data, 0, sizeof(rtcData.data));
    } 
    //fill empty values with 9999:
    for (i = 0 ; i < lengthData - rtcData.nbpts; i++) {
      rtcData.data[i+rtcData.nbpts] = 9999;
    }
    // Connect to the WiFi network and transmit (see function below loop)
    uint16_t data2send[rtcData.nbpts];
    for (i = 0 ; i < rtcData.nbpts; i++) {
      data2send[i] = rtcData.data[i];
    }       
    ConnectWIFI((uint8_t*) &data2send, rtcData.nbpts*sizeof(uint16_t));   //ConnectWIFI((uint8_t*) &rtcData.data, lengthData*sizeof(uint16_t));
    if (wifiTranfered){
      Serial.println("Incomplete data sended");
    }
    else {
      Serial.println("Data not sended, check wifi");
    }
    Serial.println("Going to infinite sleep mode");
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0); //1 = High, 0 = Low
    esp_deep_sleep_start();
  }

  // Set the LED to Low
  digitalWrite(LED_PIN, LOW);
  //Check time wasted in the loop to substract it(We want one point each 60s as much as pos
  t_total = millis() - t_depart;
  Serial.print("Iteration wasted time: ");
  Serial.println(t_total / 1e3);
  if (t_total > TIME_TO_SLEEP * 1e3) {
    t_total = TIME_TO_SLEEP * 1e3;
    Serial.print("Too Much time wasted, no deep sleep this iteration!");
    Serial.println();
    esp_sleep_enable_timer_wakeup(1); // still deepsleep but only 1us to activate timers
    esp_deep_sleep_start();
  } else {
    Serial.print("Sleep for: ");
    Serial.println((TIME_TO_SLEEP * 1e3 - t_total) / 1e3);
    Serial.println();
    Serial.println();
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0); //1 = High, 0 = Low
    esp_sleep_enable_timer_wakeup((TIME_TO_SLEEP * 1e3 - t_total) * uS_TO_S_FACTOR / 1e3);

    //Add the shutdown manualy before sleep, just to be sure
    esp_wifi_stop();
    esp_bt_controller_disable();
    esp_deep_sleep_start();
  }
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
