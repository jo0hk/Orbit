package com.example.demo.dto;

import com.example.demo.entity.Speaker;
import lombok.Getter;
import lombok.Setter;
import com.example.demo.entity.ConversationChannel;

@Getter
@Setter
public class ConversationRequest {

    private Long userId;
    private Speaker speaker;
    private String message;

    private String emotion;
    private Integer stage;
    private ConversationChannel channel;
    private String requestId;
}
