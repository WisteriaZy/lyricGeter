package com.example.lddc.presentation.screens.search

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.lddc.common.models.enums.LyricsFormat
import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.presentation.components.designsystem.ButtonSize
import com.example.lddc.presentation.components.designsystem.LDDCChip
import com.example.lddc.presentation.components.designsystem.LDDCFilledButton
import com.example.lddc.presentation.components.designsystem.LDDCLoadingState
import com.example.lddc.presentation.components.designsystem.LDDCSourceChip

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LyricsDetailScreen(
    viewModel: LyricsDetailViewModel,
    song: SongInfo?,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    LaunchedEffect(song) {
        song?.let { viewModel.loadLyrics(it) }
    }
    val uiState by viewModel.uiState.collectAsState()
    val clipboardManager = LocalClipboardManager.current
    val configuration = LocalConfiguration.current
    val isLandscape =
        configuration.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "歌曲详情",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "返回"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        modifier = modifier
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background)
        ) {
            if (uiState.isLoading) {
                LDDCLoadingState(text = "加载歌词中...")
            } else {
                if (isLandscape) {
                    LandscapeLayout(uiState, viewModel, clipboardManager)
                } else {
                    PortraitLayout(uiState, viewModel, clipboardManager)
                }
            }
        }
    }
}

@Composable
private fun PortraitLayout(
    uiState: LyricsDetailViewModel.LyricsDetailUiState,
    viewModel: LyricsDetailViewModel,
    clipboardManager: androidx.compose.ui.platform.ClipboardManager
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(scrollState),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 歌曲信息卡片 - 不使用固定高度，让内容完全展示
        SongInfoCard(
            song = uiState.currentSong,
            lyrics = uiState.lyrics,
            modifier = Modifier.fillMaxWidth()
        )

        // 源选择
        if (uiState.allLyrics.size > 1) {
            SourceSelector(
                sources = uiState.allLyrics.keys.toList(),
                currentSource = uiState.currentSource,
                onSourceSelected = { viewModel.switchSource(it) }
            )
        }

        // 歌词卡片 - 设置固定高度确保歌词区域足够大
        LyricsCard(
            lyrics = uiState.convertedLyrics ?: "暂无歌词",
            onCopy = { clipboardManager.setText(AnnotatedString(it)) },
            availableLanguages = viewModel.getAvailableLanguages(),
            selectedLanguages = uiState.selectedLanguages,
            onLanguageToggle = { viewModel.onLanguageToggle(it) },
            selectedFormat = uiState.selectedFormat,
            availableFormats = viewModel.getAvailableFormats(),
            onFormatChange = { viewModel.onFormatChange(it) },
            modifier = Modifier
                .fillMaxWidth()
                .height(500.dp)
        )

        // 底部留白，确保可以滚动到底部
        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun LandscapeLayout(
    uiState: LyricsDetailViewModel.LyricsDetailUiState,
    viewModel: LyricsDetailViewModel,
    clipboardManager: androidx.compose.ui.platform.ClipboardManager
) {
    Row(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalArrangement = Arrangement.spacedBy(32.dp)
    ) {
        // 左侧：歌曲信息卡片
        SongInfoCard(
            song = uiState.currentSong,
            lyrics = uiState.lyrics,
            modifier = Modifier
                .weight(0.4f)
                .fillMaxHeight()
        )

        // 右侧：歌词卡片
        Column(
            modifier = Modifier
                .weight(0.6f)
                .fillMaxHeight(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // 源选择（横屏时显示在歌词卡片上方）
            if (uiState.allLyrics.size > 1) {
                SourceSelector(
                    sources = uiState.allLyrics.keys.toList(),
                    currentSource = uiState.currentSource,
                    onSourceSelected = { viewModel.switchSource(it) }
                )
            }

            LyricsCard(
                lyrics = uiState.convertedLyrics ?: "暂无歌词",
                onCopy = { clipboardManager.setText(AnnotatedString(it)) },
                availableLanguages = viewModel.getAvailableLanguages(),
                selectedLanguages = uiState.selectedLanguages,
                onLanguageToggle = { viewModel.onLanguageToggle(it) },
                selectedFormat = uiState.selectedFormat,
                availableFormats = viewModel.getAvailableFormats(),
                onFormatChange = { viewModel.onFormatChange(it) },
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
            )
        }
    }
}

@Composable
private fun SongInfoCard(
    song: SongInfo?,
    lyrics: com.example.lddc.common.models.lyrics.Lyrics? = null,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 第一排：专辑封面（放大，单独一排）
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.55f)
                    .aspectRatio(1f)
                    .clip(RoundedCornerShape(16.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                if (!song?.imageUrl.isNullOrEmpty()) {
                    AsyncImage(
                        model = song?.imageUrl,
                        contentDescription = null,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = androidx.compose.ui.layout.ContentScale.Crop
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.MusicNote,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 第二排：歌曲标题
            Text(
                text = song?.title ?: "未知歌曲",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(4.dp))

            // 第三排：歌手
            Text(
                text = song?.artist?.toString() ?: "未知歌手",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(2.dp))

            // 第四排：专辑
            Text(
                text = song?.album ?: "未知专辑",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(12.dp))

            // 第五排：标签信息（时长、来源）
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 时长
                song?.duration?.let { duration ->
                    if (duration > 0) {
                        LDDCChip(text = formatDuration(duration))
                        Spacer(modifier = Modifier.width(6.dp))
                    }
                }

                // 来源
                song?.source?.let { source ->
                    val (sourceName, sourceColor) = when (source) {
                        Source.QM -> "QQ" to Color(0xFF31C27C)
                        Source.NE -> "网易" to Color(0xFFE60026)
                        Source.KG -> "酷狗" to Color(0xFF00A9FF)
                        else -> source.name to MaterialTheme.colorScheme.primary
                    }
                    LDDCSourceChip(
                        text = sourceName,
                        sourceColor = sourceColor
                    )
                }
            }

            // 第六排：歌词格式信息（换到下一行）
            lyrics?.let { lyricData ->
                if (lyricData.types.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        LyricsFormatInfo(types = lyricData.types)
                    }
                }
            }
        }
    }
}

/**
 * 歌词格式信息显示
 */
@Composable
private fun LyricsFormatInfo(
    types: Map<String, LyricsType>
) {
    val langTypeMap = mutableMapOf<String, LyricsType>()
    types.forEach { (lang, type) ->
        langTypeMap[lang] = type
    }

    val sortedLangs = langTypeMap.keys.sortedBy { lang ->
        when (lang) {
            "orig" -> 0
            "ts" -> 1
            "roma" -> 2
            else -> 3
        }
    }

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        sortedLangs.forEachIndexed { index, lang ->
            val langName = when (lang) {
                "orig" -> "原文"
                "ts" -> "译文"
                "roma" -> "罗马音"
                else -> lang
            }
            val typeName = when (langTypeMap[lang]) {
                LyricsType.VERBATIM -> "逐字"
                LyricsType.LINEBYLINE -> "逐行"
                else -> "纯文本"
            }

            LyricsTypeChip(label = langName, type = typeName)

            if (index < sortedLangs.size - 1) {
                Spacer(modifier = Modifier.width(8.dp))
            }
        }
    }
}

