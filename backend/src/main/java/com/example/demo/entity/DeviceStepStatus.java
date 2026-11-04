
package com.example.demo.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
        name = "device_step_status",
        uniqueConstraints = {
                @UniqueConstraint(
                        columnNames = {"device_id", "step_date"}
                )
        }
)
@Getter
@Setter
@NoArgsConstructor
public class DeviceStepStatus {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 키링 고유 식별값
    @Column(name = "device_id", nullable = false)
    private String deviceId;

    // 걸음 수 기록 날짜
    @Column(name = "step_date", nullable = false)
    private LocalDate stepDate;

    // 해당 날짜 누적 걸음 수
    @Column(nullable = false)
    private Integer steps = 0;

    // 마지막 수신 시각
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public DeviceStepStatus(String deviceId, LocalDate stepDate) {
        this.deviceId = deviceId;
        this.stepDate = stepDate;
        this.steps = 0;
    }
}
