package com.example.myapplication.data.repository

import com.example.myapplication.data.local.dao.*
import com.example.myapplication.data.local.entity.*
import kotlinx.coroutines.flow.Flow

class OrbitRepository(
    private val flightRecordDao: FlightRecordDao,
    private val trajectoryPointDao: TrajectoryPointDao,
    private val checklistDao: MissionChecklistDao,
    private val journalEntryDao: JournalEntryDao,
) {
    suspend fun startNewFlight(title: String): Long {
        val record = FlightRecordEntity(missionTitle = title)
        return flightRecordDao.insert(record)
    }

    suspend fun endFlight(record: FlightRecordEntity, distanceMeters: Float, durationSec: Long) {
        flightRecordDao.update(
            record.copy(
                endedAt = System.currentTimeMillis(),
                totalDistanceMeters = distanceMeters,
                durationSeconds = durationSec,
            )
        )
    }

    fun getAllFlights(): Flow<List<FlightRecordEntity>> =
        flightRecordDao.getAllRecords()

    suspend fun getActiveFlightOrNull(): FlightRecordEntity? =
        flightRecordDao.getActiveRecord()

    suspend fun saveTrajectoryPoint(flightId: Long, lat: Double, lng: Double, accuracy: Float) {
        trajectoryPointDao.insert(
            TrajectoryPointEntity(
                flightRecordId = flightId,
                latitude = lat,
                longitude = lng,
                accuracyMeters = accuracy,
            )
        )
    }

    fun getTrajectory(flightId: Long): Flow<List<TrajectoryPointEntity>> =
        trajectoryPointDao.getPointsByRecord(flightId)

    suspend fun initChecklist(flightId: Long, items: List<String>) {
        val entities = items.mapIndexed { index, content ->
            MissionChecklistEntity(
                flightRecordId = flightId,
                order = index,
                content = content,
            )
        }
        checklistDao.insertAll(entities)
    }

    suspend fun toggleCheckItem(id: Long, isCompleted: Boolean) {
        checklistDao.updateCheckState(
            id = id,
            isCompleted = isCompleted,
            completedAt = if (isCompleted) System.currentTimeMillis() else null,
        )
    }

    fun getChecklist(flightId: Long): Flow<List<MissionChecklistEntity>> =
        checklistDao.getChecklistByRecord(flightId)

    suspend fun saveJournalEntry(flightId: Long, content: String, context: String = "") {
        journalEntryDao.insert(
            JournalEntryEntity(
                flightRecordId = flightId,
                content = content,
                sourceContext = context,
            )
        )
    }

    fun getAllJournalEntries(): Flow<List<JournalEntryEntity>> =
        journalEntryDao.getAllEntries()

    fun getJournalEntriesByFlight(flightId: Long): Flow<List<JournalEntryEntity>> =
        journalEntryDao.getEntriesByRecord(flightId)
}