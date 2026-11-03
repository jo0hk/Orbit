package com.example.demo.service;

import com.example.demo.domain.CharacterStatus;
import com.example.demo.domain.CharacterRepository;
import com.example.demo.entity.Emotion;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CharacterService {

    @Autowired
    private CharacterRepository characterRepository;

    @Transactional
    public void chargeFuel(Long charId, int amount) {
        CharacterStatus status = characterRepository.findById(charId)
                .orElseThrow(() ->
                        new RuntimeException("캐릭터를 찾을 수 없습니다.")
                );

        System.out.println("연료 충전 중: " + amount);
    }

    @Transactional
    public void updateIntimacy(Long charId, int amount) {
        CharacterStatus status = characterRepository.findById(charId)
                .orElseThrow(() ->
                        new RuntimeException("캐릭터 상태를 찾을 수 없습니다.")
                );

        status.addIntimacy(amount);
    }



    @Transactional
    public void updateEmotionStatus(Long charId, String emotionStatus) {

        CharacterStatus character = characterRepository.findById(charId)
                .orElseThrow(() ->
                        new RuntimeException("캐릭터를 찾을 수 없습니다.")
                );

        Emotion emotion = Emotion.fromString(emotionStatus);

        character.setEmotionStatus(emotion.toJson());

        characterRepository.save(character);
    }
}