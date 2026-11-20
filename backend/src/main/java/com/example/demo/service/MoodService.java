
package com.example.demo.service;

import com.example.demo.domain.CharacterRepository;
import com.example.demo.domain.CharacterStatus;
import com.example.demo.entity.Emotion;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class MoodService {

    private static final Long DEFAULT_USER_ID = 1L;

    private final CharacterRepository characterRepository;
    private final MessageChannel mqttOutboundChannel;
    private final ObjectMapper objectMapper;
    private final String moodTopic;

    public MoodService(
            CharacterRepository characterRepository,
            @Qualifier("mqttOutboundChannel")
            MessageChannel mqttOutboundChannel,
            ObjectMapper objectMapper,
            @Value("${orbit.mqtt.mood-topic}") String moodTopic
    ) {
        this.characterRepository = characterRepository;
        this.mqttOutboundChannel = mqttOutboundChannel;
        this.objectMapper = objectMapper;
        this.moodTopic = moodTopic;
    }

    // 앱에서 현재 감정 조회
    @Transactional(readOnly = true)
    public String getMood() {

        CharacterStatus character = characterRepository
                .findByUserId(DEFAULT_USER_ID)
                .orElseThrow(() ->
                        new IllegalStateException(
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        return character.getEmotionStatus();
    }

    // 앱에서 감정 변경
    @Transactional
    public synchronized void setMood(String mood) {

        Emotion emotion = Emotion.fromString(mood);
        String newMood = emotion.toJson();

        CharacterStatus character = characterRepository
                .findByUserId(DEFAULT_USER_ID)
                .orElseThrow(() ->
                        new IllegalStateException(
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        // 1. DB 감정 상태 변경
        character.setEmotionStatus(newMood);
        characterRepository.save(character);

        try {
            // 2. OLED 변경 명령
            // Stage와 LED는 변경하지 않음
            Map<String, Object> command = new LinkedHashMap<>();

            command.put("vibe", "short");
            command.put("oled", newMood);

            String payload = objectMapper.writeValueAsString(command);

            // 3. MQTT 전송
            boolean sent = mqttOutboundChannel.send(
                    MessageBuilder.withPayload(payload)
                            .setHeader(MqttHeaders.TOPIC, moodTopic)
                            .setHeader(MqttHeaders.QOS, 1)
                            .build()
            );

            if (!sent) {
                throw new IllegalStateException(
                        "MQTT 전송 실패"
                );
            }

            System.out.println("[무드 변경] " + newMood);
            System.out.println("[MQTT Topic] " + moodTopic);
            System.out.println("[MQTT Payload] " + payload);

        } catch (Exception e) {
            throw new IllegalStateException(
                    "무드 변경 처리 실패", e
            );
        }
    }
}
