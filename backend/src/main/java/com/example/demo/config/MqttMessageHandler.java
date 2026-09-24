package com.example.demo.config;

import com.example.demo.service.CharacterService;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;

@Component
public class MqttMessageHandler {

    private final CharacterService characterService;

    public MqttMessageHandler(CharacterService characterService) {
        this.characterService = characterService;
    }

    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handleMessage(Message<?> message) {

        String payload = message.getPayload().toString().trim();
        String topic = String.valueOf(message.getHeaders().get("mqtt_receivedTopic"));

        Long charId = 1L;
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

        } else if ("STAGE_UP".equals(payload)) {
            characterService.increaseStage(charId);
            System.out.println("스테이지 증가 완료!");

        } else if ("JACKPOT_SUCCESS".equals(payload)) {
            characterService.chargeFuel(charId, 10);
            characterService.updateIntimacy(charId, 5);
            System.out.println("잭팟 성공 처리 완료! 연료 10 충전, 친밀도 5 상승");

        } else if ("EMOTION_HAPPY".equals(payload)) {
            characterService.updateEmotionStatus(charId, "HAPPY");
            System.out.println("감정 상태 HAPPY로 변경 완료!");

        } else if ("EMOTION_SAD".equals(payload)) {
            characterService.updateEmotionStatus(charId, "SAD");
            System.out.println("감정 상태 SAD로 변경 완료!");

        } else if ("TOUCHED".equals(payload)) { // 하드웨어-벡엔드 연동부분 터치 센서 감지 출력
            characterService.updateEmotionStatus(charId, "HAPPY");
            characterService.updateIntimacy(charId, 5);
            System.out.println("터치 이벤트 수신! 감정 HAPPY 변경, 친밀도 5 상승 완료!");

        } else {
            System.out.println("알 수 없는 MQTT 메시지: " + payload);
        }
    }
}