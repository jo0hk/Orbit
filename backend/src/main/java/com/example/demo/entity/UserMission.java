
package com.example.demo.entity;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
        name = "user_missions",
        uniqueConstraints = @UniqueConstraint(
                columnNames = {"user_id", "assigned_date"}
        )
)
public class UserMission {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "mission_id", nullable = false)
    private Mission mission;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private MissionStatus status;

    @Column(name = "assigned_date", nullable = false)
    private LocalDate assignedDate;

    private LocalDateTime completedAt;

    protected UserMission() {
    }

    // 미션 생성 시 날짜를 외부에서 전달받음
    public UserMission(
            Long userId,
            Mission mission,
            LocalDate assignedDate
    ) {
        this.userId = userId;
        this.mission = mission;
        this.status = MissionStatus.IN_PROGRESS;
        this.assignedDate = assignedDate;
    }

    // 미션 완료 처리
    public void complete(LocalDateTime completedAt) {
        if (this.status == MissionStatus.COMPLETED) {
            return;
        }

        this.status = MissionStatus.COMPLETED;
        this.completedAt = completedAt;
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public Mission getMission() {
        return mission;
    }

    public MissionStatus getStatus() {
        return status;
    }

    public LocalDate getAssignedDate() {
        return assignedDate;
    }

    public LocalDateTime getCompletedAt() {
        return completedAt;
    }
}
