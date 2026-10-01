package com.example.myapplication.data.local.dao

import androidx.room.*
import com.example.myapplication.data.local.entity.TrajectoryPointEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TrajectoryPointDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(point: TrajectoryPointEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(points: List<TrajectoryPointEntity>)

    @Query("""
        SELECT * FROM trajectory_points 
        WHERE flightRecordId = :flightRecordId 
        ORDER BY recordedAt ASC
    """)
    fun getPointsByRecord(flightRecordId: Long): Flow<List<TrajectoryPointEntity>>

    @Query("""
        SELECT * FROM trajectory_points 
        WHERE flightRecordId = :flightRecordId 
        ORDER BY recordedAt ASC
    """)
    suspend fun getPointsByRecordOnce(flightRecordId: Long): List<TrajectoryPointEntity>

    @Query("DELETE FROM trajectory_points WHERE flightRecordId = :flightRecordId")
    suspend fun deleteByRecord(flightRecordId: Long)
}