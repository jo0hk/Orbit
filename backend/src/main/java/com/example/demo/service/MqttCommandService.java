package com.example.demo.service;

import com.example.demo.config.MqttGateway;
import org.springframework.stereotype.Service;

@Service
public class MqttCommandService {

    private final MqttGateway mqttGateway;

    public MqttCommandService(
            MqttGateway mqttGateway
    ) {
        this.mqttGateway = mqttGateway;
    }

    public void sendCommand(
            String deviceId,
            String payload
    ) {

        String topic =
                "orbit/"
                        + deviceId
                        + "/command";

        mqttGateway.send(
                topic,
                payload
        );

        System.out.println(
                "[MQTT 명령 전송]"
        );
        System.out.println(
                "topic   : " + topic
        );
        System.out.println(
                "payload : " + payload
        );
    }
}