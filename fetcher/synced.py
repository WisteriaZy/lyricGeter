from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

import syncedlyrics

from .base import LyricFormat, LyricResult, LyricsFetcher

# 逐字判断：一行内出现两个或以上时间戳（中间夹文字）
_WORD_LEVEL_RE = re.compile(r"\[\d+:\d+\.\d+\][^\[\]]+\[\d+:\d+\.\d+\]")


def _detect_format(lrc: str) -> LyricFormat:
    for line in lrc.splitlines():
        if _WORD_LEVEL_RE.search(line):
            return LyricFormat.WORD
    if re.search(r"\[\d+:\d+\.\d+\]", lrc):
        return LyricFormat.LINE
    return LyricFormat.PLAIN


def _fetch(query: str, providers: list[str], enhanced: bool, lang: str | None) -> str | None:
    try:
        return syncedlyrics.search(
            query,
            providers=providers,
            enhanced=enhanced,
            lang=lang,
        )
    except Exception:
        return None


class SyncedLyricsFetcher(LyricsFetcher):
    """
    包装 syncedlyrics，支持逐字优先 + 翻译并行获取。

    providers: 默认 ["NetEase", "Lrclib"]
    lang: 翻译语言代码，如 "zh"；None 表示不获取翻译
          翻译仅 Musixmatch 支持，需在 providers 中显式加入且有 API key。
    """

    DEFAULT_PROVIDERS = ["NetEase"]
    # lang 参数只有 Musixmatch 支持
    TRANS_PROVIDERS = ["Musixmatch"]

    def __init__(
        self,
        providers: list[str] | None = None,
        lang: str | None = "zh",
    ) -> None:
        self.providers = providers or self.DEFAULT_PROVIDERS
        self.lang = lang
        self.trans_providers = [p for p in self.TRANS_PROVIDERS if p in self.providers]

    def search(self, title: str, artist: str) -> LyricResult | None:
        query = f"{title} {artist}".strip()

        # 并行：主歌词（enhanced=True，有逐字返回逐字，否则返回行级）+ 翻译
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_main = pool.submit(_fetch, query, self.providers, True, None)
            f_trans = (
                pool.submit(_fetch, query, self.trans_providers, False, self.lang)
                if self.lang and self.trans_providers
                else None
            )
            main_lrc = f_main.result()
            trans_lrc = f_trans.result() if f_trans else None

        if not main_lrc:
            return None

        fmt = _detect_format(main_lrc)

        return LyricResult(
            content=main_lrc,
            format=fmt,
            source_name="syncedlyrics",
            translation=trans_lrc if trans_lrc and trans_lrc != main_lrc else None,
        )
