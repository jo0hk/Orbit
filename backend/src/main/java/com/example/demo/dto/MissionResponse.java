package com.example.demo.dto;

import com.example.demo.entity.Mission;
import com.example.demo.entity.MissionStatus;
import com.example.demo.entity.MissionType;
import com.example.demo.entity.UserMission;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class MissionResponse {

    private Long missionId;
    private Integer stage;
    private String title;
    private String description;
    private MissionType missionType;

    private MissionStatus status;
    private LocalDate assignedDate;
    private LocalDateTime completedAt;

    // 전체 미션 목록 조회용
    public static MissionResponse from(Mission mission) {

        return new MissionResponse(
                mission.getId(),
                mission.getStage(),
                mission.getTitle(),
                mission.getDescription(),
                mission.getMissionType(),
                null,
                null,
                null
        );
    }

    // 사용자 미션 조회용
    public static MissionResponse from(UserMission userMission) {

        Mission mission = userMission.getMission();

        return new MissionResponse(
                mission.getId(),
                mission.getStage(),
                mission.getTitle(),
                mission.getDescription(),
                mission.getMissionType(),
                userMission.getStatus(),
                userMission.getAssignedDate(),
                userMission.getCompletedAt()
        );
    }
}