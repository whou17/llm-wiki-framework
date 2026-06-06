#!/usr/bin/env python3
"""
知识库同步检测脚本

功能：
1. 检测 raw/ 目录下新增/删除的 .md 文件
2. 扫描空壳文件（极小文件或含平台残留文字）
3. 与 learning-log.json 对账

用法：在项目根目录运行 `python3 claude/sync-log.py`
依赖：无第三方包，仅需 Python 3.6+
"""

import json
import os
from datetime import datetime

LOG_FILE = ".claude/learning-log.json"

# 空壳文件检测阈值（字节）
SHELL_SIZE_THRESHOLD = 500

# 平台残留特征（微信、头条等转载平台的文章 chrome 文字）
SHELL_PATTERNS = [
    "在小说阅读器读本章",
    "微信扫一扫",
    "使用小程序",
    "阅读原文",
    "继续滑动看下一个",
    "向上滑动看下一个",
    "知道了",
]


def get_actual_files():
    """扫描 raw/ 目录下所有 .md 文件"""
    files = set()
    if not os.path.isdir("raw"):
        print("[WARN] raw/ 目录不存在，创建空目录")
        os.makedirs("raw", exist_ok=True)
        return files
    for root, dirs, filenames in os.walk("raw"):
        for f in filenames:
            if f.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, f), "raw")
                files.add(rel_path)
    return files


def load_log():
    """加载学习记录，若文件不存在则返回空记录"""
    if not os.path.exists(LOG_FILE):
        print("[INFO] learning-log.json 不存在，初始化为空记录")
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        return {"entries": {}, "total-files": 0, "learned-count": 0, "last-scan": ""}
    with open(LOG_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("[WARN] learning-log.json 格式错误，重建空记录")
            return {"entries": {}, "total-files": 0, "learned-count": 0, "last-scan": ""}


def save_log(log):
    """保存学习记录"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def scan_shells():
    """检测 raw/ 下的疑似空壳文件。
    空壳 = 文件极小（<SHELL_SIZE_THRESHOLD 字节）或正文几乎全是平台残留文字。
    返回 [(相对路径, 字节数, 原因), ...]
    """
    shells = []
    for root, dirs, filenames in os.walk("raw"):
        for f in filenames:
            if not f.endswith('.md'):
                continue
            filepath = os.path.join(root, f)
            size = os.path.getsize(filepath)
            rel = os.path.relpath(filepath, "raw")

            if size < SHELL_SIZE_THRESHOLD:
                with open(filepath, 'r') as fh:
                    content = fh.read()
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                line_count = len(lines)

                # 原因1：极小文件（几乎无正文）
                if line_count <= 5:
                    shells.append((rel, size, f"仅 {line_count} 行正文"))
                    continue

                # 原因2：内容以平台残留为主
                shell_hits = [p for p in SHELL_PATTERNS if p in content]
                if shell_hits:
                    shells.append((rel, size, f"含平台残留: {shell_hits[:3]}"))

    return shells


def sync():
    """主流程：比对实际文件与记录，输出差异报告"""
    actual = get_actual_files()
    log = load_log()
    recorded = set(log['entries'].keys())

    new_files = actual - recorded
    deleted_files = recorded - actual
    matched = actual & recorded

    print("=" * 50)
    print("知识库同步检测")
    print("=" * 50)
    print(f"实际文件: {len(actual)}")
    print(f"记录数量: {len(recorded)}")
    print()

    # === 空壳文件检测 ===
    shells = scan_shells()
    if shells:
        print(f"⚠️  疑似空壳文件 ({len(shells)}):")
        for rel, size, reason in shells[:10]:
            print(f"   🐚 {rel[:60]}")
            print(f"      {size} bytes | {reason}")
        if len(shells) > 10:
            print(f"   ... 还有 {len(shells)-10} 个")
        print()

    if new_files:
        print(f"新增未记录 ({len(new_files)}):")
        for f in sorted(new_files)[:5]:
            print(f"   + {f[:50]}...")
        if len(new_files) > 5:
            print(f"   ... 还有 {len(new_files)-5} 个")
        print()

    if deleted_files:
        print(f"已删待清理 ({len(deleted_files)}):")
        for f in sorted(deleted_files)[:5]:
            print(f"   - {f[:50]}...")
        if len(deleted_files) > 5:
            print(f"   ... 还有 {len(deleted_files)-5} 个")
        print()

    if matched:
        print(f"已匹配: {len(matched)}")

    if deleted_files:
        for f in deleted_files:
            del log['entries'][f]
        log['total-files'] = len(actual)
        log['learned-count'] = len(actual) - len(new_files)
        log['last-scan'] = datetime.now().isoformat() + 'Z'
        save_log(log)
        print(f"\n已清理 {len(deleted_files)} 条过期记录")

    if not new_files and not deleted_files and not shells:
        print("\n状态: 完全同步")
    elif not new_files and not deleted_files:
        print("\n状态: 同步一致（有空壳待处理）")

    return {
        'new': sorted(new_files),
        'deleted': sorted(deleted_files),
        'matched': len(matched),
        'shells': [(rel, size, reason) for rel, size, reason in shells],
    }


if __name__ == "__main__":
    sync()
