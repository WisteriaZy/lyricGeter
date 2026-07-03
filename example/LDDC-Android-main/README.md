# LDDC-Android

⚠️ 注意：本项目全部代码由 AI 生成
本项目是基于 LDDC 的 Android 版本，所有代码（包括 README 文件）均由 AI 助手生成，不包含任何人工编写的代码。

一个支持多平台的精准歌词（逐字歌词）下载匹配工具 Android 版。

## 主要特性

- ⚡ 多线程快速匹配：所有歌词匹配功能均采用多线程技术，实现自动搜索与极速精准匹配每一个歌词。
- 📝 逐字歌词样式：绝大多数歌曲都能获取到逐字样式的歌词，精准同步到每个字。
- 💾 多种格式支持：支持保存歌词为逐字 LRC、逐行 LRC、增强型 LRC、SRT 和 ASS 等格式。
- 🎵 多音乐平台歌词搜索：支持搜索 QQ音乐、酷狗音乐、网易云音乐中的单曲。
- 🛠️ 多样歌词组合：灵活组合原文、译文、罗马音的歌词内容。
- 🔧 加密歌词支持：支持解析 QQ音乐(QRC)、酷狗音乐(KRC)、网易云音乐(YRC) 等加密歌词格式。
- 📱 自适应UI：根据系统主题自动调整界面颜色。

## 版本信息

| 项目            | 值                      |
|---------------|------------------------|
| 版本号           | 1.0.2 (versionCode: 3) |
| 最低 Android 版本 | Android 7.0 (API 24)   |
| 目标 Android 版本 | Android 15 (API 36)    |
| 发布日期          | 2026-03-12             |

## 技术栈

- 语言：Kotlin
- UI 框架：Jetpack Compose
- 架构：MVVM + 仓库模式 + UseCase
- 网络：OkHttp
- 异步：Kotlin Coroutines + Flow
- 依赖注入：Hilt
- 数据库：Room
- 图片加载：Coil
- 序列化：Kotlinx Serialization

## 项目结构

