
package com.example.demo.service;

import com.example.demo.entity.DeviceStepStatus;
import com.example.demo.repository.DeviceStepStatusRepository;

import lombok.RequiredArgsConstructor;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;

@Service
@RequiredArgsConstructor
public class DeviceStepService {

    private final DeviceStepStatusRepository stepRepository;

    private static final ZoneId ZONE =
            ZoneId.of("Asia/Seoul");

    // HW에서 받은 오늘의 누적 걸음 수 저장
    @Transactional
    public void updateSteps(String deviceId, int steps) {

        if (steps < 0) {
            throw new IllegalArgumentException(
                    "걸음 수는 0 이상이어야 합니다."
            );
        }

        LocalDate today = LocalDate.now(ZONE);

        // 오늘 기록이 없으면 새로 생성
        DeviceStepStatus status = stepRepository
                .findByDeviceIdAndStepDate(deviceId, today)
                .orElseGet(() ->
                        new DeviceStepStatus(deviceId, today)
                );

        // 이미 받은 누적값을 다시 더하지 않음
        // 같은 날 오래된 값이 들어와도 기록이 감소하지 않도록 처리
        status.setSteps(
                Math.max(status.getSteps(), steps)
        );

        status.setUpdatedAt(LocalDateTime.now(ZONE));

        stepRepository.save(status);
    }

    // 오늘의 걸음 수 조회
    @Transactional(readOnly = true)
    public int getTodaySteps(String deviceId) {

        LocalDate today = LocalDate.now(ZONE);

        return stepRepository
                .findByDeviceIdAndStepDate(deviceId, today)
                .map(DeviceStepStatus::getSteps)
                .orElse(0);
    }
}
