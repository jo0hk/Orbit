package com.example.demo.dto;

public class DeviceCommandDto {

    private Integer stage;
    private String led;
    private String vibe;
    private String oled;

    public Integer getStage() {
        return stage;
    }

    public void setStage(Integer stage) {
        this.stage = stage;
    }

    public String getLed() {
        return led;
    }

    public void setLed(String led) {
        this.led = led;
    }

    public String getVibe() {
        return vibe;
    }

    public void setVibe(String vibe) {
        this.vibe = vibe;
    }

    public String getOled() {
        return oled;
    }

    public void setOled(String oled) {
        this.oled = oled;
    }
}