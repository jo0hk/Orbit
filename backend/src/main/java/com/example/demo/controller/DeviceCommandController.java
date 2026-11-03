package com.example.demo.controller;

import com.example.demo.dto.DeviceCommandDto;
import com.example.demo.service.MqttCommandService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/devices")
public class DeviceCommandController {

    private final MqttCommandService mqttCommandService;
    private final ObjectMapper objectMapper;

    public DeviceCommandController(
            MqttCommandService mqttCommandService,
            ObjectMapper objectMapper
    ) {
        this.mqttCommandService = mqttCommandService;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/{deviceId}/command")
    public ResponseEntity<?> sendCommand(
            @PathVariable String deviceId,
            @RequestBody DeviceCommandDto request
    ) {

        try {
            String payload =
                    objectMapper.writeValueAsString(request);

            mqttCommandService.sendCommand(
                    deviceId,
                    payload
            );

            return ResponseEntity.ok(
                    "MQTT 명령 전송 완료"
            );

        } catch (Exception e) {

            return ResponseEntity
                    .internalServerError()
                    .body("MQTT 명령 전송 실패");
        }
    }
}