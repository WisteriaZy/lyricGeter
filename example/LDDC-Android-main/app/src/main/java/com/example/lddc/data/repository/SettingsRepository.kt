package com.example.lddc.data.repository

import com.example.lddc.data.local.datastore.AppSettings
import com.example.lddc.data.local.datastore.SettingsDataStore
import kotlinx.coroutines.flow.Flow

class SettingsRepository(
    private val settingsDataStore: SettingsDataStore
) {

    val settings: Flow<AppSettings> = settingsDataStore.settings

    suspend fun updateSettings(settings: AppSettings) {
        settingsDataStore.updateSettings(settings)
    }

    suspend fun updateDefaultSavePath(path: String) {
        settingsDataStore.updateDefaultSavePath(path)
    }

}
