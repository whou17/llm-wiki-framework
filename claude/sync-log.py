#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone

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
    files = set()
    for root, dirs, filenames in os.walk("raw"):
        for f in filenames:
            if f.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, f), "raw")
                files.add(rel_path)
    return files


def load_log():
    with open(LOG_FILE, 'r') as f:
        return json.load(f)


def save_log(log):
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


def mark_learned(file_paths):
    """将指定文件标记为已学习。

    Args:
        file_paths: raw/ 下的相对路径列表，如 ["policy/xxx.md", "sources/yyy.md"]

    每个文件在 learning-log.json 中新增或更新条目：
    - 首次标记：创建 learned=true, learned-at=<now>, status=completed
    - 重复标记：仅更新 learned-at 时间戳
    """
    log = load_log()
    now = datetime.now(timezone.utc).isoformat()
    updated = 0
    skipped = 0
    missing = []

    for path in file_paths:
        # 验证文件存在
        full_path = os.path.join("raw", path)
        if not os.path.exists(full_path):
            missing.append(path)
            continue

        if path in log['entries']:
            entry = log['entries'][path]
            if entry.get('status') == 'completed':
                skipped += 1
                # 更新时间戳
                entry['learned-at'] = now
            else:
                entry['learned'] = True
                entry['learned-at'] = now
                entry['status'] = 'completed'
                updated += 1
        else:
            log['entries'][path] = {
                'learned': True,
                'learned-at': now,
                'status': 'completed'
            }
            updated += 1

    # 更新统计
    actual = get_actual_files()
    log['total-files'] = len(actual)
    log['learned-count'] = sum(
        1 for e in log['entries'].values()
        if isinstance(e, dict) and e.get('status') == 'completed'
    )
    log['last-learn'] = now
    log['last-scan'] = now

    save_log(log)

    # 输出结果
    if updated > 0:
        print(f"✅ 已标记 {updated} 个文件为已完成")
    if skipped > 0:
        print(f"⏭  {skipped} 个文件已标记过（仅更新时间戳）")
    if missing:
        print(f"❌ {len(missing)} 个文件不存在于 raw/ 中:")
        for m in missing:
            print(f"   - {m}")

    return updated, skipped, missing


def _find_relocations(new_files, deleted_files, log):
    """检测搬迁文件：被删文件在新路径出现时，转移学习记录而非删除。

    匹配规则：基文件名（不含目录部分）相同即视为搬迁。
    """
    new_basenames = {}
    for f in new_files:
        base = os.path.basename(f)
        if base not in new_basenames:
            new_basenames[base] = []
        new_basenames[base].append(f)

    relocations = {}  # old_path -> new_path
    still_deleted = []

    for f in deleted_files:
        base = os.path.basename(f)
        if base in new_basenames:
            # 取第一个匹配的新路径（同一基名应只有一个）
            relocations[f] = new_basenames[base][0]
        else:
            still_deleted.append(f)

    return relocations, still_deleted


def sync():
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

    # === 搬迁检测：先于清理执行 ===
    relocations, still_deleted = _find_relocations(new_files, deleted_files, log)
    relocation_count = len(relocations)

    if relocations:
        print(f"\n📦 检测到 {relocation_count} 个搬迁文件（基名匹配，转移学习记录）:")
        for old_path, new_path in sorted(relocations.items()):
            print(f"   {old_path[:50]}... → {new_path[:50]}...")
            # 转移记录：保留原有学习状态，更新路径
            log['entries'][new_path] = log['entries'].pop(old_path)
            # 从 new_files 中移除（不再视为新增未记录）
            new_files.discard(new_path)

    if still_deleted:
        for f in still_deleted:
            del log['entries'][f]
        log['total-files'] = len(actual)
        log['learned-count'] = len(actual) - len(new_files)
        log['last-scan'] = datetime.now().isoformat() + 'Z'
        save_log(log)
        print(f"\n已清理 {len(still_deleted)} 条过期记录")
    elif relocations:
        # 有搬迁但无其他删除，仍需保存
        log['total-files'] = len(actual)
        log['learned-count'] = len(actual) - len(new_files)
        log['last-scan'] = datetime.now().isoformat() + 'Z'
        save_log(log)
        print(f"\n（已保存搬迁记录）")

    if not new_files and not still_deleted and not shells:
        print("\n状态: 完全同步")
    elif not new_files and not still_deleted:
        print("\n状态: 同步一致（有空壳待处理）")

    return {
        'new': sorted(new_files),
        'deleted': sorted(still_deleted),
        'relocations': [(old, new) for old, new in sorted(relocations.items())],
        'matched': len(matched),
        'shells': [(rel, size, reason) for rel, size, reason in shells],
    }


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == '--mark-learned':
        # 用法: python3 .claude/sync-log.py --mark-learned "policy/xxx.md" "sources/yyy.md"
        file_paths = sys.argv[2:]
        if not file_paths:
            print("用法: python3 .claude/sync-log.py --mark-learned <file1> [file2 ...]")
            print("示例: python3 .claude/sync-log.py --mark-learned \"policy/xxx.md\" \"sources/yyy.md\"")
            sys.exit(1)
        mark_learned(file_paths)
    else:
        sync()
