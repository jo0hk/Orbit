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

        // 2. 공통 감정값 검증
        String emotion = null;

        if (request.getEmotion() != null) {
            emotion = Emotion
                    .fromString(request.getEmotion())
                    .toJson();
        }

        // 3. 메시지 AES-GCM 암호화
        String encryptedMessage =
                cryptoService.encrypt(request.getMessage());

        // 4. Conversation 객체 생성
        Conversation conversation = Conversation.builder()
                .userId(request.getUserId())
                .speaker(request.getSpeaker())
                .message(encryptedMessage)
                .emotion(emotion)
                .stage(request.getStage())
                .channel(request.getChannel())
                .requestId(request.getRequestId())
                .build();

        // 5. DB에 저장
        Conversation saved =
                conversationRepository.save(conversation);

        // 6. 응답 반환
        return toResponse(saved);
    }



    public List<ConversationResponse> getConversations(Long userId) {

        return conversationRepository
                .findByUserIdOrderByCreatedAtAsc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    public List<ConversationResponse> getRecentConversations(Long userId, int limit) {

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