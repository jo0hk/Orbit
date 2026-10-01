package com.example.myapplication.data.remote

import com.example.myapplication.data.remote.api.ConversationApi
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object OrbitRetrofitClient {

    private const val BASE_URL = "http://서버IP:8080/"

    val conversationApi: ConversationApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ConversationApi::class.java)
    }
}