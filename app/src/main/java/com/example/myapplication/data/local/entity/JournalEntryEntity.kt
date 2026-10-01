package com.example.myapplication.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "journal_entries",
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
data class JournalEntryEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    val flightRecordId: Long,
    val content: String,
    val generatedAt: Long = System.currentTimeMillis(),
    val sourceContext: String = "",
)