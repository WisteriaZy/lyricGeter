package com.example.lddc.common.models.enums

enum class LyricsFormat {
    VERBATIMLRC,
    LINEBYLINELRC,
    ENHANCEDLRC,
    SRT,
    ASS,
    QRC,
    KRC,
    YRC,
    JSON;

    val displayName: String
        get() = when (this) {
            VERBATIMLRC -> "逐字LRC"
            LINEBYLINELRC -> "逐行LRC"
            ENHANCEDLRC -> "增强LRC"
            SRT -> "SRT字幕"
            ASS -> "ASS字幕"
            QRC -> "QRC格式"
            KRC -> "KRC格式"
            YRC -> "YRC格式"
            JSON -> "JSON格式"
        }
}
