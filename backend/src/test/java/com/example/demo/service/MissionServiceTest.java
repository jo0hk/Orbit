
package com.example.demo.service;

import com.example.demo.domain.CharacterRepository;
import com.example.demo.domain.CharacterStatus;
import com.example.demo.dto.MissionResponse;
import com.example.demo.dto.MissionResultRequest;
import com.example.demo.entity.Mission;
import com.example.demo.entity.MissionStatus;
import com.example.demo.entity.MissionType;
import com.example.demo.entity.UserMission;
import com.example.demo.repository.MissionRepository;
import com.example.demo.repository.UserMissionRepository;

import org.springframework.context.ApplicationEventPublisher;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MissionServiceTest {

    @Mock
    private MissionRepository missionRepository;

    @Mock
    private UserMissionRepository userMissionRepository;

    @Mock
    private CharacterRepository characterRepository;

    @Mock
    private ApplicationEventPublisher eventPublisher;

    private static final Long USER_ID = 1L;
    private static final Long MISSION_ID = 4L;

    private static final ZoneId ZONE =
            ZoneId.of("Asia/Seoul");

    // 테스트 날짜를 고정
    private Clock createClock(LocalDate date) {
        return Clock.fixed(
                date.atTime(12, 0)
                        .atZone(ZONE)
                        .toInstant(),
                ZONE
        );
    }

    // 테스트용 MissionService 생성
    private MissionService createService(LocalDate date) {
        return new MissionService(
                missionRepository,
                userMissionRepository,
                characterRepository,
                createClock(date),
                eventPublisher
        );
    }

    // 실제 DB를 사용하지 않는 4단계 미션
    private Mission createMission() {

        Mission mission = new Mission(
                4,
                "대중교통 이용 인증",
                "대중교통을 이용하고 사진으로 인증하기",
                MissionType.TRANSIT
        );

        ReflectionTestUtils.setField(
                mission, "id", MISSION_ID
        );

        return mission;
    }

    // 테스트용 캐릭터 생성
    private CharacterStatus createCharacter(int fuel) {

        CharacterStatus character = new CharacterStatus();

        character.setUserId(USER_ID);
        character.setCurrentStage(4);
        character.setFuelGauge(fuel);

        return character;
    }

    // ==========================================
    // TEST 1. Stage 4 미션 성공 연료 보상
    // ==========================================
    @ParameterizedTest
    @CsvSource({
            "65, 75",
            "75, 85",
            "85, 95",
            "95, 100"
    })
    void stage4FuelRewardTest(
            int beforeFuel,
            int expectedFuel
    ) {

        LocalDate today = LocalDate.of(2026, 11, 19);

        CharacterStatus character =
                createCharacter(beforeFuel);

        Mission mission = createMission();

        UserMission userMission = new UserMission(
                USER_ID,
                mission,
                today
        );

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, today))
                .thenReturn(Optional.of(userMission));

        when(characterRepository.findByUserId(USER_ID))
                .thenReturn(Optional.of(character));

        MissionService service = createService(today);

        MissionResponse response =
                service.processMissionResult(
                        MISSION_ID,
                        new MissionResultRequest(USER_ID, true)
                );

        // 연료 증가 확인
        assertEquals(
                expectedFuel,
                character.getFuelGauge()
        );

        // Stage 4 유지 확인
        assertEquals(4, character.getCurrentStage());

        // 미션 완료 확인
        assertEquals(
                MissionStatus.COMPLETED,
                response.getStatus()
        );

        // 저장 메서드 호출 확인
        verify(userMissionRepository).save(userMission);
        verify(characterRepository).save(character);
    }

    // ==========================================
    // TEST 2. 연료 100%이면 배정 중단
    // ==========================================
    @Test
    void fuel100StopsAssignment() {

        LocalDate today = LocalDate.of(2026, 11, 23);

        CharacterStatus character = createCharacter(100);

        when(characterRepository.findByUserId(USER_ID))
                .thenReturn(Optional.of(character));

        MissionService service = createService(today);

        MissionResponse response =
                service.assignTodayMission(USER_ID);

        assertNull(response);

        verifyNoInteractions(missionRepository);

        verify(userMissionRepository, never())
                .save(any(UserMission.class));
    }

    // ==========================================
    // TEST 3. 연료가 100 미만이면 배정
    // ==========================================
    @Test
    void fuelBelow100AssignsMission() {

        LocalDate today = LocalDate.of(2026, 11, 19);

        CharacterStatus character = createCharacter(65);
        Mission mission = createMission();

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, today))
                .thenReturn(Optional.empty());

        when(characterRepository.findByUserId(USER_ID))
                .thenReturn(Optional.of(character));

        when(missionRepository.findByStage(4))
                .thenReturn(Optional.of(mission));

        MissionService service = createService(today);

        MissionResponse response =
                service.assignTodayMission(USER_ID);

        assertNotNull(response);

        assertEquals(4, response.getStage());

        assertEquals(
                MissionStatus.IN_PROGRESS,
                response.getStatus()
        );

        assertEquals(
                today,
                response.getAssignedDate()
        );

        verify(userMissionRepository)
                .save(any(UserMission.class));
    }

    // ==========================================
    // TEST 4. 날짜가 바뀌면 새 미션 배정
    // ==========================================
    @Test
    void nextDayAssignsNewMission() {

        LocalDate day1 = LocalDate.of(2026, 11, 19);
        LocalDate day2 = LocalDate.of(2026, 11, 20);

        CharacterStatus character = createCharacter(75);
        Mission mission = createMission();

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, day1))
                .thenReturn(Optional.empty());

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, day2))
                .thenReturn(Optional.empty());

        when(characterRepository.findByUserId(USER_ID))
                .thenReturn(Optional.of(character));

        when(missionRepository.findByStage(4))
                .thenReturn(Optional.of(mission));

        MissionService service1 = createService(day1);
        MissionService service2 = createService(day2);

        service1.assignTodayMission(USER_ID);
        service2.assignTodayMission(USER_ID);

        ArgumentCaptor<UserMission> captor =
                ArgumentCaptor.forClass(UserMission.class);

        verify(userMissionRepository, times(2))
                .save(captor.capture());

        assertEquals(
                day1,
                captor.getAllValues().get(0).getAssignedDate()
        );

        assertEquals(
                day2,
                captor.getAllValues().get(1).getAssignedDate()
        );
    }

    // ==========================================
    // TEST 5. 같은 날 기존 미션 반환
    // ==========================================
    @Test
    void sameDayReturnsExistingMission() {

        LocalDate today = LocalDate.of(2026, 11, 19);

        Mission mission = createMission();

        UserMission existing = new UserMission(
                USER_ID,
                mission,
                today
        );

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, today))
                .thenReturn(Optional.of(existing));

        MissionService service = createService(today);

        MissionResponse response =
                service.assignTodayMission(USER_ID);

        assertNotNull(response);

        assertEquals(
                MISSION_ID,
                response.getMissionId()
        );

        assertEquals(
                MissionStatus.IN_PROGRESS,
                response.getStatus()
        );

        verify(userMissionRepository, never())
                .save(any(UserMission.class));

        verifyNoInteractions(missionRepository);
    }

    // ==========================================
    // TEST 6. 완료된 미션 중복 보상 방지
    // ==========================================
    @Test
    void duplicateRewardIsBlocked() {

        LocalDate today = LocalDate.of(2026, 11, 19);

        Mission mission = createMission();

        UserMission userMission = new UserMission(
                USER_ID,
                mission,
                today
        );

        ReflectionTestUtils.setField(
                userMission,
                "status",
                MissionStatus.COMPLETED
        );

        MissionService service = createService(today);

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, today))
                .thenReturn(Optional.of(userMission));

        ResponseStatusException exception =
                assertThrows(
                        ResponseStatusException.class,
                        () -> service.processMissionResult(
                                MISSION_ID,
                                new MissionResultRequest(
                                        USER_ID, true
                                )
                        )
                );

        assertEquals(
                HttpStatus.CONFLICT,
                exception.getStatusCode()
        );

        verifyNoInteractions(characterRepository);

        verify(userMissionRepository, never())
                .save(any(UserMission.class));
    }

    // ==========================================
    // TEST 7. Stage 1~3 미션 성공 시 이벤트 발행
    // ==========================================
    @ParameterizedTest
    @CsvSource({
            "1, 2",
            "2, 3",
            "3, 4"
    })
    void missionSuccessPublishesStageChangedEvent(
            int beforeStage,
            int expectedStage
    ) {

        LocalDate today = LocalDate.of(2026, 11, 20);

        // 현재 단계에 해당하는 미션 생성
        Mission mission = new Mission(
                beforeStage,
                "테스트 미션",
                "Stage 상승 검증",
                MissionType.TRANSIT
        );

        ReflectionTestUtils.setField(
                mission, "id", MISSION_ID
        );

        UserMission userMission = new UserMission(
                USER_ID,
                mission,
                today
        );

        // 캐릭터의 기존 Stage 지정
        CharacterStatus character = createCharacter(65);
        character.setCurrentStage(beforeStage);

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, today))
                .thenReturn(Optional.of(userMission));

        when(characterRepository.findByUserId(USER_ID))
                .thenReturn(Optional.of(character));

        MissionService service = createService(today);

        // 미션 성공 처리
        MissionResponse response =
                service.processMissionResult(
                        MISSION_ID,
                        new MissionResultRequest(USER_ID, true)
                );

        // 1. 미션 완료 확인
        assertEquals(
                MissionStatus.COMPLETED,
                response.getStatus()
        );

        // 2. 캐릭터 Stage 상승 확인
        assertEquals(
                expectedStage,
                character.getCurrentStage()
        );

        // 3. 연료 +10 확인
        assertEquals(75, character.getFuelGauge());

        // 4. StageChangedEvent 발행 확인
        ArgumentCaptor<StageChangedEvent> captor =
                ArgumentCaptor.forClass(StageChangedEvent.class);

        verify(eventPublisher, times(1))
                .publishEvent(captor.capture());

        StageChangedEvent event = captor.getValue();

        // 5. 발행된 이벤트 값 확인
        assertEquals(USER_ID, event.userId());
        assertEquals(expectedStage, event.stage());

        // 6. DB 저장 메서드 호출 확인
        verify(userMissionRepository).save(userMission);
        verify(characterRepository).save(character);
    }

    // ==========================================
    // TEST 8. Stage 4 미션 성공 시 이벤트 미발행
    // ==========================================
    @Test
    void stage4DoesNotPublishStageChangedEvent() {

        LocalDate today = LocalDate.of(2026, 11, 20);

        Mission mission = createMission();

        UserMission userMission = new UserMission(
                USER_ID,
                mission,
                today
        );

        CharacterStatus character = createCharacter(75);

        when(userMissionRepository
                .findByUserIdAndAssignedDate(USER_ID, today))
                .thenReturn(Optional.of(userMission));

        when(characterRepository.findByUserId(USER_ID))
                .thenReturn(Optional.of(character));

        MissionService service = createService(today);

        // Stage 4 미션 성공 처리
        MissionResponse response =
                service.processMissionResult(
                        MISSION_ID,
                        new MissionResultRequest(USER_ID, true)
                );

        // 1. 미션 완료 확인
        assertEquals(
                MissionStatus.COMPLETED,
                response.getStatus()
        );

        // 2. Stage 4 유지
        assertEquals(4, character.getCurrentStage());

        // 3. 연료 +10 확인
        assertEquals(85, character.getFuelGauge());

        // 4. Stage 변경 이벤트 미발행 확인
        verify(eventPublisher, never())
                .publishEvent(any(StageChangedEvent.class));

        // 5. DB 저장 메서드 호출 확인
        verify(userMissionRepository).save(userMission);
        verify(characterRepository).save(character);
    }
}
