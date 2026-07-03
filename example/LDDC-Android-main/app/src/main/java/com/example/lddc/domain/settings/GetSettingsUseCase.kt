package com.example.lddc.domain.settings

import com.example.lddc.data.local.datastore.AppSettings
import com.example.lddc.data.repository.SettingsRepository
import kotlinx.coroutines.flow.Flow

class GetSettingsUseCase(
    private val settingsRepository: SettingsRepository
) {
    operator fun invoke(): Flow<AppSettings> {
        return settingsRepository.settings
    }
}
