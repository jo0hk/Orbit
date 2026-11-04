
package com.example.demo.controller;

import com.example.demo.domain.CharacterStatus;
import com.example.demo.service.CharacterService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/character")
@RequiredArgsConstructor
public class CharacterController {

    private final CharacterService characterService;

    // 1. 캐릭터 상태 조회 API (앱 연동용)
    @GetMapping("/{id}")
    public CharacterStatus getCharacter(@PathVariable Long id) {
        return characterService.getCharacter(id);
    }

    // 2. 연료 충전 API
    @PostMapping("/{id}/charge")
    public String chargeFuel(
            @PathVariable Long id,
            @RequestParam int amount
    ) {
        characterService.chargeFuel(id, amount);
        return "연료가 " + amount + "% 충전되었습니다! 치칙-";
    }

    // 3. 친밀도 상승 API
    @PostMapping("/{id}/intimacy")
    public String chargeIntimacy(
            @PathVariable Long id,
            @RequestParam int amount
    ) {
        characterService.updateIntimacy(id, amount);
        return "친밀도가 " + amount + "만큼 상승했습니다! 치이익-";
    }
}
