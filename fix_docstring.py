# -*- coding: utf-8 -*-
"""修复 ui.py 中 _is_header_line / _detect_leading_non_lyric 的中文弯引号引发的 docstring 不闭合。"""
import io

path = "ui.py"
src = open(path, encoding="utf-8").read()

# 定位要替换的块：从 def _is_header_line 开始，直到 _detect_leading_non_lyric 函数体结束、下一个空行后 def _render_strip_frame 之前
start_marker = "def _is_header_line(text: str) -> bool:"
end_marker = "def _render_strip_frame(lines: list[str], n: int, detected_n: int, n_total: int) -> None:"

start = src.index(start_marker)
end = src.index(end_marker)

new_block = '''def _is_header_line(text: str) -> bool:
    """判断单行是否为歌词前的「非歌词」内容。

    包含：空行、注释/分隔行（//、#、--）、元数据关键词行、
    纯音乐提示、以及以冒号结尾的短身份标注行（如「演唱者：」）。
    """
    stripped = _INLINE_TS_RE.sub("", text).strip()
    if not stripped:
        return True  # 空行在头部块里允许存在
    # 注释 / 分隔行
    if stripped.startswith("//") or stripped.startswith("#"):
        return True
    if stripped in ("--", "---"):
        return True
    if _PURE_MUSIC_RE.search(stripped):
        return True
    if len(stripped) > 80:
        return False
    if any(kw in stripped for kw in _METADATA_KEYWORDS):
        return True
    # 中文以冒号结尾的短身份标注行（如「演唱者：」「Vocals：」）
    if stripped.endswith(("：", ":")) and len(stripped) < 40:
        return True
    return False


def _detect_leading_non_lyric(lines: list[str]) -> int:
    """返回从开头连续的非歌词行数，作为交互式去除的初始建议。

    会进行一次前瞻：若开头某行本身不判为非歌词，但紧随其后又有非歌词行
    （如标题行后面跟着 // 注释），把中间这个疑似标题行一并计入。
    """
    n = 0
    i = 0
    while i < len(lines):
        text = lines[i].strip()
        if _is_header_line(text):
            n += 1
            i += 1
            continue
        # 若仍在前 3 行内，且后面几行里有非歌词行，
        # 认为这个是被定位为标题的歌词行，一并去除
        if i < 3:
            ahead = [lines[j].strip() for j in range(i + 1, min(i + 4, len(lines)))]
            ahead_nonempty = [t for t in ahead if t]
            if ahead_nonempty and _is_header_line(ahead_nonempty[0]):
                n += 1
                i += 1
                continue
        break
    return n


'''

new_src = src[:start] + new_block + src[end:]

with io.open(path, "w", encoding="utf-8", newline="") as f:
    f.write(new_src)

print("Patched. New length:", len(new_src))
