package com.example.demo.service;

import com.example.demo.domain.CharacterRepository;
import com.example.demo.domain.CharacterStatus;
import com.example.demo.dto.MissionResponse;
import com.example.demo.entity.Mission;
import com.example.demo.entity.UserMission;
import com.example.demo.repository.MissionRepository;
import com.example.demo.repository.UserMissionRepository;

import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;

import com.example.demo.dto.MissionResultRequest;
import com.example.demo.entity.MissionStatus;

@Service
@RequiredArgsConstructor
public class MissionService {

    private final MissionRepository missionRepository;
    private final UserMissionRepository userMissionRepository;
    private final CharacterRepository characterRepository;

    // 전체 미션 목록 조회
    @Transactional(readOnly = true)
    public List<MissionResponse> getAllMissions() {

        return missionRepository.findAll(
                        Sort.by("stage").ascending()
                ).stream()
                .map(MissionResponse::from)
                .toList();
    }

    // 오늘의 미션 배정
    @Transactional
    public MissionResponse assignTodayMission(Integer userId) {

        Long id = userId.longValue();

        LocalDate today =
                LocalDate.now(ZoneId.of("Asia/Seoul"));

        // 이미 오늘 배정된 미션이 있는지 확인
        var existing = userMissionRepository
                .findByUserIdAndAssignedDate(id, today);

        if (existing.isPresent()) {
            return MissionResponse.from(existing.get());
        }

        // 사용자 캐릭터 조회
        CharacterStatus character = characterRepository
                .findByUserId(userId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        // 현재 단계 확인
        Integer stage = character.getCurrentStage();

        // 현재 단계에 해당하는 미션 조회
        Mission mission = missionRepository
                .findByStage(stage)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "해당 단계의 미션이 없습니다."
                        )
                );

        // 오늘의 미션 생성 및 저장
        UserMission userMission =
                new UserMission(id, mission);

        userMissionRepository.save(userMission);

        return MissionResponse.from(userMission);
    }

    // 오늘의 미션 조회
    @Transactional(readOnly = true)
    public MissionResponse getCurrentMission(Integer userId) {

        LocalDate today =
                LocalDate.now(ZoneId.of("Asia/Seoul"));

        UserMission userMission = userMissionRepository
                .findByUserIdAndAssignedDate(
                        userId.longValue(),
                        today
                )
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "오늘 배정된 미션이 없습니다."
                        )
                );

        return MissionResponse.from(userMission);
    }

    // 사용자 미션 진행 기록 조회
    @Transactional(readOnly = true)
    public List<MissionResponse> getMissionProgress(
            Integer userId
    ) {

        return userMissionRepository
                .findAllByUserIdOrderByAssignedDateDescIdDesc(
                        userId.longValue()
                )
                .stream()
                .map(MissionResponse::from)
                .toList();
    }

    // AI 미션 판정 결과 처리
    @Transactional
    public MissionResponse processMissionResult(
            Long missionId,
            MissionResultRequest request
    ) {

        // 1. 요청 데이터 확인
        if (request.userId() == null ||
                request.success() == null) {

            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "userId와 success는 필수입니다."
            );
        }

        Long userId = request.userId().longValue();

        LocalDate today =
                LocalDate.now(ZoneId.of("Asia/Seoul"));

        // 2. 오늘 배정된 미션 조회
        UserMission userMission = userMissionRepository
                .findByUserIdAndAssignedDate(userId, today)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "오늘 배정된 미션이 없습니다."
                        )
                );

        // 3. 요청한 미션이 오늘의 미션인지 확인
        if (!userMission.getMission()
                .getId().equals(missionId)) {

            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "현재 진행 중인 미션이 아닙니다."
            );
        }

        // 4. 이미 완료된 미션인지 확인
        if (userMission.getStatus()
                == MissionStatus.COMPLETED) {

            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "이미 완료된 미션입니다."
            );
        }

        // 5. 미션 실패 시 상태 유지
        if (!request.success()) {
            return MissionResponse.from(userMission);
        }

        // 6. 사용자 캐릭터 조회
        CharacterStatus character = characterRepository
                .findByUserId(request.userId())
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        // 7. 현재 Stage와 미션 Stage 확인
        Integer stage = character.getCurrentStage();

        if (stage == null ||
                !stage.equals(
                        userMission.getMission().getStage()
                )) {

            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "캐릭터 단계와 미션 단계가 다릅니다."
            );
        }

        // 8. 미션 완료 처리
        userMission.complete();

        // 9. Stage 상승
        if (stage < 4) {
            character.setCurrentStage(stage + 1);
        }

        // 10. DB 변경사항 저장
        userMissionRepository.save(userMission);
        characterRepository.save(character);

        return MissionResponse.from(userMission);
    }
}