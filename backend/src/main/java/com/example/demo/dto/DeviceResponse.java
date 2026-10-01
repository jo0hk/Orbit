package com.example.demo.dto;

import com.example.demo.entity.Device;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class DeviceResponse {

    private Long id;

    private String deviceId;

    private Long charId;

    private Integer userId;

    public static DeviceResponse from(Device device) {

        return DeviceResponse.builder()
                .id(device.getId())
                .deviceId(device.getDeviceId())
                .charId(device.getCharId())
                .userId(device.getUserId())
                .build();
    }
}