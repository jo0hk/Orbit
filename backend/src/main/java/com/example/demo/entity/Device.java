package com.example.demo.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
        name = "devices",
        uniqueConstraints = {
                @UniqueConstraint(columnNames = "device_id"),
                @UniqueConstraint(columnNames = "char_id")
        }
)
@Getter
@Setter
@NoArgsConstructor
public class Device {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 실제 키링 고유 식별값
    @Column(name = "device_id", nullable = false, unique = true)
    private String deviceId;

    // 연결된 캐릭터 ID
    @Column(name = "char_id", nullable = false, unique = true)
    private Long charId;

    // 연결된 사용자 ID
    @Column(name = "user_id", nullable = false, unique = true)
    private Integer userId;

    public Device(
            String deviceId,
            Long charId,
            Integer userId
    ) {
        this.deviceId = deviceId;
        this.charId = charId;
        this.userId = userId;
    }
}