package com.example.demo.controller;

import com.example.demo.dto.ConversationRequest;
import com.example.demo.dto.ConversationResponse;
import com.example.demo.service.ConversationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/conversations")
@RequiredArgsConstructor
public class ConversationController {

    private final ConversationService conversationService;

    @PostMapping
    public ResponseEntity<ConversationResponse> save(
            @RequestBody ConversationRequest request) {

        return ResponseEntity.ok(
                conversationService.save(request)
        );
    }

    @GetMapping("/{userId}")
    public ResponseEntity<List<ConversationResponse>> getConversations(
            @PathVariable Long userId) {

        return ResponseEntity.ok(
                conversationService.getConversations(userId)
        );
    }
}