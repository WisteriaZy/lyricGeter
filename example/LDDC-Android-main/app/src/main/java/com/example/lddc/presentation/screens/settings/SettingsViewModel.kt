package com.example.lddc.presentation.screens.settings

import androidx.lifecycle.viewModelScope
import com.example.lddc.common.models.enums.LyricsFormat
import com.example.lddc.common.models.enums.Source
import com.example.lddc.domain.settings.GetSettingsUseCase
import com.example.lddc.domain.settings.UpdateSettingsUseCase
import com.example.lddc.presentation.viewmodel.BaseViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val getSettingsUseCase: GetSettingsUseCase,
    private val updateSettingsUseCase: UpdateSettingsUseCase
) : BaseViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        loadSettings()
    }

    private fun loadSettings() {
        viewModelScope.launch {
            getSettingsUseCase().collectLatest { settings ->
                _uiState.update {
                    it.copy(
                        enabledSources = settings.enabledSources,
                        preferredFormat = settings.lyricsFormat,
                        autoSave = settings.saveLyricsFile,
                        embedLyrics = settings.embedLyrics,
                        savePath = settings.defaultSavePath,
                        showTranslation = settings.autoTranslate,
                        showRomanization = settings.showRomaji,
                        isLoading = false
                    )
                }
            }
        }
    }

    fun toggleSource(source: Source, enabled: Boolean) {
        viewModelScope.launch {
            val currentSources = _uiState.value.enabledSources.toMutableList()
            if (enabled) {
                if (source !in currentSources) currentSources.add(source)
            } else {
                currentSources.remove(source)
            }
            _uiState.update { it.copy(enabledSources = currentSources) }
            // 获取当前设置并更新
            val currentSettings = getSettingsUseCase().first()
            updateSettingsUseCase(currentSettings.copy(enabledSources = currentSources))
        }
    }

    fun setPreferredFormat(format: LyricsFormat) {
        viewModelScope.launch {
            _uiState.update { it.copy(preferredFormat = format) }
            val currentSettings = getSettingsUseCase().first()
            updateSettingsUseCase(currentSettings.copy(lyricsFormat = format))
        }
    }

    fun setAutoSave(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(autoSave = enabled) }
            val currentSettings = getSettingsUseCase().first()
            updateSettingsUseCase(currentSettings.copy(saveLyricsFile = enabled))
        }
    }

    fun setEmbedLyrics(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(embedLyrics = enabled) }
            val currentSettings = getSettingsUseCase().first()
            updateSettingsUseCase(currentSettings.copy(embedLyrics = enabled))
        }
    }

    fun setShowTranslation(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(showTranslation = enabled) }
            val currentSettings = getSettingsUseCase().first()
            updateSettingsUseCase(currentSettings.copy(autoTranslate = enabled))
        }
    }

    fun setShowRomanization(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(showRomanization = enabled) }
            val currentSettings = getSettingsUseCase().first()
            updateSettingsUseCase(currentSettings.copy(showRomaji = enabled))
        }
    }

    data class SettingsUiState(
        val enabledSources: List<Source> = listOf(Source.MULTI, Source.NE, Source.QM, Source.KG),
        val preferredFormat: LyricsFormat = LyricsFormat.LINEBYLINELRC,
        val autoSave: Boolean = false,
        val embedLyrics: Boolean = false,
        val savePath: String? = null,
        val showTranslation: Boolean = false,
        val showRomanization: Boolean = false,
        val isLoading: Boolean = true
    )
}
