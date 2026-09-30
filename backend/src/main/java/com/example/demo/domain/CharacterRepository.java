package com.example.demo.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface CharacterRepository
        extends JpaRepository<CharacterStatus, Long> {

    Optional<CharacterStatus> findByUserId(Integer userId);
}