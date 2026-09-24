package com.example.demo.service;

import org.springframework.stereotype.Service;

@Service
public class MoodService {

    private String currentMood = "happy";

    public String getMood() {
        return currentMood;
    }

    public void setMood(String mood) {
        this.currentMood = mood;
        System.out.println("현재 mood 변경됨: " + currentMood);
    }
}