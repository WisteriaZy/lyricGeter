package com.example.lddc.presentation.components.designsystem

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * LDDC 设计系统 - 按钮组件
 *
 * 提供多种按钮变体：填充按钮、轮廓按钮、文本按钮、图标按钮
 */

/**
 * 填充按钮 - 主要操作
 */
@Composable
fun LDDCFilledButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
    loading: Boolean = false,
    size: ButtonSize = ButtonSize.Medium
) {
    val paddingValues = when (size) {
        ButtonSize.Small -> PaddingValues(horizontal = 16.dp, vertical = 8.dp)
        ButtonSize.Medium -> PaddingValues(horizontal = 24.dp, vertical = 12.dp)
        ButtonSize.Large -> PaddingValues(horizontal = 32.dp, vertical = 16.dp)
    }

    val fontSize = when (size) {
        ButtonSize.Small -> 13.sp
        ButtonSize.Medium -> 14.sp
        ButtonSize.Large -> 16.sp
    }

    Button(
        onClick = onClick,
        modifier = modifier.defaultMinSize(minHeight = if (size == ButtonSize.Small) 36.dp else 48.dp),
        enabled = enabled && !loading,
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
            disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant
        ),
        contentPadding = paddingValues
    ) {
        if (loading) {
            CircularProgressIndicator(
                modifier = Modifier.size(18.dp),
                color = MaterialTheme.colorScheme.onPrimary,
                strokeWidth = 2.dp
            )
        } else {
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(
                text = text,
                fontSize = fontSize,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * 轮廓按钮 - 次要操作
 */
@Composable
fun LDDCOutlinedButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
    size: ButtonSize = ButtonSize.Medium
) {
    val paddingValues = when (size) {
        ButtonSize.Small -> PaddingValues(horizontal = 16.dp, vertical = 8.dp)
        ButtonSize.Medium -> PaddingValues(horizontal = 24.dp, vertical = 12.dp)
        ButtonSize.Large -> PaddingValues(horizontal = 32.dp, vertical = 16.dp)
    }

    val fontSize = when (size) {
        ButtonSize.Small -> 13.sp
        ButtonSize.Medium -> 14.sp
        ButtonSize.Large -> 16.sp
    }

    Button(
        onClick = onClick,
        modifier = modifier.defaultMinSize(minHeight = if (size == ButtonSize.Small) 36.dp else 48.dp),
        enabled = enabled,
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.outlinedButtonColors(
            contentColor = MaterialTheme.colorScheme.primary,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant
        ),
        border = androidx.compose.foundation.BorderStroke(
            width = 1.dp,
            color = if (enabled) MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.surfaceVariant
        ),
        contentPadding = paddingValues
    ) {
        if (icon != null) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text(
            text = text,
            fontSize = fontSize,
            fontWeight = FontWeight.Medium
        )
    }
}

enum class ButtonSize {
    Small, Medium, Large
}

