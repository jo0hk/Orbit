package com.example.demo.dto;

import com.example.demo.entity.ConversationChannel;
import com.example.demo.entity.Speaker;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
public class ConversationResponse {

    private Long id;
    private Long userId;
    private Speaker speaker;
    private String message;
    private LocalDateTime createdAt;

    private String emotion;
    private Integer stage;
    private ConversationChannel channel;
    private String requestId;


}