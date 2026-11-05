package com.example.myapplication

import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import java.util.concurrent.TimeUnit

// ── 요청/응답 형식 (AI 담당과 확정되면 여기만 수정) ──────────────────────────

data class ChatRequest(val userId: Long, val message: String)

data class GpsRequest(val userId: Long, val distanceMeters: Float)

// 텍스트/사진/GPS 응답을 하나로 처리 (없는 필드는 null)
data class AiResponse(
    val reply: String? = null,
    val missionSuccess: Boolean? = null,
    val crisisDetected: Boolean? = null,
    val reason: String? = null
)

// ── 엔드포인트 (AI 담당에게 받은 주소로 교체) ────────────────────────────────

interface AiApiService {
    @POST("ai/chat")
    suspend fun sendChat(@Body request: ChatRequest): AiResponse

    @Multipart
    @POST("ai/photo")
    suspend fun sendPhoto(
        @Part image: MultipartBody.Part,
        @Part("userId") userId: RequestBody,
        @Part("missionId") missionId: RequestBody
    ): AiResponse

    @POST("ai/gps")
    suspend fun sendGps(@Body request: GpsRequest): AiResponse
}

object AiClient {
    // TODO: AI 서버 주소로 교체 (반드시 맨 끝에 / 붙이기)
    private const val BASE_URL = "https://example.com/"

    private val okHttp = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS) // AI 응답이 느릴 수 있어서 넉넉히
        .build()

    val api: AiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AiApiService::class.java)
    }
}