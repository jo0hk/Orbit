
package com.example.demo.controller;

import com.example.demo.service.DeviceStepService;

import lombok.RequiredArgsConstructor;

import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/devices")
@RequiredArgsConstructor
public class DeviceStepController {

    private final DeviceStepService deviceStepService;

    // 앱에서 오늘의 걸음 수 조회
    @GetMapping("/{deviceId}/steps")
    public Map<String, Object> getTodaySteps(
            @PathVariable String deviceId
    ) {

        int steps = deviceStepService.getTodaySteps(deviceId);

        return Map.of(
                "deviceId", deviceId,
                "steps", steps
        );
    }
}
