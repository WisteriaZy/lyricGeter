package com.example.lddc.presentation.screens.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.lddc.common.models.enums.Source
import com.example.lddc.presentation.components.designsystem.LDDCFilledButton
import com.example.lddc.presentation.components.designsystem.LDDCFilterChip
import com.example.lddc.presentation.components.designsystem.LDDCInput

/**
 * 筛选对话框
 *
 * 用于搜索结果页面的筛选功能
 *
 * @param searchFilters 当前筛选条件
 * @param enabledSources 启用的搜索源
 * @param onFiltersChanged 筛选条件变化回调
 * @param onDismiss 关闭对话框回调
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun FilterDialog(
    searchFilters: SearchFilters,
    enabledSources: List<Source>,
    onFiltersChanged: (SearchFilters) -> Unit,
    onDismiss: () -> Unit
) {
    var tempFilters by remember { mutableStateOf(searchFilters) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "筛选条件",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp)
            ) {
                // 歌曲名筛选
                LDDCInput(
                    value = tempFilters.songName,
                    onValueChange = { tempFilters = tempFilters.copy(songName = it) },
                    placeholder = "按歌曲名筛选",
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(16.dp))

                // 作者筛选
                LDDCInput(
                    value = tempFilters.artist,
                    onValueChange = { tempFilters = tempFilters.copy(artist = it) },
                    placeholder = "按歌手名筛选",
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(16.dp))

                // 专辑筛选
                LDDCInput(
                    value = tempFilters.album,
                    onValueChange = { tempFilters = tempFilters.copy(album = it) },
                    placeholder = "按专辑名筛选",
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(20.dp))

                // 平台筛选
                Text(
                    text = "平台筛选",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // 各个平台选项（不再显示"全部平台"选项）
                    enabledSources.filter { it != Source.MULTI }.forEach { source ->
                        val isSelected = source in tempFilters.platforms
                        LDDCFilterChip(
                            text = getSourceDisplayName(source),
                            selected = isSelected,
                            onClick = {
                                val newPlatforms = tempFilters.platforms.toMutableSet()
                                if (isSelected) {
                                    newPlatforms.remove(source)
                                } else {
                                    newPlatforms.add(source)
                                }
                                tempFilters = tempFilters.copy(platforms = newPlatforms)
                            }
                        )
                    }
                }
            }
        },
        confirmButton = {
            LDDCFilledButton(
                text = "确定",
                onClick = {
                    onFiltersChanged(tempFilters)
                    onDismiss()
                }
            )
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("取消")
            }
        }
    )
}

private fun getSourceDisplayName(source: Source): String {
    return when (source) {
        Source.QM -> "QQ音乐"
        Source.NE -> "网易云"
        Source.KG -> "酷狗音乐"
        Source.MULTI -> "全部"
        else -> source.name
    }
}


