
package com.example.demo.service;

import com.example.demo.dto.ConversationRequest;
import com.example.demo.dto.ConversationResponse;
import com.example.demo.entity.Conversation;
import com.example.demo.repository.ConversationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.domain.PageRequest;
import java.util.List;
import com.example.demo.entity.Emotion;
import java.util.Comparator;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ConversationService {

    private final ConversationRepository conversationRepository;
    private final CryptoService cryptoService;

    @Transactional
    public ConversationResponse save(ConversationRequest request) {

        // 1. 필수 데이터 검증
        if (request.getUserId() == null ||
                request.getSpeaker() == null ||
                request.getMessage() == null ||
                request.getMessage().isBlank()) {

            throw new IllegalArgumentException(
                    "사용자, 발화자, 메시지는 필수입니다."
            );
        }

        // 2. 동일한 대화 중복 저장 방지 (추가)
        if (request.getRequestId() != null &&
                !request.getRequestId().isBlank()) {

            boolean exists = conversationRepository
                    .existsByUserIdAndRequestIdAndSpeaker(
                            request.getUserId(),
                            request.getRequestId(),
                            request.getSpeaker()
                    );

            if (exists) {
                throw new IllegalArgumentException(
                        "이미 저장된 대화 요청입니다."
                );
            }
        }

        // 3. 공통 감정값 검증
        String emotion = null;

        if (request.getEmotion() != null) {
            emotion = Emotion
                    .fromString(request.getEmotion())
                    .toJson();
        }

        // 4. 메시지 AES-GCM 암호화
        String encryptedMessage =
                cryptoService.encrypt(request.getMessage());

        // 5. Conversation 객체 생성
        Conversation conversation = Conversation.builder()
                .userId(request.getUserId())
                .speaker(request.getSpeaker())
                .message(encryptedMessage)
                .emotion(emotion)
                .stage(request.getStage())
                .channel(request.getChannel())
                .requestId(request.getRequestId())
                .build();

        // 6. DB에 저장
        Conversation saved =
                conversationRepository.save(conversation);

        // 7. 응답 반환
        return toResponse(saved);
    }

    // 전체 대화 조회
    public List<ConversationResponse> getConversations(Long userId) {

        return conversationRepository
                .findByUserIdOrderByCreatedAtAsc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    // 최근 N개 대화 조회
    public List<ConversationResponse> getRecentConversations(
            Long userId,
            int limit
    ) {

        List<Conversation> conversations = conversationRepository
                .findByUserIdOrderByCreatedAtDesc(
                        userId,
                        PageRequest.of(0, limit)
                );

        return conversations.stream()
                .sorted(Comparator.comparing(Conversation::getCreatedAt))
                .map(this::toResponse)
                .toList();
    }

    // Conversation → Response DTO 변환
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
                .emotion(conversation.getEmotion())
                .stage(conversation.getStage())
                .channel(conversation.getChannel())
                .requestId(conversation.getRequestId())
                .createdAt(conversation.getCreatedAt())
                .build();
    }
}