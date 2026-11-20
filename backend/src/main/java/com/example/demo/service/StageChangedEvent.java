package com.example.demo.service;

public record StageChangedEvent(
        Long userId,
        Integer stage
) {
}