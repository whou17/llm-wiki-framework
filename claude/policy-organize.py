#!/usr/bin/env python3
"""
制度文件梳理工具 — Policy File Organization

功能：
1. 扫描 raw/policy/ 目录，统计文件行数，标记潜在空壳文件
2. 按关键词自动分类（党建/科研/育人/综合/财务）
3. 检测近似重复（同一制度不同来源的版本）
4. 提取文号
5. 生成重命名方案： [类型]-[序号]-[文号]-[名称].md

用法：在项目根目录运行 `python3 claude/policy-organize.py`
"""

import os, re
from collections import defaultdict

# === 分类关键词 ===
CAT_RULES = [
    ("党建", [
        "党章", "党员", "党组织", "党支部", "基层组织", "选举工作", "组织工作", "组织处理",
        "从严治党", "八项规定", "八项细则", "民主生活会", "主题教育",
        "意识形态", "思想政治工作", "思政工作", "思想政治理论课", "思政课",
        "马克思主义学院", "课程思政建设指导纲要",
        "党委领导下的校长负责制", "教职工代表大会", "学术委员会规程",
        "领导人员管理", "事业单位领导", "干部人事档案", "干部档案", "干部选拔",
        "党的建设", "党建工作标准", "党建工作重点", "党建示范", "双带头人",
        "政治建设", "政治巡察", "理论学习中心组",
        "廉政", "廉洁", "纪律处分", "发展党员", "党员教育", "监督谈话",
        "党委（党组）落实全面从严治党", "关于坚持和完善普通高等学校",
    ]),
    ("科研", [
        "科研", "科技", "创新", "成果转化", "科技成果", "专利", "知识产权",
        "产教融合", "产学合作", "产业学院", "校企合作", "产学研",
        "技术转移", "科技伦理", "新质生产力",
        "现代产业学院", "未来技术学院", "实习管理",
    ]),
    ("育人", [
        "学生", "教学", "课程", "本科教育", "人才培养", "专业认证", "专业设置",
        "学科专业", "师范类", "师范教育", "辅导员", "就业", "招生", "学位",
        "研究生", "硕士", "博士", "高等教育法",
        "教育评价", "教育数字化",
        "体育", "美育", "劳动教育", "传统文化教育", "国家安全教育",
        "阅读", "读书", "心理健康", "健康学校",
        "教师数字素养", "社会服务", "社区教育",
        "基础教育", "高中", "中小学", "规范汉字", "县域普通高中", "学生安全",
    ]),
    ("财务", [
        "国有资产", "行政事业性国有资产", "资产管理工作", "资产", "财务",
        "经费", "审计", "预算", "资金", "碳金融", "金融", "电子印章",
    ]),
]


def classify(filename: str) -> str:
    """按文件名关键词自动分类。无法匹配的归入'综合'。"""
    scores = defaultdict(int)
    for cat, keywords in CAT_RULES:
        for kw in keywords:
            if kw in filename:
                scores[cat] += 1
    return max(scores, key=scores.get) if scores else "综合"


def extract_year(filename: str) -> str:
    """从文件名提取年份。"""
    m = re.search(r'[〔(（](\d{4})[〕)）]', filename)
    if m: return m.group(1)
    m = re.search(r'(\d{4})\s*年', filename)
    if m: return m.group(1)
    m = re.search(r'^(\d{4})', filename)
    if m: return m.group(1)
    m = re.search(r'(\d{4})', filename)
    if m: return m.group(1)
    return "0000"


