package com.example.myapplication.data.local.dao

import androidx.room.*
import com.example.myapplication.data.local.entity.FlightRecordEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface FlightRecordDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(record: FlightRecordEntity): Long

    @Update
    suspend fun update(record: FlightRecordEntity)

    @Query("SELECT * FROM flight_records ORDER BY startedAt DESC")
    fun getAllRecords(): Flow<List<FlightRecordEntity>>

    @Query("SELECT * FROM flight_records WHERE id = :id")
    suspend fun getById(id: Long): FlightRecordEntity?

    @Query("SELECT * FROM flight_records WHERE endedAt IS NULL LIMIT 1")
    suspend fun getActiveRecord(): FlightRecordEntity?

    @Delete
    suspend fun delete(record: FlightRecordEntity)
}