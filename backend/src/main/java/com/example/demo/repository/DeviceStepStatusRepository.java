
package com.example.demo.repository;

import com.example.demo.entity.DeviceStepStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.Optional;

public interface DeviceStepStatusRepository
        extends JpaRepository<DeviceStepStatus, Long> {

    // 기기와 날짜로 걸음 수 조회
    Optional<DeviceStepStatus> findByDeviceIdAndStepDate(
            String deviceId,
            LocalDate stepDate
    );
}
