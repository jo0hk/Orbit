
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
    private Long userId;

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

    // 연료 증가 (최대 100%)
    public void addFuel(int amount) {

        if (amount < 0) {
            throw new IllegalArgumentException(
                    "연료 증가량은 0 이상이어야 합니다."
            );
        }

        if (this.fuelGauge == null) {
            this.fuelGauge = 0;
        }

        this.fuelGauge = (int) Math.min(
                100L,
                (long) this.fuelGauge + amount
        );
    }
}
