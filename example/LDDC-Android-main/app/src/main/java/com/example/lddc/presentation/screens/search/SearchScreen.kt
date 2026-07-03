package com.example.lddc.presentation.screens.search

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.presentation.components.designsystem.LDDCCard
import com.example.lddc.presentation.components.designsystem.LDDCEmptyState
import com.example.lddc.presentation.components.designsystem.LDDCFilledButton
import com.example.lddc.presentation.components.designsystem.LDDCLoadingState
import com.example.lddc.presentation.components.designsystem.LDDCOutlinedButton
import com.example.lddc.presentation.components.designsystem.LDDCSearchInput
import com.example.lddc.presentation.components.designsystem.LDDCSourceChip
import com.example.lddc.presentation.theme.KugouColor
import com.example.lddc.presentation.theme.NetEaseColor
import com.example.lddc.presentation.theme.QQMusicColor

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun SearchScreen(
    viewModel: SearchViewModel,
    initialQuery: String = "",
    initialFilters: SearchFilters = SearchFilters(),
    onSongClick: (SongInfo) -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val searchHistory by viewModel.searchHistory.collectAsState()
    var showFilterDialog by remember { mutableStateOf(false) }

    // 处理初始搜索词和筛选条件
    // 只在以下情况执行搜索：
    // 1. 有初始搜索词且当前没有搜索结果（首次进入）
    // 2. 有初始搜索词且当前关键词为空（从其他页面跳转过来）
    LaunchedEffect(Unit) {
        if (initialQuery.isNotEmpty() && !uiState.hasSearched) {
            viewModel.onKeywordChange(initialQuery)
            // 应用初始筛选条件
            if (initialFilters.hasActiveFilters()) {
                viewModel.onFiltersChange(initialFilters)
            }
            viewModel.search()
        }
    }

    // 筛选对话框
    if (showFilterDialog) {
        FilterDialog(
            searchFilters = uiState.filters,
            enabledSources = uiState.enabledSources,
            onFiltersChanged = viewModel::onFiltersChange,
            onDismiss = { }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "搜索歌词",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        modifier = modifier
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp)
        ) {
            Spacer(modifier = Modifier.height(8.dp))

            // 搜索栏
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 搜索输入框
                LDDCSearchInput(
                    value = uiState.keyword,
                    onValueChange = viewModel::onKeywordChange,
                    placeholder = "搜索歌曲、歌手",
                    onSearch = viewModel::search,
                    modifier = Modifier.weight(1f)
                )

                // 筛选按钮
                val activeFilterCount = uiState.filters.getActiveFilterCount()
                BadgedBox(
                    badge = {
                        if (activeFilterCount > 0) {
                            androidx.compose.material3.Badge {
                                Text(activeFilterCount.toString())
                            }
                        }
                    }
                ) {
                    LDDCOutlinedButton(
                        text = "筛选",
                        onClick = { },
                        icon = Icons.Default.FilterList
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 内容区域
            when {
                uiState.isSearching -> {
                    LDDCLoadingState(text = "搜索中...")
                }

                uiState.errorMessage != null -> {
                    LDDCEmptyState(
                        icon = Icons.Default.Search,
                        title = "搜索失败",
                        description = uiState.errorMessage!!,
                        action = {
                            LDDCFilledButton(
                                text = "重试",
                                onClick = viewModel::search
                            )
                        }
                    )
                }

                !uiState.hasSearched -> {
                    // 显示搜索历史
                    if (searchHistory.isNotEmpty()) {
                        SearchHistorySection(
                            history = searchHistory.map { it.keyword },
                            onItemClick = { viewModel.searchFromHistory(it) },
                            onClear = { viewModel.clearAllSearchHistory() }
                        )
                    } else {
                        LDDCEmptyState(
                            icon = Icons.Default.Search,
                            title = "开始搜索",
                            description = "输入关键词搜索歌词"
                        )
                    }
                }

                uiState.searchResults.isEmpty() -> {
                    LDDCEmptyState(
                        icon = Icons.Default.Search,
                        title = "未找到结果",
                        description = "尝试使用其他关键词搜索"
                    )
                }

                else -> {
                    // 使用筛选后的结果
                    val displaySongs = uiState.filteredResults
                    val totalCount = uiState.searchResults.values.flatten().size

                    // 搜索结果列表
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = if (displaySongs.size != totalCount)
                                "搜索结果 (${displaySongs.size}/$totalCount)"
                            else
                                "搜索结果 ($totalCount)",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Medium
                        )

                        // 清除筛选按钮
                        if (uiState.filters.hasActiveFilters()) {
                            Text(
                                text = "清除筛选",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.clickable { viewModel.clearFilters() }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    if (displaySongs.isEmpty()) {
                        LDDCEmptyState(
                            icon = Icons.Default.Search,
                            title = "没有符合条件的结果",
                            description = "尝试调整筛选条件"
                        )
                    } else {
                        // 根据屏幕方向使用单列或多列
                        val configuration = LocalConfiguration.current
                        val isLandscape = configuration.screenWidthDp > configuration.screenHeightDp

                        if (isLandscape) {
                            // 横屏使用网格布局
                            val gridState = rememberLazyGridState()
                            // 用于检测滑动方向
                            var lastFirstVisibleItem by remember { mutableIntStateOf(0) }
                            var lastFirstVisibleScrollOffset by remember { mutableIntStateOf(0) }

                            // 监听滚动到底部
                            LaunchedEffect(gridState, uiState.hasMoreData) {
                                snapshotFlow {
                                    Triple(
                                        gridState.layoutInfo.visibleItemsInfo,
                                        gridState.firstVisibleItemIndex,
                                        gridState.firstVisibleItemScrollOffset
                                    )
                                }
                                    .collect { (visibleItems, firstIndex, scrollOffset) ->
                                        if (!uiState.hasMoreData || uiState.isLoadingMore) return@collect

                                        val totalItems = gridState.layoutInfo.totalItemsCount
                                        val lastVisibleItem = visibleItems.lastOrNull()?.index ?: 0

                                        // 判断是否滑到底部
                                        val isNearBottom = lastVisibleItem >= totalItems - 2

                                        // 判断是否在滑动（第一个可见项或偏移量发生变化）
                                        val isScrolling = firstIndex != lastFirstVisibleItem ||
                                                scrollOffset != lastFirstVisibleScrollOffset

                                        // 更新上次状态
                                        lastFirstVisibleItem = firstIndex
                                        lastFirstVisibleScrollOffset = scrollOffset

                                        // 同时满足：滑到底部 + 正在滑动
                                        if (isNearBottom && isScrolling) {
                                            viewModel.loadMore()
                                        }
                                    }
                            }

                            LazyVerticalGrid(
                                columns = GridCells.Adaptive(minSize = 320.dp),
                                state = gridState,
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                verticalArrangement = Arrangement.spacedBy(12.dp),
                                contentPadding = PaddingValues(bottom = 16.dp)
                            ) {
                                items(displaySongs) { song ->
                                    SearchResultGridItem(
                                        song = song,
                                        onClick = { onSongClick(song) }
                                    )
                                }

                                // 加载更多指示器
                                if (uiState.isLoadingMore || uiState.hasMoreData) {
                                    item(span = { GridItemSpan(maxLineSpan) }) {
                                        LoadMoreIndicator(
                                            isLoading = uiState.isLoadingMore,
                                            hasMoreData = uiState.hasMoreData,
                                            onClick = { viewModel.loadMore() }
                                        )
                                    }
                                }
                            }
                        } else {
                            // 竖屏使用单列列表
                            val listState = rememberLazyListState()
                            // 用于检测滑动方向
                            var lastFirstVisibleItem by remember { mutableIntStateOf(0) }
                            var lastFirstVisibleScrollOffset by remember { mutableIntStateOf(0) }

                            // 监听滚动到底部
                            LaunchedEffect(listState, uiState.hasMoreData) {
                                snapshotFlow {
                                    Triple(
                                        listState.layoutInfo.visibleItemsInfo,
                                        listState.firstVisibleItemIndex,
                                        listState.firstVisibleItemScrollOffset
                                    )
                                }
                                    .collect { (visibleItems, firstIndex, scrollOffset) ->
                                        if (!uiState.hasMoreData || uiState.isLoadingMore) return@collect

                                        val totalItems = listState.layoutInfo.totalItemsCount
                                        val lastVisibleItem = visibleItems.lastOrNull()?.index ?: 0

                                        // 判断是否滑到底部
                                        val isNearBottom = lastVisibleItem >= totalItems - 2

                                        // 判断是否在滑动（第一个可见项或偏移量发生变化）
                                        val isScrolling = firstIndex != lastFirstVisibleItem ||
                                                scrollOffset != lastFirstVisibleScrollOffset

                                        // 更新上次状态
                                        lastFirstVisibleItem = firstIndex
                                        lastFirstVisibleScrollOffset = scrollOffset

                                        // 同时满足：滑到底部 + 正在滑动
                                        if (isNearBottom && isScrolling) {
                                            viewModel.loadMore()
                                        }
                                    }
                            }

                            LazyColumn(
                                state = listState,
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                                contentPadding = PaddingValues(bottom = 16.dp)
                            ) {
                                items(displaySongs) { song ->
                                    SearchResultItem(
                                        song = song,
                                        onClick = { onSongClick(song) }
                                    )
                                }

                                // 加载更多指示器
                                if (uiState.isLoadingMore || uiState.hasMoreData) {
                                    item {
                                        LoadMoreIndicator(
                                            isLoading = uiState.isLoadingMore,
                                            hasMoreData = uiState.hasMoreData,
                                            onClick = { viewModel.loadMore() }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SearchHistorySection(
    history: List<String>,
    onItemClick: (String) -> Unit,
    onClear: () -> Unit
) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "搜索历史",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = "清空",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.clickable { onClear() }
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            history.forEach { keyword ->
                SearchHistoryChip(
                    keyword = keyword,
                    onClick = { onItemClick(keyword) }
                )
            }
        }
    }
}

@Composable
private fun LoadMoreIndicator(
    isLoading: Boolean,
    hasMoreData: Boolean,
    onClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        if (isLoading) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "加载中...",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
        } else if (hasMoreData) {
            TextButton(
                onClick = onClick,
                modifier = Modifier
                    .padding(8.dp)
            ) {
                Text(
                    text = "点击加载更多",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        } else {
            Text(
                text = "没有更多数据了",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun SearchHistoryChip(
    keyword: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Icon(
            imageVector = Icons.Default.History,
            contentDescription = null,
            modifier = Modifier.size(16.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = keyword,
            fontSize = 14.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun SearchResultItem(
    song: SongInfo,
    onClick: () -> Unit
) {
    LDDCCard(
        onClick = onClick,
        elevated = true
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 专辑封面
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                if (!song.imageUrl.isNullOrEmpty()) {
                    AsyncImage(
                        model = song.imageUrl,
                        contentDescription = null,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }

            Spacer(modifier = Modifier.width(16.dp))

            // 歌曲信息
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = song.title ?: "未知歌曲",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = song.artist?.toString() ?: "未知歌手",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1
                )
            }

            // 来源标签
            song.source?.let { source ->
                LDDCSourceChip(
                    text = getSourceShortName(source),
                    sourceColor = getSourceColor(source)
                )
            }
        }
    }
}

/**
 * 网格布局的搜索结果项（用于横屏）
 */
@Composable
private fun SearchResultGridItem(
    song: SongInfo,
    onClick: () -> Unit
) {
    LDDCCard(
        onClick = onClick,
        elevated = true
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 专辑封面
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                if (!song.imageUrl.isNullOrEmpty()) {
                    AsyncImage(
                        model = song.imageUrl,
                        contentDescription = null,
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            // 歌曲信息
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = song.title ?: "未知歌曲",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = song.artist?.toString() ?: "未知歌手",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            // 来源标签
            song.source?.let { source ->
                LDDCSourceChip(
                    text = getSourceShortName(source),
                    sourceColor = getSourceColor(source)
                )
            }
        }
    }
}

private fun getSourceShortName(source: Source): String {
    return when (source) {
        Source.QM -> "QQ"
        Source.NE -> "网易"
        Source.KG -> "酷狗"
        Source.MULTI -> "全部"
        else -> source.name
    }
}

@Composable
private fun getSourceColor(source: Source): androidx.compose.ui.graphics.Color {
    return when (source) {
        Source.QM -> QQMusicColor
        Source.NE -> NetEaseColor
        Source.KG -> KugouColor
        Source.MULTI -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.primary
    }
}
