package com.example.myapplication.data.remote.api

import com.example.myapplication.data.remote.dto.ConversationRequestDto
import com.example.myapplication.data.remote.dto.ConversationResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ConversationApi {

    // 대화 저장
    @POST("api/conversations")
    suspend fun saveConversation(
        @Body request: ConversationRequestDto
    ): ConversationResponseDto

    // 사용자별 대화 조회
    @GET("api/conversations/{userId}")
    suspend fun getConversations(
        @Path("userId") userId: Long
    ): List<ConversationResponseDto>
}