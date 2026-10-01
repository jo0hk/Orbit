package com.example.myapplication.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "mission_checklists",
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
data class MissionChecklistEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    val flightRecordId: Long,
    val order: Int,
    val content: String,
    val isCompleted: Boolean = false,
    val completedAt: Long? = null,
)