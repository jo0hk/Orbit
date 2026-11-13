package com.example.myapplication.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.example.myapplication.data.local.dao.*
import com.example.myapplication.data.local.entity.*

@Database(
    entities = [
        FlightRecordEntity::class,
        TrajectoryPointEntity::class,
        MissionChecklistEntity::class,
        JournalEntryEntity::class,
    ],
    version = 1,
    exportSchema = false
)
abstract class OrbitDatabase : RoomDatabase() {

    abstract fun flightRecordDao(): FlightRecordDao
    abstract fun trajectoryPointDao(): TrajectoryPointDao
    abstract fun missionChecklistDao(): MissionChecklistDao
    abstract fun journalEntryDao(): JournalEntryDao

    companion object {
        @Volatile
        private var INSTANCE: OrbitDatabase? = null

        fun getInstance(context: Context): OrbitDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(
                    context.applicationContext,
                    OrbitDatabase::class.java,
                    "orbit_flight_log.db"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}