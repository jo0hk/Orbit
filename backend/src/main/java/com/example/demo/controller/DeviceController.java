package com.example.demo.controller;

import com.example.demo.dto.DeviceRequest;
import com.example.demo.dto.DeviceResponse;
import com.example.demo.service.DeviceService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/devices")
@RequiredArgsConstructor
public class DeviceController {

    private final DeviceService deviceService;

    // 기기 등록
    @PostMapping
    public DeviceResponse registerDevice(
            @RequestBody DeviceRequest request
    ) {
        return deviceService.registerDevice(request);
    }

    // 기기 조회
    @GetMapping("/{deviceId}")
    public DeviceResponse getDevice(
            @PathVariable String deviceId
    ) {
        return deviceService.getDevice(deviceId);
    }

    // 기기에 연결된 charId 조회
    @GetMapping("/{deviceId}/character")
    public Long getCharacterId(
            @PathVariable String deviceId
    ) {
        return deviceService.getCharIdByDeviceId(deviceId);
    }
}