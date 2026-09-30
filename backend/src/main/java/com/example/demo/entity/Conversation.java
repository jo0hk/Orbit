package com.example.demo.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "conversations")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Conversation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;

    @Enumerated(EnumType.STRING)
    private Speaker speaker;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String message;

    private LocalDateTime createdAt;

    // 감정: happy, sad, angry, calm
    private String emotion;

    // 대화 당시 단계: 1~4
    private Integer stage;

    // 대화 채널: TEXT 또는 VOICE
    @Enumerated(EnumType.STRING)
    private ConversationChannel channel;

    // AI 요청 식별값 (중복 저장 방지)
    private String requestId;

    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
    }
}