```
app/src/main/java/com/example/lddc/
├── LDDCApplication.kt          # 应用入口
├── MainActivity.kt              # 主Activity
├── common/                      # 通用模块
│   ├── models/                  # 数据模型
│   │   ├── enums/               # 枚举类
│   │   │   ├── Language.kt      # 语言
│   │   │   ├── LyricsFormat.kt  # 歌词格式
│   │   │   ├── LyricsType.kt    # 歌词类型
│   │   │   ├── SearchType.kt    # 搜索类型
│   │   │   └── Source.kt        # 音乐平台
│   │   ├── info/                # 信息模型
│   │   │   ├── AlbumInfo.kt     # 专辑信息
│   │   │   ├── Artist.kt        # 艺术家信息
│   │   │   ├── LyricInfo.kt     # 歌词信息
│   │   │   ├── PlaylistInfo.kt  # 播放列表信息
│   │   │   └── SongInfo.kt      # 歌曲信息
│   │   └── lyrics/              # 歌词模型
│   │       ├── Lyrics.kt        # 歌词数据
│   │       ├── LyricsLine.kt    # 歌词行
│   │       └── LyricsWord.kt    # 歌词字
│   └── utils/                   # 工具类
│       ├── AlbumArtLoader.kt    # 专辑封面加载
│       ├── PermissionUtils.kt   # 权限工具
│       └── TextUtils.kt         # 文本工具
├── core/                        # 核心功能
│   ├── api/                     # API实现
│   │   ├── base/                # 基础API
│   │   │   └── BaseLyricsApi.kt # 基础歌词API
│   │   ├── impl/                # 具体实现
│   │   │   ├── KugouApi.kt      # 酷狗音乐API
│   │   │   ├── NetEaseApi.kt    # 网易云音乐API
│   │   │   └── QQMusicApi.kt    # QQ音乐API
│   │   ├── LyricsApiManager.kt  # API管理器
│   │   └── NetEaseDeviceIds.kt  # 网易云设备ID
│   ├── decryptor/               # 解密器
│   │   ├── EapiDecryptor.kt     # EAPI解密
│   │   ├── KrcDecryptor.kt      # KRC解密
│   │   └── QrcDecryptor.kt      # QRC解密
│   └── parser/                  # 解析器
│       ├── KrcParser.kt         # KRC解析
│       ├── LrcParser.kt         # LRC解析
│       ├── LyricsParser.kt      # 歌词解析基类
│       ├── QrcParser.kt         # QRC解析
│       └── YrcParser.kt         # YRC解析
├── data/                        # 数据层
│   ├── local/                   # 本地数据
│   │   ├── database/            # 数据库
│   │   │   ├── dao/             # DAO
│   │   │   │   ├── LyricsCacheDao.kt      # 歌词缓存DAO
│   │   │   │   └── SearchHistoryDao.kt    # 搜索历史DAO
│   │   │   ├── entity/          # 实体类
│   │   │   │   ├── LyricsCacheEntity.kt   # 歌词缓存实体
│   │   │   │   └── SearchHistoryEntity.kt # 搜索历史实体
│   │   │   └── LDDCDatabase.kt  # 数据库
│   │   └── datastore/           # 数据存储
│   │       └── SettingsDataStore.kt # 设置数据存储
│   └── repository/              # 仓库
│       ├── LyricsRepository.kt      # 歌词仓库
│       ├── SearchHistoryRepository.kt # 搜索历史仓库
│       └── SettingsRepository.kt    # 设置仓库
├── di/                          # 依赖注入
│   └── AppModule.kt             # 应用模块
├── domain/                      # 领域层
│   ├── convert/                 # 转换
│   │   └── ConvertLyricsUseCase.kt # 转换歌词用例
│   ├── search/                  # 搜索
│   │   ├── ClearSearchHistoryUseCase.kt  # 清除搜索历史用例
│   │   ├── GetLyricsUseCase.kt          # 获取歌词用例
│   │   ├── GetSearchHistoryUseCase.kt   # 获取搜索历史用例
│   │   └── SearchSongsUseCase.kt        # 搜索歌曲用例
│   └── settings/                # 设置
│       ├── GetSettingsUseCase.kt       # 获取设置用例
│       └── UpdateSettingsUseCase.kt    # 更新设置用例
├── presentation/                # 表现层
│   ├── components/              # 组件
│   │   ├── common/              # 通用组件
│   │   │   ├── EmptyState.kt    # 空状态
│   │   │   ├── ErrorMessage.kt  # 错误信息
│   │   │   └── LoadingIndicator.kt # 加载指示器
│   │   ├── designsystem/        # 设计系统
│   │   │   ├── LDDCButton.kt    # 按钮
│   │   │   ├── LDDCCard.kt      # 卡片
│   │   │   ├── LDDCChip.kt      # 芯片
│   │   │   ├── LDDCInput.kt     # 输入框
│   │   │   ├── LDDCListItem.kt  # 列表项
│   │   │   └── LDDCState.kt     # 状态组件
│   │   ├── music/               # 音乐组件
│   │   │   ├── LocalMusicListItem.kt # 本地音乐列表项
│   │   │   └── SongListItem.kt  # 歌曲列表项
│   │   └── search/              # 搜索组件
│   │       └── SourceChip.kt    # 来源芯片
│   ├── screens/                 # 页面
│   │   ├── search/              # 搜索页面
│   │   │   ├── FilterDialog.kt  # 筛选对话框
│   │   │   ├── LyricsDetailScreen.kt # 歌词详情页面
│   │   │   ├── LyricsDetailViewModel.kt # 歌词详情ViewModel
│   │   │   ├── SearchFilters.kt # 搜索筛选
│   │   │   ├── SearchScreen.kt  # 搜索页面
│   │   │   └── SearchViewModel.kt # 搜索ViewModel
│   │   └── settings/            # 设置页面
│   │       ├── SettingsScreen.kt # 设置页面
│   │       └── SettingsViewModel.kt # 设置ViewModel
│   ├── theme/                   # 主题
│   │   ├── Color.kt             # 颜色
│   │   ├── Shape.kt             # 形状
│   │   ├── Theme.kt             # 主题
│   │   └── Type.kt              # 类型
│   └── viewmodel/               # ViewModel
│       └── BaseViewModel.kt     # 基础ViewModel
└── ui/                          # UI
    └── theme/                   # UI主题
        ├── Color.kt             # 颜色
        ├── Theme.kt             # 主题
        └── Type.kt              # 类型
```

## 安装说明

1. 克隆项目
   ```bash
   git clone https://github.com/adaozi/LDDC-Android.git
   ```

2. 在 Android Studio 中打开项目

3. 同步依赖并构建项目

4. 运行应用

## 许可证

本项目采用 MIT 许可证
## 更新日志

### v1.0.2 (2026-03-12)
- ✨ 添加翻译和罗马歌词的适配
- ✨ 添加设置页面
- ✨ 添加多种歌词形式
- 🎨 重置UI设计
- 🔧 修复编译错误
- 📦 清理项目结构，移除不必要文件

### v1.01 (2025-02-25)
- ✨ 新增单曲修改功能
- ✨ 新增一键匹配功能
- ✨ 新增加载更多选项
- 🎨 优化UI界面设计
- 📱 添加横屏适配
- 🔧 修复多个已知Bug

### v1.0.0
- 🎨 初始版本发布
- 📱 基本UI界面
- 🔍 基本搜索功能
