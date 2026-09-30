package com.example.demo.repository;

import com.example.demo.entity.UserMission;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface UserMissionRepository
        extends JpaRepository<UserMission, Long> {

    // 특정 사용자의 오늘 미션 조회
    Optional<UserMission> findByUserIdAndAssignedDate(
            Long userId,
            LocalDate assignedDate
    );

    // 특정 사용자의 미션 진행 기록 조회
    List<UserMission> findAllByUserIdOrderByAssignedDateDescIdDesc(
            Long userId
    );
}