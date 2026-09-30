
package com.example.demo.service;

import com.example.demo.entity.Emotion;
import org.springframework.stereotype.Service;

@Service
public class MoodService {

    private String currentMood = "happy";

    public String getMood() {
        return currentMood;
    }

    public void setMood(String mood) {

        Emotion emotion = Emotion.fromString(mood);

        this.currentMood = emotion.toJson();

        System.out.println("현재 mood 변경됨: " + currentMood);
    }
}
