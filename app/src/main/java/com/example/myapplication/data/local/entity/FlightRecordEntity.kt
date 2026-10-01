package com.example.myapplication.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "flight_records")
data class FlightRecordEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    val startedAt: Long = System.currentTimeMillis(),
    val endedAt: Long? = null,

    val totalDistanceMeters: Float = 0f,
    val durationSeconds: Long = 0L,

    val missionTitle: String = "UNKNOWN SECTOR",
)