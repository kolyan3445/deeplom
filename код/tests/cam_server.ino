#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_wifi.h>
#include <soc/rtc_cntl_reg.h>
#include <soc/soc.h>

// wifi
#define WIFI_SSID "ESP32-CAM"
#define WIFI_PASS "12345678"

// camera pins Ai Thinker
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// camera init
bool cameraInit(framesize_t frame_size, pixformat_t pixel_format, int jpeg_quality) {
    esp_wifi_set_ps(WIFI_PS_NONE);              // no power save
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);  // disable brownout

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.frame_size = FRAMESIZE_UXGA;
    config.pixel_format = PIXFORMAT_JPEG;  // for streaming
    //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    
    if (config.pixel_format == PIXFORMAT_JPEG) {
      if (psramFound()) {
        config.jpeg_quality = 10;
        config.fb_count = 2;
        config.grab_mode = CAMERA_GRAB_LATEST;
      } else {
        // Limit the frame size when PSRAM is not available
        config.frame_size = FRAMESIZE_SVGA;
        config.fb_location = CAMERA_FB_IN_DRAM;
      }
    } else {
      // Best option for face detection/recognition
      config.frame_size = FRAMESIZE_240X240;
    }
    
    return esp_camera_init(&config) == ESP_OK;
}

WebServer server(80);

void setup() {
    Serial.begin(115200);
    Serial.println();

    // camera
    if (!cameraInit(FRAMESIZE_VGA, PIXFORMAT_JPEG, 4)) {
        Serial.println("Camera error");
        for (;;);
    }

    // wifi
    WiFi.softAP(WIFI_SSID, WIFI_PASS);
  
    server.on("/image", []() {
        Serial.println("HTTP request received");
        
        camera_fb_t* fb = esp_camera_fb_get();
        sensor_t *s = esp_camera_sensor_get();
        
        if (s->id.PID == OV3660_PID) {
            s->set_vflip(s, 1);        // flip it back
            s->set_brightness(s, 1);   // up the brightness just a bit
            s->set_saturation(s, -2);  // lower the saturation
        }
        if (fb) {
            server.setContentLength(fb->len);
            server.send(200, "image/jpeg", "");
            server.sendContent((const char*)fb->buf, fb->len);
        }
        esp_camera_fb_return(fb);
    });
    server.begin();

}

void loop() {

    server.handleClient();
    
}
