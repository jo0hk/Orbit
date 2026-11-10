package com.example.myapplication

import com.google.gson.annotations.SerializedName
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

// ── 텍스트 교신 요청/응답 ─────────────────────────────────────────────────────

data class ChatRequest(
    @SerializedName("user_id") val userId: Long,
    @SerializedName("text") val text: String,
    @SerializedName("request_id") val requestId: String = java.util.UUID.randomUUID().toString()
)

// 텍스트/사진 공통 응답 (없는 필드는 null)
data class AiResponse(
    @SerializedName("speech") val speech: String? = null,
    @SerializedName("mission_result") val missionResult: String? = null, // success / retry / deferred / none
    @SerializedName("high_risk_detected") val highRiskDetected: Boolean? = null,
    @SerializedName("emotion") val emotion: String? = null,
    @SerializedName("next_step") val nextStep: String? = null            // 사진 전용: "alighting" 또는 null
) {
    val missionSuccess: Boolean get() = missionResult == "success"
}

// ── API 정의 ─────────────────────────────────────────────────────────────────

interface AiApiService {

    // 텍스트 교신 (1단계 기분 텍스트 미션 포함)
    @POST("api/v1/interact/text")
    suspend fun sendChat(@Body request: ChatRequest): AiResponse

    // 사진 판정 (3단계 랜드마크 / 4단계 승차·하차)
    // 3단계: image, user_id, captured_at 만 보냄 (step, lat, lng 는 null)
    // 4단계: step("boarding"/"alighting"), lat, lng 도 함께 보냄
    @Multipart
    @POST("api/v1/interact/photo")
    suspend fun sendPhoto(
        @Part image: MultipartBody.Part,
        @Part("user_id") userId: RequestBody,
        @Part("captured_at") capturedAt: RequestBody,
        @Part("request_id") requestId: RequestBody,
        @Part("step") step: RequestBody? = null,
        @Part("lat") lat: RequestBody? = null,
        @Part("lng") lng: RequestBody? = null
    ): AiResponse
}

object AiClient {
    // TODO: AI 담당이 준 터널 주소로 교체 (반드시 맨 끝에 / 붙이기)
    private const val BASE_URL = "https://example.com/"

    private val okHttp = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS) // 응답이 3~7초 걸려서 넉넉히
        .writeTimeout(30, TimeUnit.SECONDS)
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