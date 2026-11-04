
package com.example.demo.service;

import com.example.demo.domain.CharacterStatus;
import com.example.demo.domain.CharacterRepository;
import com.example.demo.entity.Emotion;

import lombok.RequiredArgsConstructor;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class CharacterService {

    private final CharacterRepository characterRepository;

    // 1. 캐릭터 상태 조회 (앱 연동용)
    @Transactional(readOnly = true)
    public CharacterStatus getCharacter(Long charId) {
        return characterRepository.findById(charId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );
    }

    // 2. 연료 충전
    @Transactional
    public void chargeFuel(Long charId, int amount) {

        if (amount <= 0) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "충전량은 0보다 커야 합니다."
            );
        }

        CharacterStatus status = characterRepository.findById(charId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        // 연료 최대 100 제한
        int currentFuel = status.getFuelGauge() == null
                ? 0
                : status.getFuelGauge();

        status.setFuelGauge(
                Math.min(100, currentFuel + amount)
        );

        characterRepository.save(status);
    }

    // 3. 친밀도 상승
    @Transactional
    public void updateIntimacy(Long charId, int amount) {

        CharacterStatus status = characterRepository.findById(charId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터 상태를 찾을 수 없습니다."
                        )
                );

        status.addIntimacy(amount);
    }

    // 4. 감정 상태 변경
    @Transactional
    public void updateEmotionStatus(Long charId, String emotionStatus) {

        CharacterStatus character = characterRepository.findById(charId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "캐릭터를 찾을 수 없습니다."
                        )
                );

        Emotion emotion = Emotion.fromString(emotionStatus);

        character.setEmotionStatus(emotion.toJson());

        characterRepository.save(character);
    }
}
