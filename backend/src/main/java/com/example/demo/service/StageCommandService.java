
package com.example.demo.service;

import com.example.demo.entity.Device;
import com.example.demo.repository.DeviceRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class StageCommandService {

    private final DeviceRepository deviceRepository;
    private final MessageChannel mqttOutboundChannel;
    private final ObjectMapper objectMapper;

    public StageCommandService(
            DeviceRepository deviceRepository,
            @Qualifier("mqttOutboundChannel")
            MessageChannel mqttOutboundChannel,
            ObjectMapper objectMapper
    ) {
        this.deviceRepository = deviceRepository;
        this.mqttOutboundChannel = mqttOutboundChannel;
        this.objectMapper = objectMapper;
    }

    // 미션 성공 후 키링에 Stage 변경 명령 전송
    public void sendStage(Long userId, Integer stage) {

        // 1. Stage 값 검증
        if (stage == null || stage < 1 || stage > 4) {
            throw new IllegalArgumentException(
                    "유효하지 않은 Stage입니다."
            );
        }

        // 2. 사용자와 연결된 디바이스 조회
        Device device = deviceRepository.findByUserId(userId)
                .orElseThrow(() ->
                        new IllegalStateException(
                                "사용자에 연결된 디바이스가 없습니다."
                        )
                );

        // 3. 디바이스별 MQTT command 토픽
        String topic = "orbit/" + device.getDeviceId()
                + "/command";

        // 4. 변경된 Stage만 JSON으로 생성
        String payload;

        try {
            payload = objectMapper.writeValueAsString(
                    Map.of("stage", stage)
            );
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(
                    "Stage 명령 JSON 생성 실패", e
            );
        }

        // 5. MQTT 명령 발행
        boolean sent = mqttOutboundChannel.send(
                MessageBuilder.withPayload(payload)
                        .setHeader(MqttHeaders.TOPIC, topic)
                        .setHeader(MqttHeaders.QOS, 1)
                        .build()
        );

        if (!sent) {
            throw new IllegalStateException(
                    "Stage MQTT 전송 요청 실패"
            );
        }

        System.out.println("[Stage 변경 MQTT 발행]");
        System.out.println("[User ID] " + userId);
        System.out.println("[MQTT Topic] " + topic);
        System.out.println("[MQTT Payload] " + payload);
    }
}