def extract_doc_number(filename: str) -> str:
    """从文件名提取文号。"""
    patterns = [
        (r'国办发\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '国办发'),
        (r'鲁政办字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁政办字'),
        (r'鲁政发\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁政发'),
        (r'鲁政字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁政字'),
        (r'中组发\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '中组发'),
        (r'鲁组发\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁组发'),
        (r'鲁组字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁组字'),
        (r'教党\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教党'),
        (r'教高厅\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教高厅'),
        (r'教高函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教高函'),
        (r'教高发\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教高发'),
        (r'教高字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教高字'),
        (r'教师函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教师函'),
        (r'教基厅\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教基厅'),
        (r'教思政\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教思政'),
        (r'教思字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教思字'),
        (r'鲁教厅办函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教厅办函'),
        (r'鲁教工委字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教工委字'),
        (r'鲁教工委函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教工委函'),
        (r'鲁教组字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教组字'),
        (r'鲁教组办函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教组办函'),
        (r'鲁教办函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教办函'),
        (r'鲁教师函\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁教师函'),
        (r'鲁科字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁科字'),
        (r'鲁人社字\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '鲁人社字'),
        (r'财资\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '财资'),
        (r'教育部令第(\d+)号', None),
        (r'国务院令第(\d+)号', None),
        (r'教师\s*[〔(（]\s*(\d{4})\s*[〕)）]\s*(\d+)\s*号', '教师'),
    ]
    for pat, prefix in patterns:
        m = re.search(pat, filename)
        if m:
            if prefix is None:
                return m.group(0).strip()
            try:
                return f"{prefix}〔{m.group(1)}〕{m.group(2)}号"
            except IndexError:
                return m.group(0).strip()
    return ""


def extract_short_name(f: str) -> str:
    """清理文件名：去掉来源后缀、日期前缀、序号前缀。"""
    n = f.replace('.md', '')
    n = re.sub(r'^\d+[-.]?\s*', '', n)
    n = re.sub(r'^\d{4}年\d{1,2}月\d{1,2}日\s*', '', n)
    n = re.sub(r'^\d{8}', '', n)
    # 来源后缀
    for s in [' - 中华人民共和国教育部政府门户网站', ' _中国政府网', ' _共产党员网',
              '_中央有关文件_中国政府网', '_国务院部门文件_中国政府网',
              '_滚动新闻_中国政府网', '_最新政策_中国政府网', '_中央文件_中国政府网',
              '_部门政务_中国政府网', '_国务院文件_中国政府网', '_教育_中国政府网',
              '_教育部_中国政府网', ' - 集标数字资源网', ' - 新华网',
              ' - 要闻信息-国家新闻出版署', ' - 政策法规-集标数字资源网',
              ' - 中央网络安全和信息化委员会办公室']:
        n = n.replace(s, '')
    # 前缀
    n = re.sub(r'^山东省教育厅\s+(?:其他文件|政策文件|通知公告|高等教育综合改革|鲁教发)\s+', '', n)
    n = re.sub(r'^山东省人民政府\s+其他文件\s+', '', n)
    n = re.sub(r'^\d+[-.]\d+[-.]?\d*\s*', '', n)
    n = re.sub(r'^附件1[：:]\s*', '', n)
    n = re.sub(r'^\d+\.', '', n)
    n = re.sub(r'^\d{4}年\d{1,2}月[，,]\s*', '', n)
    n = n.replace('###', '')
    n = re.sub(r'\s*[-]\s*副本$', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    n = n.replace('/', '-').replace('：', '-')
    if len(n) > 120:
        m = re.search(r'《([^》]+)》', n)
        if m and len(m.group(1)) > 10:
            prefix = n[:n.index('《')].strip()
            n = f"{prefix}《{m.group(1)}》"
    return n


def scan():
    """主扫描函数：分析 raw/policy/ 目录，输出分类和重命名方案。"""
    policy_dir = "raw/policy"
    if not os.path.isdir(policy_dir):
        print(f"[ERROR] {policy_dir}/ 目录不存在")
        return

    files = sorted([f for f in os.listdir(policy_dir) if f.endswith('.md')])
    print(f"\n=== {policy_dir}/ 制度文件扫描 ===\n")
    print(f"总文件数: {len(files)}")

    # 行数统计
    short_files = [(f, sum(1 for _ in open(os.path.join(policy_dir, f)))) for f in files]
    short_files = [(f, n) for f, n in short_files if n < 30]
    if short_files:
        print(f"\n⚠ 短文件 (<30 行): {len(short_files)}")
        for f, n in short_files:
            print(f"  [{n} 行] {f}")

    # 精确重复检测
    import hashlib
    hashes = defaultdict(list)
    for f in files:
        path = os.path.join(policy_dir, f)
        with open(path, 'rb') as fh:
            h = hashlib.md5(fh.read()).hexdigest()
        hashes[h].append(f)
    dup_groups = {h: fl for h, fl in hashes.items() if len(fl) > 1}
    if dup_groups:
        print(f"\n🔴 精确重复: {len(dup_groups)} 组")
        for h, fl in dup_groups.items():
            print(f"  {fl}")

    # 近似重复检测（同文件名含 " 1" 或 "(1)" 后缀）
    near_dups = []
    for f in files:
        if f.endswith(" 1.md") or f.endswith("(1).md"):
            base = f.replace(" 1.md", ".md").replace("(1).md", ".md")
            if base in files:
                near_dups.append((f, base))
    if near_dups:
        print(f"\n🟡 近似重复 (后缀版本): {len(near_dups)}")
        for dup, base in near_dups:
            print(f"  [删除] {dup}")
            print(f"  [保留] {base}")

    # 分类统计
    print(f"\n=== 分类统计 ===\n")
    classified = defaultdict(list)
    for f in files:
        cat = classify(f)
        year = extract_year(f)
        doc = extract_doc_number(f)
        classified[cat].append((f, year, doc))

    for cat in ["党建", "科研", "育人", "综合", "财务"]:
        items = sorted(classified[cat], key=lambda x: (x[1], x[0]))
        print(f"{cat}: {len(items)}")
        for i, (f, year, doc) in enumerate(items, 1):
            short = extract_short_name(f)
            doc_str = doc if doc else "无文号"
            new_name = f"{cat}-{i:02d}-{doc_str}-{short}.md"
            new_name = new_name.replace('//', '-')
            print(f"  {f}")
            print(f"    → {new_name}")

    # 汇总
    total = sum(len(v) for v in classified.values())
    print(f"\n=== 汇总 ===")
    print(f"总文件数: {total}")
    for cat in ["党建", "科研", "育人", "综合", "财务"]:
        print(f"  {cat}: {len(classified[cat])}")
    if short_files:
        print(f"短文件(需审核): {len(short_files)}")
    if dup_groups:
        print(f"精确重复组: {len(dup_groups)}")
    if near_dups:
        print(f"近似重复: {len(near_dups)}")


if __name__ == "__main__":
    scan()
