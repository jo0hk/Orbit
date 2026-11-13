package com.example.myapplication.data.local.dao

import androidx.room.*
import com.example.myapplication.data.local.entity.JournalEntryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface JournalEntryDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entry: JournalEntryEntity): Long

    @Query("""
        SELECT * FROM journal_entries 
        WHERE flightRecordId = :flightRecordId 
        ORDER BY generatedAt DESC
    """)
    fun getEntriesByRecord(flightRecordId: Long): Flow<List<JournalEntryEntity>>

    @Query("SELECT * FROM journal_entries ORDER BY generatedAt DESC")
    fun getAllEntries(): Flow<List<JournalEntryEntity>>
}