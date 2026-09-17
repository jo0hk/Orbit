package com.example.demo.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(name = "character_status")
public class CharacterStatus {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long charId;

    @Column(name = "user_id")
    private Integer userId;

    @Column(name = "fuel_gauge")
    private Integer fuelGauge = 35;

    private Integer closeness = 0;

    @Column(name = "current_stage")
    private Integer currentStage = 1;

    @Column(name = "emotion_status")
    private String emotionStatus = "NORMAL";

    @Column(name = "last_action_at")
    private LocalDateTime lastActionAt;

    private Integer intimacy = 0;

    // 친밀도를 높이는 메서드
    public void addIntimacy(int amount) {
        if (this.intimacy == null) {
            this.intimacy = 0;
        }

        this.intimacy += amount;
    }
}