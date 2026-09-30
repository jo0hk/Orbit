package com.example.demo.controller;

import com.example.demo.dto.MissionResponse;
import com.example.demo.service.MissionService;

import lombok.RequiredArgsConstructor;

import org.springframework.web.bind.annotation.*;

import java.util.List;

import com.example.demo.dto.MissionResultRequest;

@RestController
@RequestMapping("/api/missions")
@RequiredArgsConstructor
public class MissionController {

    private final MissionService missionService;

    // 전체 미션 목록 조회
    @GetMapping
    public List<MissionResponse> getAllMissions() {

        return missionService.getAllMissions();
    }

    // 오늘의 미션 배정
    @PostMapping("/today/assign")
    public MissionResponse assignTodayMission(
            @RequestParam Integer userId
    ) {

        return missionService.assignTodayMission(userId);
    }

    // 오늘의 미션 조회
    @GetMapping("/current")
    public MissionResponse getCurrentMission(
            @RequestParam Integer userId
    ) {

        return missionService.getCurrentMission(userId);
    }

    // 미션 진행 기록 조회
    @GetMapping("/progress")
    public List<MissionResponse> getMissionProgress(
            @RequestParam Integer userId
    ) {

        return missionService.getMissionProgress(userId);
    }

    // AI 미션 판정 결과 수신
    @PostMapping("/{missionId}/result")
    public MissionResponse processMissionResult(
            @PathVariable Long missionId,
            @RequestBody MissionResultRequest request
    ) {

        return missionService.processMissionResult(
                missionId,
                request
        );
    }
}