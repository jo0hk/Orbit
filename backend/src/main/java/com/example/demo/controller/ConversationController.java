package com.example.demo.controller;

import com.example.demo.dto.ConversationRequest;
import com.example.demo.dto.ConversationResponse;
import com.example.demo.service.ConversationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
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
    @GetMapping("/{userId}/recent")
    public ResponseEntity<List<ConversationResponse>> getRecentConversations(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "10") int limit) {

        return ResponseEntity.ok(
                conversationService.getRecentConversations(userId, limit)
        );
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<String> handleIllegalArgumentException(
            IllegalArgumentException e) {

        return ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(e.getMessage());
    }
}