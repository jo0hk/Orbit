
package com.example.demo.service;

import com.example.demo.domain.CharacterRepository;
import com.example.demo.domain.CharacterStatus;
import com.example.demo.dto.MissionResponse;
import com.example.demo.dto.MissionResultRequest;
import com.example.demo.entity.Mission;
import com.example.demo.entity.UserMission;
import com.example.demo.entity.MissionStatus;
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
    // 오늘의 미션 배정
    @Transactional
    public MissionResponse assignTodayMission(Long userId) {

        LocalDate today =
                LocalDate.now(ZoneId.of("Asia/Seoul"));

        // 1. 오늘 이미 배정된 미션이 있으면 그대로 반환
        var existing = userMissionRepository
                .findByUserIdAndAssignedDate(userId, today);

        if (existing.isPresent()) {
            return MissionResponse.from(existing.get());
        }

        // 2. 사용자 캐릭터 조회
        CharacterStatus character = characterRepository
                .findByUserId(userId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        // 3. 현재 캐릭터 단계
        Integer stage = character.getCurrentStage();

        if (stage == null || stage < 1 || stage > 4) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "유효하지 않은 캐릭터 단계입니다."
            );
        }

        // 4. 4단계에서는 연료 100% 이상이면 미션 배정 중단
        if (stage == 4) {

            Number fuelGauge = character.getFuelGauge();

            if (fuelGauge == null) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "연료 정보가 없습니다."
                );
            }

            if (fuelGauge.doubleValue() >= 100) {
                return null;
            }
        }

        // 5. 현재 단계 미션 조회
        Mission mission = missionRepository
                .findByStage(stage)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "해당 단계의 미션이 없습니다."
                        )
                );

        // 6. 오늘의 미션 생성
        UserMission userMission =
                new UserMission(userId, mission);

        userMissionRepository.save(userMission);

        return MissionResponse.from(userMission);
    }

    // 오늘의 미션 조회
    // 오늘의 미션 조회
    @Transactional(readOnly = true)
    public MissionResponse getCurrentMission(Long userId) {

        LocalDate today =
                LocalDate.now(ZoneId.of("Asia/Seoul"));

        return userMissionRepository
                .findByUserIdAndAssignedDate(userId, today)
                .map(MissionResponse::from)
                .orElse(null);
    }

    // 사용자 미션 진행 기록 조회
    @Transactional(readOnly = true)
    public List<MissionResponse> getMissionProgress(
            Long userId
    ) {

        return userMissionRepository
                .findAllByUserIdOrderByAssignedDateDescIdDesc(
                        userId
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

        Long userId = request.userId();

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
        // AI는 SUCCESS일 때만 POST하므로 일반 연동에서는 사용하지 않음
        if (!request.success()) {
            return MissionResponse.from(userMission);
        }

        // 6. 사용자 캐릭터 조회
        CharacterStatus character = characterRepository
                .findByUserId(userId)
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

// 9. 캐릭터 단계 상승
        if (stage < 4) {
            character.setCurrentStage(stage + 1);
        }

// 10. 미션 성공 연료 보상
        character.addFuel(10);

// 11. DB 저장
        userMissionRepository.save(userMission);
        characterRepository.save(character);



        return MissionResponse.from(userMission);
    }
}
