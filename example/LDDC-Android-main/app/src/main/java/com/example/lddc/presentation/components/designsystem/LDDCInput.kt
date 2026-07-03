package com.example.lddc.presentation.components.designsystem

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * LDDC 设计系统 - 输入组件
 *
 * 提供多种输入框变体：标准输入框、搜索框、下拉选择框、多行文本框
 */

/**
 * 标准输入框
 */
@Composable
fun LDDCInput(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = "",
    label: String? = null,
    leadingIcon: ImageVector? = null,
    trailingIcon: ImageVector? = null,
    onTrailingIconClick: (() -> Unit)? = null,
    isError: Boolean = false,
    errorMessage: String? = null,
    keyboardType: KeyboardType = KeyboardType.Text,
    imeAction: ImeAction = ImeAction.Done,
    onImeAction: (() -> Unit)? = null,
    singleLine: Boolean = true,
    maxLines: Int = 1,
    enabled: Boolean = true,
    readOnly: Boolean = false
) {
    Column(modifier = modifier.fillMaxWidth()) {
        if (label != null) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(bottom = 8.dp)
            )
        }

        val borderColor = when {
            isError -> MaterialTheme.colorScheme.error
            value.isNotEmpty() -> MaterialTheme.colorScheme.primary
            else -> MaterialTheme.colorScheme.outline
        }

        val backgroundColor = if (enabled) {
            MaterialTheme.colorScheme.surface
        } else {
            MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        }

        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            enabled = enabled,
            readOnly = readOnly,
            textStyle = TextStyle(
                fontSize = 15.sp,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Normal
            ),
            keyboardOptions = KeyboardOptions(
                keyboardType = keyboardType,
                imeAction = imeAction
            ),
            keyboardActions = KeyboardActions(
                onDone = { onImeAction?.invoke() },
                onSearch = { onImeAction?.invoke() },
                onSend = { onImeAction?.invoke() }
            ),
            singleLine = singleLine,
            maxLines = maxLines,
            cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
            decorationBox = { innerTextField ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(backgroundColor)
                        .border(
                            width = 1.dp,
                            color = borderColor,
                            shape = RoundedCornerShape(12.dp)
                        )
                        .padding(horizontal = 16.dp, vertical = 14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (leadingIcon != null) {
                        Icon(
                            imageVector = leadingIcon,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                    }

                    Box(modifier = Modifier.weight(1f)) {
                        if (value.isEmpty() && placeholder.isNotEmpty()) {
                            Text(
                                text = placeholder,
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                            )
                        }
                        innerTextField()
                    }

                    if (trailingIcon != null) {
                        Spacer(modifier = Modifier.width(12.dp))
                        if (onTrailingIconClick != null) {
                            IconButton(
                                onClick = onTrailingIconClick,
                                modifier = Modifier.size(20.dp)
                            ) {
                                Icon(
                                    imageVector = trailingIcon,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        } else {
                            Icon(
                                imageVector = trailingIcon,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        )

        if (isError && errorMessage != null) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = errorMessage,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}

/**
 * 搜索输入框
 */
@Composable
fun LDDCSearchInput(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = "搜索...",
    onSearch: (() -> Unit)? = null,
    enabled: Boolean = true
) {
    val backgroundColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)

    BasicTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier.fillMaxWidth(),
        enabled = enabled,
        textStyle = TextStyle(
            fontSize = 15.sp,
            color = MaterialTheme.colorScheme.onSurface,
            fontWeight = FontWeight.Normal
        ),
        keyboardOptions = KeyboardOptions(
            imeAction = ImeAction.Search
        ),
        keyboardActions = KeyboardActions(
            onSearch = { onSearch?.invoke() }
        ),
        singleLine = true,
        cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
        decorationBox = { innerTextField ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(backgroundColor)
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.width(12.dp))

                Box(modifier = Modifier.weight(1f)) {
                    if (value.isEmpty()) {
                        Text(
                            text = placeholder,
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                        )
                    }
                    innerTextField()
                }

                if (value.isNotEmpty()) {
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = { onValueChange("") },
                        modifier = Modifier.size(20.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Clear,
                            contentDescription = "清除",
                            modifier = Modifier.size(18.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    )
}

