package com.example.lddc.presentation.components.designsystem

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * LDDC 设计系统 - 卡片组件
 *
 * 提供多种卡片变体：标准卡片、可点击卡片、列表卡片、信息卡片
 */

/**
 * 标准卡片
 */
@Composable
fun LDDCCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    elevated: Boolean = true,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(
            defaultElevation = if (elevated) 2.dp else 0.dp
        ),
        border = if (!elevated) BorderStroke(
            width = 1.dp,
            color = MaterialTheme.colorScheme.outlineVariant
        ) else null
    ) {
        if (onClick != null) {
            Box(modifier = Modifier.clickable(onClick = onClick)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    content = content
                )
            }
        } else {
            Column(
                modifier = Modifier.padding(16.dp),
                content = content
            )
        }
    }
}

