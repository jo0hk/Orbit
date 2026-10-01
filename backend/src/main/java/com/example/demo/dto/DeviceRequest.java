package com.example.demo.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class DeviceRequest {

    private String deviceId;

    private Long charId;

    private Integer userId;
}