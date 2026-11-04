package com.example.demo.service;

import com.example.demo.entity.Emotion;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class MoodService {

    private final MessageChannel mqttOutboundChannel;
    private final ObjectMapper objectMapper;
    private final String moodTopic;

    private volatile String currentMood = "happy";

    public MoodService(
            @Qualifier("mqttOutboundChannel") MessageChannel mqttOutboundChannel,
            ObjectMapper objectMapper,
            @Value("${orbit.mqtt.mood-topic}") String moodTopic
    ) {
        this.mqttOutboundChannel = mqttOutboundChannel;
        this.objectMapper = objectMapper;
        this.moodTopic = moodTopic;
    }

    public String getMood() {
        return currentMood;
    }

    public synchronized void setMood(String mood) {

        // 1. 감정값 검증
        Emotion emotion = Emotion.fromString(mood);
        String newMood = emotion.toJson();

        try {
            // 2. HW OLED용 JSON 생성
            Map<String, Object> command = new LinkedHashMap<>();

            command.put("stage", 1);
            command.put("led", "blue");
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
                throw new IllegalStateException("MQTT 전송 실패");
            }

            // 4. 앱 조회용 무드 변경
            currentMood = newMood;

            System.out.println("[무드 변경] " + currentMood);
            System.out.println("[MQTT Topic] " + moodTopic);
            System.out.println("[MQTT Payload] " + payload);

        } catch (Exception e) {
            throw new IllegalStateException("무드 변경 처리 실패", e);
        }
    }
}