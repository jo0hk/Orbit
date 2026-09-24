package com.example.demo.controller;

import com.example.demo.dto.WalkAiRequest;
import com.example.demo.service.WalkAiService;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/ai/walk")
@CrossOrigin(origins = "*")
public class WalkAiController {

    private final WalkAiService walkAiService;

    public WalkAiController(WalkAiService walkAiService) {
        this.walkAiService = walkAiService;
    }

    @PostMapping
    public Map<String, String> requestWalkAi(@RequestBody WalkAiRequest request) {

        String prompt = walkAiService.createWalkPrompt(request);

        System.out.println("================================");
        System.out.println("AI 요청용 프롬프트 생성 완료");
        System.out.println(prompt);
        System.out.println("================================");

        return Map.of(
                "prompt", prompt,
                "answer", "현재 위치와 날씨 정보를 바탕으로 산책 조언을 생성했습니다. 추후 Gemini API 응답으로 교체 예정입니다."
        );
    }
}