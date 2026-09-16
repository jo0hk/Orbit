package com.example.demo.service;
import com.example.demo.dto.ConversationRequest;
import com.example.demo.dto.ConversationResponse;
import com.example.demo.entity.Conversation;
import com.example.demo.repository.ConversationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ConversationService {

    private final ConversationRepository conversationRepository;
    private final CryptoService cryptoService;

    @Transactional
    public ConversationResponse save(ConversationRequest request) {

        String encryptedMessage =
                cryptoService.encrypt(request.getMessage());

        Conversation conversation = Conversation.builder()
                .userId(request.getUserId())
                .speaker(request.getSpeaker())
                .message(encryptedMessage)
                .build();

        Conversation saved =
                conversationRepository.save(conversation);

        return toResponse(saved);
    }

    public List<ConversationResponse> getConversations(Long userId) {

        return conversationRepository
                .findByUserIdOrderByCreatedAtAsc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    private ConversationResponse toResponse(Conversation conversation) {

        return ConversationResponse.builder()
                .id(conversation.getId())
                .userId(conversation.getUserId())
                .speaker(conversation.getSpeaker())
                .message(
                        cryptoService.decrypt(
                                conversation.getMessage()
                        )
                )
                .createdAt(conversation.getCreatedAt())
                .build();
    }
}