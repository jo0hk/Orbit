package com.example.demo.config;

import com.example.demo.service.CharacterService;
import com.example.demo.service.DeviceService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;

@Component
public class MqttMessageHandler {

    private final CharacterService characterService;
    private final DeviceService deviceService;
    private final ObjectMapper objectMapper;

    public MqttMessageHandler(
            CharacterService characterService,
            DeviceService deviceService,
            ObjectMapper objectMapper
    ) {
        this.characterService = characterService;
        this.deviceService = deviceService;
        this.objectMapper = objectMapper;
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
            System.out.println(
                    "잘못된 MQTT topic 형식: " + topic
            );
            return;
        }

        String deviceId = parts[1];

        Long charId;

        try {
            charId =
                    deviceService.getCharIdByDeviceId(
                            deviceId
                    );
        } catch (Exception e) {
            System.out.println(
                    "등록되지 않은 deviceId: "
                            + deviceId
            );
            return;
        }

        System.out.println(
                "================================"
        );
        System.out.println("[MQTT 메시지 수신]");
        System.out.println("topic    : " + topic);
        System.out.println("deviceId : " + deviceId);
        System.out.println("charId   : " + charId);
        System.out.println("payload  : " + payload);
        System.out.println(
                "================================"
        );

        /*
         * JSON 상태 메시지 처리
         *
         * 예:
         * {
         *   "steps": 120,
         *   "stage": 2,
         *   "uptime": 38400
         * }
         */
        if (payload.startsWith("{")) {

            try {

                JsonNode json =
                        objectMapper.readTree(payload);

                Integer steps =
                        json.has("steps")
                                ? json.get("steps").asInt()
                                : null;

                Integer stage =
                        json.has("stage")
                                ? json.get("stage").asInt()
                                : null;

                Long uptime =
                        json.has("uptime")
                                ? json.get("uptime").asLong()
                                : null;

                System.out.println(
                        "[HW 상태 JSON 수신]"
                );
                System.out.println(
                        "steps  : " + steps
                );
                System.out.println(
                        "stage  : " + stage
                );
                System.out.println(
                        "uptime : " + uptime
                );

                /*
                 * 현재는 연동 확인용으로
                 * JSON 값을 파싱해서 로그만 출력.
                 *
                 * 나중에 필요하면
                 * steps 등을 DB에 저장하면 됨.
                 */

            } catch (Exception e) {

                System.out.println(
                        "JSON 파싱 실패: "
                                + payload
                );
            }

            return;
        }

        /*
         * 기존 문자열 이벤트 처리
         */

        if ("FUEL_UP".equals(payload)) {

            characterService.chargeFuel(
                    charId,
                    10
            );

            System.out.println(
                    "연료 10 충전 완료!"
            );

        } else if ("LOVE_UP".equals(payload)) {

            characterService.updateIntimacy(
                    charId,
                    5
            );

            System.out.println(
                    "친밀도 5 상승 완료!"
            );

        } else if (
                "JACKPOT_SUCCESS".equals(payload)
        ) {

            characterService.chargeFuel(
                    charId,
                    10
            );

            characterService.updateIntimacy(
                    charId,
                    5
            );

            System.out.println(
                    "잭팟 성공 처리 완료! "
                            + "연료 10 충전, "
                            + "친밀도 5 상승"
            );

        } else if (
                "happy".equalsIgnoreCase(payload)
        ) {

            characterService.updateEmotionStatus(
                    charId,
                    "happy"
            );

            System.out.println(
                    "감정 상태 happy로 변경 완료!"
            );

        } else if (
                "sad".equalsIgnoreCase(payload)
        ) {

            characterService.updateEmotionStatus(
                    charId,
                    "sad"
            );

            System.out.println(
                    "감정 상태 sad로 변경 완료!"
            );

        } else if (
                "angry".equalsIgnoreCase(payload)
        ) {

            characterService.updateEmotionStatus(
                    charId,
                    "angry"
            );

            System.out.println(
                    "감정 상태 angry로 변경 완료!"
            );

        } else if (
                "calm".equalsIgnoreCase(payload)
        ) {

            characterService.updateEmotionStatus(
                    charId,
                    "calm"
            );

            System.out.println(
                    "감정 상태 calm으로 변경 완료!"
            );

        } else if (
                "TOUCHED".equals(payload)
                        || "TOUCH_LONG".equals(payload)
        ) {

            characterService.updateEmotionStatus(
                    charId,
                    "happy"
            );

            characterService.updateIntimacy(
                    charId,
                    5
            );

            System.out.println(
                    "터치 이벤트 수신! "
                            + "감정 happy 변경, "
                            + "친밀도 5 상승 완료!"
            );

        } else if (
                "SHAKE".equals(payload)
        ) {

            /*
             * 현재는 연동 테스트용 임시 처리.
             * 최종 정책이 정해지면
             * emotion 변경 등의 로직 수정 가능.
             */

            System.out.println(
                    "흔들기 이벤트 SHAKE 수신 완료!"
            );

        } else if (
                "STEP_TICK".equals(payload)
        ) {

            /*
             * HW가 STEP_TICK 문자열만 보낼 경우
             * 이벤트 수신 여부만 확인.
             *
             * 실제 steps 값은 JSON 상태 메시지에서
             * 받는 방식 권장.
             */

            System.out.println(
                    "STEP_TICK 이벤트 수신 완료!"
            );

        } else {

            System.out.println(
                    "알 수 없는 MQTT 메시지: "
                            + payload
            );
        }
    }
}