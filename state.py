"""断点续传状态管理

在目标目录下维护 .lyricgeter.json 状态文件，
记录批量处理进度，支持退出后恢复。

仅用于目录批量处理；单文件处理不启用状态机制。
"""

from __future__ import annotations

import json
from pathlib import Path

STATE_FILENAME = ".lyricgeter.json"


class BatchState:
    """管理单次批处理的进度状态。

    状态文件位于目标目录下，记录已处理文件的相对路径集合。
    每处理完一个文件后立即保存，保证随时退出不丢进度。
    全部完成后自动清除状态文件。
    """

    def __init__(self, target_dir: Path):
        self.target_dir = Path(target_dir)
        self.state_file = self.target_dir / STATE_FILENAME
        self.processed: set[str] = set()
        self.total: int = 0

    def exists(self) -> bool:
        """状态文件是否存在。"""
        return self.state_file.exists()

    def load(self) -> None:
        """从文件加载状态。损坏时静默忽略并从零开始。"""
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.processed = set(data.get("processed", []))
            self.total = data.get("total", 0)
        except (json.JSONDecodeError, OSError):
            self.processed = set()
            self.total = 0

    def init(self, total: int) -> None:
        """初始化全新批处理状态。"""
        self.total = total
        self.processed = set()
        self.save()

    def save(self) -> None:
        """写入状态文件。"""
        data = {
            "total": self.total,
            "processed": sorted(self.processed),
        }
        self.state_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def rel_path(self, file_path: Path) -> str:
        """获取文件相对于目标目录的路径，用于存储和比较。"""
        try:
            return str(file_path.resolve().relative_to(self.target_dir.resolve()))
        except ValueError:
            return str(file_path)

    def is_processed(self, rel: str) -> bool:
        """检查文件是否已处理。"""
        return rel in self.processed

    def mark_processed(self, rel: str) -> None:
        """标记文件为已处理并立即保存。"""
        self.processed.add(rel)
        self.save()

    def clear(self) -> None:
        """删除状态文件（批处理全部完成时调用）。"""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except OSError:
                pass

    @property
    def processed_count(self) -> int:
        return len(self.processed)
