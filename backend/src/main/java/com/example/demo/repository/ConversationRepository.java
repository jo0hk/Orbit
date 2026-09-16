package com.example.demo.repository;


import com.example.demo.entity.Conversation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ConversationRepository
        extends JpaRepository<Conversation, Long> {

    List<Conversation> findByUserIdOrderByCreatedAtAsc(Long userId);
}