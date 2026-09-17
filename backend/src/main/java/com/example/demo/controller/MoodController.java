package com.example.demo.controller;

import com.example.demo.service.MoodService;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/mood")
@CrossOrigin(origins = "*")
public class MoodController {

    private final MoodService moodService;

    public MoodController(MoodService moodService) {
        this.moodService = moodService;
    }

    // 현재 mood 상태 확인
    @GetMapping
    public Map<String, String> getMood() {
        return Map.of("mood", moodService.getMood());
    }

    // mood 상태 변경
    @PostMapping
    public Map<String, String> updateMood(@RequestBody Map<String, String> request) {
        String mood = request.get("mood");
        moodService.setMood(mood);

        return Map.of("mood", moodService.getMood());
    }
}