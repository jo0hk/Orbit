
package com.example.demo.repository;

import com.example.demo.entity.Device;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface DeviceRepository
        extends JpaRepository<Device, Long> {

    Optional<Device> findByDeviceId(String deviceId);

    Optional<Device> findByCharId(Long charId);

    // 사용자 ID 타입을 Long으로 통일
    Optional<Device> findByUserId(Long userId);

    boolean existsByDeviceId(String deviceId);

    boolean existsByCharId(Long charId);

    boolean existsByUserId(Long userId);
}
