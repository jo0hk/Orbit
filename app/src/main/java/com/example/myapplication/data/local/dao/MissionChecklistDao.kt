package com.example.myapplication.data.local.dao

import androidx.room.*
import com.example.myapplication.data.local.entity.MissionChecklistEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MissionChecklistDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(items: List<MissionChecklistEntity>)

    @Query("""
        UPDATE mission_checklists 
        SET isCompleted = :isCompleted, 
            completedAt = :completedAt 
        WHERE id = :id
    """)
    suspend fun updateCheckState(id: Long, isCompleted: Boolean, completedAt: Long?)

    @Query("""
        SELECT * FROM mission_checklists 
        WHERE flightRecordId = :flightRecordId 
        ORDER BY `order` ASC
    """)
    fun getChecklistByRecord(flightRecordId: Long): Flow<List<MissionChecklistEntity>>
}