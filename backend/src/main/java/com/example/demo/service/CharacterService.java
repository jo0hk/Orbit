package com.example.demo.service;

import com.example.demo.domain.CharacterStatus;
import com.example.demo.domain.CharacterRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CharacterService {

    @Autowired
    private CharacterRepository characterRepository;

    // 1. 연료 충전 메서드
    @Transactional
    public void chargeFuel(Long charId, int amount) {
        CharacterStatus status = characterRepository.findById(charId)
                .orElseThrow(() -> new RuntimeException("캐릭터를 찾을 수 없습니다."));

        System.out.println("연료 충전 중: " + amount);
        // 여기에 fuel 업데이트 로직이 필요할 수 있습니다.
    } // <--- chargeFuel 메서드가 여기서 끝납니다.

    // 2. 친밀도 업데이트 메서드 (chargeFuel 밖으로 꺼냈습니다!)
    @Transactional
    public void updateIntimacy(Long charId, int amount) {
        CharacterStatus status = characterRepository.findById(charId)
                .orElseThrow(() -> new RuntimeException("캐릭터 상태를 찾을 수 없습니다."));

        status.addIntimacy(amount);
        // @Transactional이 붙어있어서 자동으로 DB에 반영됩니다.
    }

    @Transactional
    public void increaseStage(Long charId) {
        CharacterStatus character = characterRepository.findById(charId)
                .orElseThrow(() -> new RuntimeException("캐릭터를 찾을 수 없습니다."));

        character.setCurrentStage(character.getCurrentStage() + 1);

        characterRepository.save(character);
    }

    @Transactional
    public void updateEmotionStatus(Long charId, String emotionStatus) {
        CharacterStatus character = characterRepository.findById(charId)
                .orElseThrow(() -> new RuntimeException("캐릭터를 찾을 수 없습니다."));

        character.setEmotionStatus(emotionStatus);

        characterRepository.save(character);
    }
}