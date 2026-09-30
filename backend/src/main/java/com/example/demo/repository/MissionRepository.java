package com.example.demo.repository;

import com.example.demo.entity.Mission;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface MissionRepository
        extends JpaRepository<Mission, Long> {

    Optional<Mission> findByStage(Integer stage);
}