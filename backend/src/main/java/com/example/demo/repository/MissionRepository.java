package com.example.demo.repository;

import com.example.demo.entity.Mission;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.Comparator;

public interface MissionRepository
        extends JpaRepository<Mission, Long> {

    Optional<Mission> findByStage(Integer stage);
    List<Mission> findAllByStageOrderByIdAsc(Integer stage);
}