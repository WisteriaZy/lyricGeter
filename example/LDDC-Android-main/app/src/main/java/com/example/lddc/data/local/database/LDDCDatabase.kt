package com.example.lddc.data.local.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.lddc.data.local.database.dao.LyricsCacheDao
import com.example.lddc.data.local.database.dao.SearchHistoryDao
import com.example.lddc.data.local.database.entity.LyricsCacheEntity
import com.example.lddc.data.local.database.entity.SearchHistoryEntity

@Database(
    entities = [LyricsCacheEntity::class, SearchHistoryEntity::class],
    version = 2,
    exportSchema = false
)
abstract class LDDCDatabase : RoomDatabase() {
    abstract fun lyricsCacheDao(): LyricsCacheDao
    abstract fun searchHistoryDao(): SearchHistoryDao

    companion object {
        @Volatile
        private var INSTANCE: LDDCDatabase? = null

        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                // 从版本 1 升级到版本 2
                // 由于我们删除了 LocalMusicCache，所以不需要额外的迁移操作
            }
        }

        fun getDatabase(context: Context): LDDCDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(
                    context.applicationContext,
                    LDDCDatabase::class.java,
                    "lddc_database"
                )
                    .addMigrations(MIGRATION_1_2)
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
