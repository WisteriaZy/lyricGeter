# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# ==================== 基础配置 ====================

# 保留注解
-keepattributes *Annotation*

# 保留签名
-keepattributes Signature

# 保留异常
-keepattributes Exceptions

# 保留内部类
-keepattributes InnerClasses

# 保留封闭方法
-keepattributes EnclosingMethod

# 保留泛型信息
-keepattributes Signature

# 保留运行时可见注解
-keepattributes RuntimeVisibleAnnotations,RuntimeVisibleParameterAnnotations

# 移除 Kotlin 元数据警告
-dontwarn kotlin.Metadata

# ==================== 日志优化（Release 包移除日志）====================
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int i(...);
    public static int w(...);
    public static int d(...);
    public static int e(...);
}

# ==================== Jetpack Compose ====================
-dontwarn androidx.compose.**
-keep class androidx.compose.** { *; }
-keep class com.example.lddc.presentation.theme.** { *; }
-keep class com.example.lddc.ui.theme.** { *; }

# ==================== Hilt ====================
-keep class dagger.hilt.** { *; }
-keep class com.example.lddc.di.** { *; }
-keep class * extends dagger.hilt.android.HiltApplication
-keep class * extends dagger.hilt.android.lifecycle.HiltViewModel

# ==================== Room ====================
-keep class com.example.lddc.data.local.database.** { *; }
-keep class * extends androidx.room.RoomDatabase
-keep class * implements androidx.room.Dao
-dontwarn androidx.room.paging.**

# ==================== DataStore ====================
-keep class com.example.lddc.data.local.datastore.** { *; }

# ==================== Ktor ====================
-dontwarn io.ktor.**
-keep class io.ktor.** { *; }
-keepclassmembers class io.ktor.** { *; }

# ==================== Serialization ====================
-keep class kotlinx.serialization.** { *; }
-keep class com.example.lddc.common.models.** { *; }
-keepclassmembers class com.example.lddc.common.models.** { *; }

# ==================== Coroutines ====================
-keep class kotlinx.coroutines.** { *; }
-keepclassmembers class kotlinx.coroutines.** {
    volatile <fields>;
}

# ==================== Audio Tagging ====================
-keep class org.jaudiotagger.** { *; }

# ==================== Coil ====================
-keep class coil.** { *; }

# ==================== WorkManager ====================
-keep class androidx.work.** { *; }

# ==================== Navigation ====================
-keep class androidx.navigation.** { *; }

# ==================== 项目特定类 ====================

# 保留所有模型类
-keep class com.example.lddc.common.models.** { *; }
-keepclassmembers class com.example.lddc.common.models.** { *; }

# 保留所有仓库类
-keep class com.example.lddc.data.repository.** { *; }

# 保留所有用例类
-keep class com.example.lddc.domain.** { *; }

# 保留所有 ViewModel 类
-keep class com.example.lddc.presentation.viewmodel.** { *; }
-keep class com.example.lddc.presentation.screens.**.*ViewModel { *; }

# 保留所有组件
-keep class com.example.lddc.presentation.components.** { *; }

# 保留所有页面
-keep class com.example.lddc.presentation.screens.** { *; }

# 保留所有工具类
-keep class com.example.lddc.common.utils.** { *; }

# 保留所有 API 类
-keep class com.example.lddc.core.api.** { *; }

# 保留所有解密器类
-keep class com.example.lddc.core.decryptor.** { *; }

# 保留所有解析器类
-keep class com.example.lddc.core.parser.** { *; }

# 保留所有枚举
-keep enum com.example.lddc.common.models.enums.** { *; }

# ==================== Kotlin 特定 ====================

# 保留 Kotlin 伴生对象
-keepclassmembers class **$Companion {
    <fields>;
    <methods>;
}

# 保留 Kotlin 数据类
-keepclassmembers class * extends kotlin.jvm.internal.GeneratedByKotlinCompiler {
    <init>();
}

# 保留 Kotlin 元数据
-keepclassmembers class * {
    @kotlin.Metadata public *;
}

# ==================== AndroidX ====================
# 只保留真正需要的AndroidX类
-keep class androidx.compose.** { *; }
-keep class androidx.navigation.** { *; }
-keep class androidx.work.** { *; }
-keep class androidx.room.** { *; }
-keep class androidx.datastore.** { *; }

# ==================== Google Play Services ====================
-keep class com.google.** { *; }

# ==================== OkHttp ====================
-keep class okhttp3.** { *; }
-keep class okio.** { *; }

# ==================== 其他库 ====================
# 只保留真正使用的库
# -keep class retrofit2.** { *; }
# -keep class com.google.gson.** { *; }
# -keep class com.fasterxml.jackson.** { *; }
-keep class android.util.Log { *; }

# ==================== BuildConfig 和 R 类 ====================
-keep class com.example.lddc.BuildConfig { *; }
-keep class com.example.lddc.R { *; }
-keep class com.example.lddc.R$* { *; }

# ==================== 优化配置 ====================

# 代码优化
-optimizations !code/simplification/arithmetic,!code/simplification/cast,!field/*,!class/merging/*

# 打印映射文件
-printmapping mapping.txt

# 打印使用情况
-printusage usage.txt

# 不警告缺失的类
-dontwarn **

# 不记录缺失的类
-dontnote **

# ==================== 资源优化 ====================


# 优化资源
-optimizations resource/shrinking

# ==================== 其他优化 ====================

# 移除未使用的代码
-dontusemixedcaseclassnames
-dontskipnonpubliclibraryclasses
-dontpreverify
-verbose

# 优化字节码
-optimizations code/removal/simple,code/removal/variable,code/removal/exception,code/simplification/variable,code/simplification/arithmetic
