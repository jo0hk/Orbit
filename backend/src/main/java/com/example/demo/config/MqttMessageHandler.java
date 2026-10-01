package com.example.demo.config;

import com.example.demo.service.CharacterService;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;
import com.example.demo.service.DeviceService;

@Component
public class MqttMessageHandler {

    private final CharacterService characterService;
    private final DeviceService deviceService;
    
    public MqttMessageHandler(
            CharacterService characterService,
            DeviceService deviceService
    ) {
        this.characterService = characterService;
        this.deviceService = deviceService;
    }

    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handleMessage(Message<?> message) {

        String payload =
                message.getPayload().toString().trim();

        String topic = String.valueOf(
                message.getHeaders()
                        .get("mqtt_receivedTopic")
        );
        String[] parts = topic.split("/");

        if (parts.length != 3) {
            System.out.println("잘못된 MQTT topic 형식: " + topic);
            return;
        }

        String deviceId = parts[1];

        Long charId =
                deviceService.getCharIdByDeviceId(deviceId);

        System.out.println("================================");
        System.out.println("MQTT 메시지 수신");
        System.out.println("topic: " + topic);
        System.out.println("payload: " + payload);
        System.out.println("================================");

        if ("FUEL_UP".equals(payload)) {

            characterService.chargeFuel(charId, 10);
            System.out.println("연료 10 충전 완료!");

        } else if ("LOVE_UP".equals(payload)) {

            characterService.updateIntimacy(charId, 5);
            System.out.println("친밀도 5 상승 완료!");

        } else if ("JACKPOT_SUCCESS".equals(payload)) {

            characterService.chargeFuel(charId, 10);
            characterService.updateIntimacy(charId, 5);

            System.out.println(
                    "잭팟 성공 처리 완료! 연료 10 충전, 친밀도 5 상승"
            );

        } else if ("happy".equalsIgnoreCase(payload)) {

            characterService.updateEmotionStatus(
                    charId,
                    "happy"
            );

            System.out.println(
                    "감정 상태 happy로 변경 완료!"
            );

        } else if ("sad".equalsIgnoreCase(payload)) {

            characterService.updateEmotionStatus(
                    charId,
                    "sad"
            );

            System.out.println(
                    "감정 상태 sad로 변경 완료!"
            );

        } else if ("angry".equalsIgnoreCase(payload)) {

            characterService.updateEmotionStatus(
                    charId,
                    "angry"
            );

            System.out.println(
                    "감정 상태 angry로 변경 완료!"
            );

        } else if ("calm".equalsIgnoreCase(payload)) {

            characterService.updateEmotionStatus(
                    charId,
                    "calm"
            );

            System.out.println(
                    "감정 상태 calm으로 변경 완료!"
            );

        } else if ("TOUCHED".equals(payload)) {

            characterService.updateEmotionStatus(
                    charId,
                    "happy"
            );

            characterService.updateIntimacy(
                    charId,
                    5
            );

            System.out.println(
                    "터치 이벤트 수신! 감정 happy 변경, 친밀도 5 상승 완료!"
            );

        } else {

            System.out.println(
                    "알 수 없는 MQTT 메시지: " + payload
            );
        }
    }
}