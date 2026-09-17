package com.example.demo.service;

import com.example.demo.dto.WalkAiRequest;
import org.springframework.stereotype.Service;

@Service
public class WalkAiService {

    public String createWalkPrompt(WalkAiRequest request) {

        validateWalkData(request);

        String prompt = """
                너는 사용자의 산책 상황을 분석해서 조언해주는 AI야.

                [산책 데이터]
                이동 거리: %.2f km
                산책 시간: %d분
                현재 위치: %s
                현재 날씨: %s

                [사용자 질문]
                %s

                위 정보를 바탕으로 사용자가 산책을 계속해도 괜찮은지,
                날씨나 컨디션 측면에서 주의할 점이 있는지 자연스럽게 답변해줘.
                """.formatted(
                request.getDistance(),
                request.getDuration(),
                request.getLocation(),
                request.getWeather(),
                request.getMessage()
        );

        return prompt;
    }

    private void validateWalkData(WalkAiRequest request) {

        if (request == null) {
            throw new IllegalArgumentException("요청 데이터가 비어 있습니다.");
        }

        if (request.getDistance() == null || request.getDistance() < 0) {
            throw new IllegalArgumentException("산책 거리는 0 이상이어야 합니다.");
        }

        if (request.getDuration() == null || request.getDuration() <= 0) {
            throw new IllegalArgumentException("산책 시간은 0보다 커야 합니다.");
        }

        if (request.getLocation() == null || request.getLocation().isBlank()) {
            throw new IllegalArgumentException("현재 위치 정보가 필요합니다.");
        }

        if (request.getWeather() == null || request.getWeather().isBlank()) {
            throw new IllegalArgumentException("현재 날씨 정보가 필요합니다.");
        }

        if (request.getMessage() == null || request.getMessage().isBlank()) {
            throw new IllegalArgumentException("사용자 질문이 필요합니다.");
        }

        if (request.getDistance() > 100) {
            throw new IllegalArgumentException("산책 거리가 너무 큽니다. 값을 다시 확인해주세요.");
        }

        if (request.getDuration() > 1440) {
            throw new IllegalArgumentException("산책 시간이 너무 깁니다. 값을 다시 확인해주세요.");
        }
    }
}