package com.example.myapplication.data.remote.dto

data class ConversationRequestDto(
    val userId: Long,
    val speaker: String,  // "USER" 또는 "ORBIT"
    val message: String
)