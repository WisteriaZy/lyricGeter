package com.example.lddc.presentation.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

/**
 * LDDC 设计系统 - 形状规范
 *
 * 统一使用圆角设计，营造柔和现代的视觉感受
 */

val Shapes = Shapes(
    // 小圆角 - 用于按钮、标签等小元素
    small = RoundedCornerShape(8.dp),
    // 中圆角 - 用于卡片、输入框等
    medium = RoundedCornerShape(12.dp),
    // 大圆角 - 用于对话框、底部卡片等
    large = RoundedCornerShape(16.dp),
    // 超大圆角 - 用于特殊容器
    extraLarge = RoundedCornerShape(28.dp)
)

