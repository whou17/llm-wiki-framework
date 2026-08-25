#!/bin/bash
# docx 导出后验证脚本 — 检查行间距和引号
# 用法: bash .claude/scripts/docx-validate.sh <docx文件路径>
# 必须在 docx skill 环境中运行（依赖 unpack.py）

set -e
DOCX="$1"
if [ -z "$DOCX" ]; then
    echo "用法: bash .claude/scripts/docx-validate.sh <docx文件路径>"
    exit 1
fi

TMPDIR="/tmp/docx_validate_$$"
UNPACK_SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/skills/docx/scripts/office/unpack.py"

echo "=== docx 导出验证: $(basename "$DOCX") ==="

# 1. 解包
python3 "$UNPACK_SCRIPT" "$DOCX" "$TMPDIR" 2>&1 | tail -1
XML="$TMPDIR/word/document.xml"

# 2. 行间距检查
TOTAL=$(grep -o '<w:spacing' "$XML" | wc -l | tr -d ' ')
EXACT=$(grep -o 'w:lineRule="exact"' "$XML" | wc -l | tr -d ' ')
echo ""
echo "--- 行间距 ---"
echo "总段落数: $TOTAL"
echo "固定值(exact): $EXACT"
if [ "$TOTAL" -gt 0 ] && [ "$EXACT" -eq "$TOTAL" ]; then
    echo "✅ PASS: 全部 $TOTAL 段均为固定值 28 磅"
else
    echo "❌ FAIL: $TOTAL 段中仅 $EXACT 段为固定值，差 $((TOTAL - EXACT)) 段"
fi

# 3. 引号检查
LEFT=$(grep -o '&#x201C;' "$XML" | wc -l | tr -d ' ')
RIGHT=$(grep -o '&#x201D;' "$XML" | wc -l | tr -d ' ')
ASCII_Q=$(grep -o '&quot;' "$XML" | wc -l | tr -d ' ')
echo ""
echo "--- 引号 ---"
echo "全角左引号 “: $LEFT"
echo "全角右引号 ”: $RIGHT"
echo "半角 &quot;: $ASCII_Q"
if [ "$LEFT" -eq "$RIGHT" ] && [ "$ASCII_Q" -eq 0 ]; then
    echo "✅ PASS: $LEFT 对全角引号，零处半角"
elif [ "$ASCII_Q" -gt 0 ]; then
    echo "❌ FAIL: 存在 $ASCII_Q 处半角引号"
else
    echo "❌ FAIL: 引号不配对 ($LEFT vs $RIGHT)"
fi

# 4. 总结
echo ""
if [ "$TOTAL" -gt 0 ] && [ "$EXACT" -eq "$TOTAL" ] && [ "$LEFT" -eq "$RIGHT" ] && [ "$ASCII_Q" -eq 0 ]; then
    echo "=== 🟢 全部通过 ==="
else
    echo "=== 🔴 存在问题，请修复后重新导出 ==="
fi

rm -rf "$TMPDIR"
