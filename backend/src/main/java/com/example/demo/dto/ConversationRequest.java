package com.example.demo.dto;

import com.example.demo.entity.Speaker;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ConversationRequest {

    private Long userId;
    private Speaker speaker;
    private String message;
}
