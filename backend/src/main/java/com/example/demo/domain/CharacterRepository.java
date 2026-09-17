package com.example.demo.domain;

import com.example.demo.domain.CharacterStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CharacterRepository extends JpaRepository<CharacterStatus, Long> {
    // 이 한 줄만으로 DB에서 데이터를 넣고, 빼고, 수정하는 모든 기능이 자동으로 생김
}