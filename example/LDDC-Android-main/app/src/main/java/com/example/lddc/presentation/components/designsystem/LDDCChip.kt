package com.example.lddc.presentation.components.designsystem

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * LDDC 设计系统 - Chip 组件
 *
 * 提供多种 Chip 变体：标准 Chip、可选中 Chip、可删除 Chip、图标 Chip
 */

/**
 * 标准 Chip
 */
@Composable
fun LDDCChip(
    text: String,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    selected: Boolean = false,
    enabled: Boolean = true,
    icon: ImageVector? = null,
    onDelete: (() -> Unit)? = null,
    color: Color? = null
) {
    val backgroundColor = when {
        !enabled -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        selected -> color ?: MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.surfaceVariant
    }

    val contentColor = when {
        !enabled -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.38f)
        selected -> Color.White
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    val clickableModifier = if (onClick != null && enabled) {
        modifier.clickable(onClick = onClick)
    } else modifier

    Row(
        modifier = clickableModifier
            .clip(RoundedCornerShape(8.dp))
            .background(backgroundColor)
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        if (icon != null) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = contentColor
            )
        }

        Text(
            text = text,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = contentColor
        )

        if (onDelete != null && enabled) {
            Box(
                modifier = Modifier
                    .size(16.dp)
                    .clip(CircleShape)
                    .background(contentColor.copy(alpha = 0.2f))
                    .clickable(onClick = onDelete),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "删除",
                    modifier = Modifier.size(12.dp),
                    tint = contentColor
                )
            }
        }
    }
}

/**
 * 可选中 Chip（Filter Chip 样式）
 */
@Composable
fun LDDCFilterChip(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    icon: ImageVector? = null
) {
    val backgroundColor = when {
        !enabled -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        selected -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.surface
    }

    val contentColor = when {
        !enabled -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.38f)
        selected -> Color.White
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    val borderColor = when {
        !enabled -> MaterialTheme.colorScheme.outline.copy(alpha = 0.12f)
        selected -> Color.Transparent
        else -> MaterialTheme.colorScheme.outline
    }

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(backgroundColor)
            .border(
                width = 1.dp,
                color = borderColor,
                shape = RoundedCornerShape(8.dp)
            )
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        if (selected) {
            Icon(
                imageVector = Icons.Default.Check,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = contentColor
            )
        } else if (icon != null) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = contentColor
            )
        }

        Text(
            text = text,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = contentColor
        )
    }
}

/**
 * 来源 Chip（带品牌色）
 */
@Composable
fun LDDCSourceChip(
    text: String,
    sourceColor: Color,
    modifier: Modifier = Modifier,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null,
    enabled: Boolean = true
) {
    val backgroundColor = when {
        !enabled -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        selected -> sourceColor
        else -> sourceColor.copy(alpha = 0.1f)
    }

    val contentColor = when {
        !enabled -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.38f)
        selected -> Color.White
        else -> sourceColor
    }

    val clickableModifier = if (onClick != null && enabled) {
        modifier.clickable(onClick = onClick)
    } else modifier

    Box(
        modifier = clickableModifier
            .clip(RoundedCornerShape(20.dp))
            .background(backgroundColor)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = contentColor
        )
    }
}

