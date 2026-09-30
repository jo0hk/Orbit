package com.example.demo.repository;

import com.example.demo.entity.Conversation;
import com.example.demo.entity.Speaker;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ConversationRepository
        extends JpaRepository<Conversation, Long> {

    List<Conversation> findByUserIdOrderByCreatedAtAsc(Long userId);

    boolean existsByRequestIdAndSpeaker(String requestId, Speaker speaker);

    List<Conversation> findTop10ByUserIdOrderByCreatedAtDesc(Long userId);

    List<Conversation> findByUserIdOrderByCreatedAtDesc(
            Long userId,
            org.springframework.data.domain.Pageable pageable
    );
}