/**
 * 歌词类型标签
 */
@Composable
private fun LyricsTypeChip(label: String, type: String) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.7f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSecondaryContainer,
            fontWeight = FontWeight.Medium
        )
        Text(
            text = "($type)",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.8f)
        )
    }
}

@Composable
private fun SourceSelector(
    sources: List<Source>,
    currentSource: Source?,
    onSourceSelected: (Source) -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        sources.forEach { source ->
            val selected = currentSource == source
            val (color, text) = when (source) {
                Source.QM -> Color(0xFF31C27C) to "QQ"
                Source.NE -> Color(0xFFE60026) to "网易"
                Source.KG -> Color(0xFF00A9FF) to "酷狗"
                else -> MaterialTheme.colorScheme.outline to "?"
            }

            LDDCSourceChip(
                text = text,
                sourceColor = color,
                selected = selected,
                onClick = { onSourceSelected(source) }
            )
        }
    }
}

@Composable
private fun LanguageToggleChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .size(36.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(
                if (selected) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.surfaceVariant
            )
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium,
            color = if (selected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun LyricsCard(
    lyrics: String,
    onCopy: (String) -> Unit,
    availableLanguages: List<String>,
    selectedLanguages: List<String>,
    onLanguageToggle: (String) -> Unit,
    selectedFormat: LyricsFormat,
    availableFormats: List<LyricsFormat>,
    onFormatChange: (LyricsFormat) -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(20.dp)
        ) {
            // 标题栏：歌词 + 语言选择按钮 + 格式选择器 + 复制按钮
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 左侧：歌词标题 + 语言选择按钮
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = "歌词",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )

                    // 语言选择按钮（紧跟在"歌词"后面）
                    if (availableLanguages.size > 1) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            val sortedLanguages = availableLanguages.sortedBy { lang ->
                                when (lang) {
                                    "orig" -> 0
                                    "ts" -> 1
                                    "roma" -> 2
                                    else -> 3
                                }
                            }

                            sortedLanguages.forEach { lang ->
                                val label = when (lang) {
                                    "orig" -> "原"
                                    "ts" -> "译"
                                    "roma" -> "音"
                                    else -> lang
                                }
                                val selected = lang in selectedLanguages

                                LanguageToggleChip(
                                    label = label,
                                    selected = selected,
                                    onClick = { onLanguageToggle(lang) }
                                )
                            }
                        }
                    }
                }

                // 右侧：格式选择器 + 复制按钮
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // 格式选择器
                    if (availableFormats.size > 1) {
                        FormatSelector(
                            selectedFormat = selectedFormat,
                            availableFormats = availableFormats,
                            onFormatChange = onFormatChange
                        )
                    }

                    // 复制按钮
                    LDDCFilledButton(
                        text = "复制",
                        onClick = { onCopy(lyrics) },
                        icon = Icons.Default.ContentCopy,
                        size = ButtonSize.Small
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 歌词内容 - 可滑动
            val scrollState = rememberScrollState()
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .clip(RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f))
                    .verticalScroll(scrollState)
                    .padding(16.dp)
            ) {
                Text(
                    text = lyrics,
                    style = MaterialTheme.typography.bodyMedium.copy(
                        lineHeight = 28.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                )
            }
        }
    }
}

@Composable
private fun FormatSelector(
    selectedFormat: LyricsFormat,
    availableFormats: List<LyricsFormat>,
    onFormatChange: (LyricsFormat) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    Box {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                .clickable { expanded = true }
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                text = selectedFormat.displayName,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface
            )
            Icon(
                imageVector = Icons.Default.KeyboardArrowDown,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false }
        ) {
            availableFormats.forEach { format ->
                DropdownMenuItem(
                    text = { Text(format.displayName) },
                    onClick = {
                        onFormatChange(format)
                        expanded = false
                    }
                )
            }
        }
    }
}

private fun formatDuration(durationMs: Int?): String {
    if (durationMs == null || durationMs <= 0) return ""
    val minutes = durationMs / 1000 / 60
    val seconds = (durationMs / 1000) % 60
    return String.format("%d:%02d", minutes, seconds)
}
