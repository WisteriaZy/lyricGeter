package com.example.lddc.di

import android.content.Context
import com.example.lddc.core.api.LyricsApiManager
import com.example.lddc.data.local.database.LDDCDatabase
import com.example.lddc.data.local.datastore.SettingsDataStore
import com.example.lddc.data.repository.LyricsRepository
import com.example.lddc.data.repository.SearchHistoryRepository
import com.example.lddc.data.repository.SettingsRepository
import com.example.lddc.domain.convert.ConvertLyricsUseCase
import com.example.lddc.domain.search.ClearSearchHistoryUseCase
import com.example.lddc.domain.search.GetLyricsUseCase
import com.example.lddc.domain.search.GetSearchHistoryUseCase
import com.example.lddc.domain.search.SearchSongsUseCase
import com.example.lddc.domain.settings.GetSettingsUseCase
import com.example.lddc.domain.settings.UpdateSettingsUseCase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideLyricsApiManager(): LyricsApiManager {
        return LyricsApiManager()
    }

    @Provides
    @Singleton
    fun provideLDDCDatabase(@ApplicationContext context: Context): LDDCDatabase {
        return LDDCDatabase.getDatabase(context)
    }

    @Provides
    @Singleton
    fun provideSettingsDataStore(@ApplicationContext context: Context): SettingsDataStore {
        return SettingsDataStore(context)
    }

    @Provides
    @Singleton
    fun provideLyricsRepository(
        apiManager: LyricsApiManager,
        database: LDDCDatabase
    ): LyricsRepository {
        return LyricsRepository(
            apiManager = apiManager,
            lyricsCacheDao = database.lyricsCacheDao()
        )
    }

    @Provides
    @Singleton
    fun provideSearchHistoryRepository(
        database: LDDCDatabase
    ): SearchHistoryRepository {
        return SearchHistoryRepository(
            searchHistoryDao = database.searchHistoryDao()
        )
    }

    @Provides
    @Singleton
    fun provideSettingsRepository(
        settingsDataStore: SettingsDataStore
    ): SettingsRepository {
        return SettingsRepository(settingsDataStore)
    }

    // UseCases
    @Provides
    @Singleton
    fun provideSearchSongsUseCase(
        lyricsRepository: LyricsRepository,
        searchHistoryRepository: SearchHistoryRepository
    ): SearchSongsUseCase {
        return SearchSongsUseCase(lyricsRepository, searchHistoryRepository)
    }

    @Provides
    @Singleton
    fun provideGetLyricsUseCase(
        lyricsRepository: LyricsRepository
    ): GetLyricsUseCase {
        return GetLyricsUseCase(lyricsRepository)
    }

    @Provides
    @Singleton
    fun provideGetSearchHistoryUseCase(
        searchHistoryRepository: SearchHistoryRepository
    ): GetSearchHistoryUseCase {
        return GetSearchHistoryUseCase(searchHistoryRepository)
    }

    @Provides
    @Singleton
    fun provideClearSearchHistoryUseCase(
        searchHistoryRepository: SearchHistoryRepository
    ): ClearSearchHistoryUseCase {
        return ClearSearchHistoryUseCase(searchHistoryRepository)
    }

    @Provides
    @Singleton
    fun provideConvertLyricsUseCase(): ConvertLyricsUseCase {
        return ConvertLyricsUseCase()
    }

    @Provides
    @Singleton
    fun provideGetSettingsUseCase(
        settingsRepository: SettingsRepository
    ): GetSettingsUseCase {
        return GetSettingsUseCase(settingsRepository)
    }

    @Provides
    @Singleton
    fun provideUpdateSettingsUseCase(
        settingsRepository: SettingsRepository
    ): UpdateSettingsUseCase {
        return UpdateSettingsUseCase(settingsRepository)
    }
}
