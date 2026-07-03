package com.example.lddc.domain.settings

import com.example.lddc.data.local.datastore.AppSettings
import com.example.lddc.data.repository.SettingsRepository

class UpdateSettingsUseCase(
    private val settingsRepository: SettingsRepository
) {
    suspend operator fun invoke(settings: AppSettings) {
        settingsRepository.updateSettings(settings)
    }

}
