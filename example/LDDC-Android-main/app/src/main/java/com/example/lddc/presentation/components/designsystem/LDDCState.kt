package com.example.lddc.presentation.components.designsystem

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * LDDC 设计系统 - 状态组件
 *
 * 提供多种状态显示：加载状态、空状态、错误状态、占位状态
 */

/**
 * 加载状态
 */
@Composable
fun LDDCLoadingState(
    modifier: Modifier = Modifier,
    text: String = "加载中...",
    size: LoadingSize = LoadingSize.Medium
) {
    val indicatorSize = when (size) {
        LoadingSize.Small -> 24.dp
        LoadingSize.Medium -> 40.dp
        LoadingSize.Large -> 56.dp
    }

    val textSize = when (size) {
        LoadingSize.Small -> 13.sp
        LoadingSize.Medium -> 14.sp
        LoadingSize.Large -> 16.sp
    }

    Column(
        modifier = modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(indicatorSize),
            color = MaterialTheme.colorScheme.primary,
            strokeWidth = if (size == LoadingSize.Small) 2.dp else 3.dp
        )

        if (text.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = text,
                fontSize = textSize,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * 空状态
 */
@Composable
fun LDDCEmptyState(
    modifier: Modifier = Modifier,
    icon: ImageVector = Icons.Default.Search,
    title: String = "暂无数据",
    description: String? = null,
    action: @Composable (() -> Unit)? = null
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(80.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(40.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )

        if (description != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }

        if (action != null) {
            Spacer(modifier = Modifier.height(24.dp))
            action()
        }
    }
}

enum class LoadingSize {
    Small, Medium, Large
}
