package com.example.myapplication.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "trajectory_points",
    foreignKeys = [
        ForeignKey(
            entity = FlightRecordEntity::class,
            parentColumns = ["id"],
            childColumns = ["flightRecordId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("flightRecordId")]
)
data class TrajectoryPointEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    val flightRecordId: Long,
    val latitude: Double,
    val longitude: Double,
    val altitude: Double = 0.0,
    val recordedAt: Long = System.currentTimeMillis(),
    val accuracyMeters: Float = 0f,
)