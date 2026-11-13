package com.example.myapplication.data.remote.dto

data class ConversationResponseDto(
    val id: Long,
    val userId: Long,
    val speaker: String,
    val message: String,
    val createdAt: String
)