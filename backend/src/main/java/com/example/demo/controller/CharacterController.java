package com.example.demo.controller;

import com.example.demo.service.CharacterService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/character")
public class CharacterController {

    @Autowired
    private CharacterService characterService;

    // 1. 연료를 충전하는 주소
    @GetMapping("/{id}/charge")
    public String chargeFuel(@PathVariable Long id, @RequestParam int amount) {
        characterService.chargeFuel(id, amount);
        return "연료가 " + amount + "% 충전되었습니다! 치칙-";
    }

    // 2. 친밀도 상승 API
    @PostMapping("/{id}/intimacy")
    public String chargeIntimacy(@PathVariable Long id, @RequestParam int amount) {
        characterService.updateIntimacy(id, amount);
        return "친밀도가 " + amount + "만큼 상승했습니다! 치이익-";
    }
}