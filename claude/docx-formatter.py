#!/usr/bin/env python3
"""
docx-formatter.py — Generate formatted Chinese official-document .docx from JSON manifest.

Usage:
  python3 docx-formatter.py manifest.json
  echo '{"paragraphs":[...]}' | python3 docx-formatter.py --stdin -o output.docx

The script reads a JSON manifest describing paragraph types, text content, and
tracked-change fixes, then produces a fully formatted .docx with:
  - A4 page, standard Chinese govt margins
  - Correct Chinese fonts (方正小标宋简体/黑体/楷体/仿宋)
  - 28pt exact line spacing, 2-char first-line indent on body/headings
  - Odd/even page numbers (宋体四号, "- N -" format)
  - OOXML tracked changes (<w:del>/<w:ins>) for content corrections
"""

import json
import sys
import os
import shutil
import copy
from pathlib import Path
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsmap
from docx.oxml import parse_xml, OxmlElement
from lxml import etree

# ── Constants ──────────────────────────────────────────────────────────────
WML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DATE_STAMP = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
AUTHOR = "Claude"

FONTS = {
    "title":    "方正小标宋简体",
    "subtitle": "楷体_GB2312",
    "author":   "楷体_GB2312",
    "h2":       "黑体",
    "h3":       "楷体_GB2312",
    "body":     "仿宋_GB2312",
    "empty":    "仿宋_GB2312",
    "page_number": "宋体",
}

SIZES_PT = {
    "title":    22,   # 二号
    "subtitle": 16,   # 三号
    "author":   16,
    "h2":       16,
    "h3":       16,
    "body":     16,
    "empty":    16,
    "page_number": 14,  # 四号
}

LINE_SPACING_PT = 28           # 28pt exact → OOXML: w:line="560" w:lineRule="exact"
# 单位换算: 1pt = 20 twips, 所以 28pt = 560 twips
# python-docx 的 Pt(28) 自动换算为 560 twips + lineRule="exact"
INDENT_CHARS = 2               # first-line indent in characters
INDENT_PT = INDENT_CHARS * 16  # = 32pt = 640 twips (2 × 16pt × 20)
# OOXML: w:ind w:firstLine="640"

# Tracking ID counter
_tc_id_counter = 0

def set_run_font_full(run, font_name):
    """Set font for ALL character sets (西文 + 中日韩 + 复杂脚本).

    CRITICAL: python-docx 的 run.font.name 只设置 w:ascii 和 w:hAnsi。
    必须额外设置 w:eastAsia 和 w:cs，否则中文字符回退到默认字体。
    """
    run.font.name = font_name  # 设置 w:ascii + w:hAnsi
    # 补充设置东亚字体
    rPr = run._element.find(qn('w:rPr'))
    if rPr is None:
        return
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        return
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:cs'), font_name)

def next_tc_id():
    global _tc_id_counter
    _tc_id_counter += 1
    return _tc_id_counter

# ── OOXML Helpers ──────────────────────────────────────────────────────────

def clone_run_props(rPr_elem):
    """Deep-clone a <w:rPr> element for use in tracked-change runs."""
    return copy.deepcopy(rPr_elem)

def make_run(rPr, text, nsmap_override=None):
    """Create a <w:r> element with run properties and text."""
    r = OxmlElement("w:r")
    if rPr is not None:
        r.append(clone_run_props(rPr))
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r

def make_del_run(rPr, text, tc_id):
    """Create a <w:del> containing a run with <w:delText>."""
    del_el = OxmlElement("w:del")
    del_el.set(qn("w:id"), str(tc_id))
    del_el.set(qn("w:author"), AUTHOR)
    del_el.set(qn("w:date"), DATE_STAMP)
    r = OxmlElement("w:r")
    if rPr is not None:
        r.append(clone_run_props(rPr))
    dt = OxmlElement("w:delText")
    dt.set(qn("xml:space"), "preserve")
    dt.text = text
    r.append(dt)
    del_el.append(r)
    return del_el

def make_ins_run(rPr, text, tc_id):
    """Create a <w:ins> containing a run with <w:t>."""
    ins_el = OxmlElement("w:ins")
    ins_el.set(qn("w:id"), str(tc_id))
    ins_el.set(qn("w:author"), AUTHOR)
    ins_el.set(qn("w:date"), DATE_STAMP)
    r = OxmlElement("w:r")
    if rPr is not None:
        r.append(clone_run_props(rPr))
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    ins_el.append(r)
    return ins_el

# ── Manifest Validation ────────────────────────────────────────────────────

VALID_TYPES = {"title", "subtitle", "author", "h2", "h3", "body", "empty"}
VALID_FIX_OPS = {"insert_after", "delete", "replace"}

def validate_manifest(m):
    """Validate and normalize the JSON manifest. Returns (ok, errors)."""
    errors = []
    if "paragraphs" not in m:
        errors.append("Missing 'paragraphs' key")
        return False, errors, []
    if not isinstance(m["paragraphs"], list):
        errors.append("'paragraphs' must be a list")
        return False, errors, []

    for i, p in enumerate(m["paragraphs"]):
        if not isinstance(p, dict):
            errors.append(f"P{i}: not a dict")
            continue
        ptype = p.get("type", "")
        if ptype not in VALID_TYPES:
            errors.append(f"P{i}: invalid type '{ptype}' (valid: {VALID_TYPES})")
        if ptype != "empty" and "text" not in p:
            errors.append(f"P{i}: missing 'text' for type '{ptype}'")

        fixes = p.get("fix", [])
        if fixes and not isinstance(fixes, list):
            errors.append(f"P{i}: 'fix' must be a list")
        for j, f in enumerate(fixes):
            if not isinstance(f, dict):
                errors.append(f"P{i} fix[{j}]: not a dict")
                continue
            op = f.get("op", "")
            if op not in VALID_FIX_OPS:
                errors.append(f"P{i} fix[{j}]: invalid op '{op}'")
            if "match" not in f:
                errors.append(f"P{i} fix[{j}]: missing 'match'")
            if op in ("insert_after", "replace") and "text" not in f:
                errors.append(f"P{i} fix[{j}]: op '{op}' requires 'text'")

    # Check for ASCII double quotes in Chinese text (should be full-width "")
    quote_warnings = []
    for i, p in enumerate(m["paragraphs"]):
        text = p.get("text", "")
        if '"' in text:
            quote_warnings.append(
                f"P{i}: ASCII 双引号 (U+0022) 出现在正文中，应替换为全角"
                f" “ (U+201C) 和 ” (U+201D)。"
                f" 如果这是 JSON 转义产生的 \"，请使用 Unicode 原字符。"
            )
    return len(errors) == 0, errors, quote_warnings

# ── Document Creation ──────────────────────────────────────────────────────

def create_document(manifest):
    """Create a python-docx Document from the manifest paragraphs."""
    doc = Document()

    # ── Page setup ──
    section = doc.sections[0]
    section.page_width  = Cm(21.0)   # A4 width
    section.page_height = Cm(29.7)   # A4 height
    # Use direct DXA values to avoid Cm→DXA rounding errors
    # 3.7cm=2098, 3.5cm=1985, 2.8cm=1588, 2.6cm=1474 (1 DXA = 1/1440 inch)
    section.top_margin    = Cm(3.7)    # → 2098 DXA
    section.bottom_margin = Cm(3.5)    # → 1985 DXA (python-docx rounds to 1984, acceptable)
    section.left_margin   = Cm(2.8)    # → 1588 DXA (python-docx rounds to 1587, acceptable)
    section.right_margin  = Cm(2.6)    # → 1474 DXA

    # ── Default paragraph format (for empty paragraphs) ──
    style = doc.styles["Normal"]
    style.font.name = FONTS["body"]
    style.font.size = Pt(SIZES_PT["body"])
    style.paragraph_format.line_spacing = Pt(LINE_SPACING_PT)

    # ── Paragraphs ──
    for pdata in manifest["paragraphs"]:
        ptype = pdata.get("type", "body")
        text = pdata.get("text", "")

        if ptype == "empty":
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = Pt(LINE_SPACING_PT)
            run = p.add_run("")
            set_run_font_full(run, FONTS[ptype])
            run.font.size = Pt(SIZES_PT[ptype])
            continue

        p = doc.add_paragraph()
        run = p.add_run(text)
        set_run_font_full(run, FONTS[ptype])
        run.font.size = Pt(SIZES_PT[ptype])

        # ── Alignment ──
        if ptype in ("title", "subtitle", "author"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif ptype == "body":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # h2, h3: left-aligned (default)

        # ── Spacing ──
        p.paragraph_format.line_spacing = Pt(LINE_SPACING_PT)

        # 段前/段后统一设为 "0 行"（用 beforeLines/afterLines 而非 before/after）
        # python-docx 的 space_before/space_after 生成的是 w:before/w:after (磅)，
        # 需要改为 w:beforeLines/w:afterLines (行)
        pPr = p._element.get_or_add_pPr()
        spacing = pPr.find(qn('w:spacing'))
        if spacing is None:
            spacing = OxmlElement('w:spacing')
            pPr.insert(0, spacing)
        spacing.set(qn('w:beforeLines'), '0')
        spacing.set(qn('w:afterLines'), '0')
        # 清除 python-docx 可能写入的磅值属性
        for attr in ['{'+WML_NS+'}before', '{'+WML_NS+'}after']:
            if attr in spacing.attrib:
                del spacing.attrib[attr]

        # ── Indentation ──
        if ptype in ("h2", "h3", "body"):
            p.paragraph_format.first_line_indent = Pt(INDENT_PT)

    return doc

# ── Tracked Changes ────────────────────────────────────────────────────────

def apply_fix_to_paragraph(p_elem, fix, tc_id):
    """
    Apply a single fix to a <w:p> element's text runs.
    Returns (success, error_message).
    """
    op = fix["op"]
    match = fix["match"]

    # Collect all <w:r> elements with <w:t> text
    runs = p_elem.findall(qn("w:r"))
    # Build a map of cumulative text positions across runs
    # For simplicity, we assume the fix applies within a single run
    # (which is always true for docx created by this script)

    for r_elem in runs:
        rPr = r_elem.find(qn("w:rPr"))
        t_elem = r_elem.find(qn("w:t"))
        if t_elem is None or t_elem.text is None:
            continue

        full_text = t_elem.text
        pos = full_text.find(match)
        if pos == -1:
            continue

        # Found the match in this run
        before = full_text[:pos]
        match_text = full_text[pos:pos + len(match)]
        after = full_text[pos + len(match):]

        parent = r_elem.getparent()
        idx = list(parent).index(r_elem)

        fragments = []

        if op == "insert_after":
            # before + match, then ins(new_text), then after
            combined = before + match_text
            if combined:
                new_r = make_run(rPr, combined)
                fragments.append(new_r)
            ins_text = fix.get("text", "")
            if ins_text:
                ins_el = make_ins_run(rPr, ins_text, tc_id)
                fragments.append(ins_el)
            if after:
                new_r2 = make_run(rPr, after)
                fragments.append(new_r2)

        elif op == "delete":
            if before:
                new_r = make_run(rPr, before)
                fragments.append(new_r)
            del_el = make_del_run(rPr, match_text, tc_id)
            fragments.append(del_el)
            if after:
                new_r2 = make_run(rPr, after)
                fragments.append(new_r2)

        elif op == "replace":
            if before:
                new_r = make_run(rPr, before)
                fragments.append(new_r)
            del_el = make_del_run(rPr, match_text, tc_id)
            fragments.append(del_el)
            new_text = fix.get("text", "")
            if new_text:
                ins_el = make_ins_run(rPr, new_text, tc_id + 1)
                fragments.append(ins_el)
            # Note: replace uses 2 IDs (del + ins). We return the last used ID.
            if after:
                new_r2 = make_run(rPr, after)
                fragments.append(new_r2)

        # Replace the original run with fragments
        for frag in reversed(fragments):
            parent.insert(idx + 1, frag)
        parent.remove(r_elem)
        return True, None

    return False, f"match '{match}' not found in paragraph text"

def apply_tracked_changes(doc, manifest):
    """Apply all tracked changes from the manifest to the document XML."""
    body = doc.element.body
    all_paras = body.findall(qn("w:p"))

    para_index = 0
    fixes_applied = 0
    errors = []

    for pdata in manifest["paragraphs"]:
        fixes = pdata.get("fix", [])
        if not fixes:
            para_index += 1
            continue

        if para_index >= len(all_paras):
            errors.append(f"P{para_index}: paragraph index out of range")
            para_index += 1
            continue

        p_elem = all_paras[para_index]

        for fix in fixes:
            tc_id = next_tc_id()
            ok, err = apply_fix_to_paragraph(p_elem, fix, tc_id)
            if ok:
                fixes_applied += 1
                # If it was a replace, we used 2 IDs
                if fix["op"] == "replace":
                    next_tc_id()  # consume the extra ID
            else:
                errors.append(f"P{para_index} fix({fix['op']} '{fix['match']}'): {err}")

        para_index += 1

    return fixes_applied, errors

# ── Section Properties Fix ─────────────────────────────────────────────────

def fix_section_properties(doc):
    """Add <w:evenAndOddHeaders/> and fix <w:pgNumType> in sectPr."""
    body = doc.element.body
    sectPr = body.find(qn("w:sectPr"))
    if sectPr is None:
        return False

    # Fix pgNumType
    pgNumType = sectPr.find(qn("w:pgNumType"))
    if pgNumType is not None:
        pgNumType.set(qn("w:fmt"), "decimal")
    else:
        pgNumType = OxmlElement("w:pgNumType")
        pgNumType.set(qn("w:fmt"), "decimal")
        # Insert before docGrid
        docGrid = sectPr.find(qn("w:docGrid"))
        if docGrid is not None:
            sectPr.insert(list(sectPr).index(docGrid), pgNumType)
        else:
            sectPr.append(pgNumType)

    # Add evenAndOddHeaders (must be last child of sectPr)
    eao = sectPr.find(qn("w:evenAndOddHeaders"))
    if eao is None:
        eao = OxmlElement("w:evenAndOddHeaders")
        sectPr.append(eao)

    return True

# ── Headers / Footers with Page Numbers ────────────────────────────────────

def setup_page_numbers(doc):
    """Add odd/even footers with page numbers (宋体四号, '- N -' format)."""
    for section in doc.sections:
        # Access internal sectPr
        sectPr = section._sectPr

        # We need to add footer references for odd/even pages
        # This requires creating footer XML files and relationships.
        # Since python-docx doesn't natively support even/odd footers easily,
        # we'll handle this at the XML level.

        # For now, add a default footer with page number
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.line_spacing = Pt(LINE_SPACING_PT)

        # Clear existing runs
        for r in p.runs:
            p._element.remove(r._element)

        # Build footer content: "- " + PAGE + " -"
        run1 = p.add_run("‐ ")  # U+2010 HYPHEN (not ASCII hyphen)
        set_run_font_full(run1, FONTS["page_number"])
        run1.font.size = Pt(SIZES_PT["page_number"])

        # PAGE field
        run_page = p.add_run()
        set_run_font_full(run_page, FONTS["page_number"])
        run_page.font.size = Pt(SIZES_PT["page_number"])
        # Insert PAGE field code
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        run_page._element.append(fld_begin)
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        run_page._element.append(instr)
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        run_page._element.append(fld_sep)
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run_page._element.append(fld_end)

        run2 = p.add_run(" ‐")  # U+2010 HYPHEN (not ASCII hyphen)
        set_run_font_full(run2, FONTS["page_number"])
        run2.font.size = Pt(SIZES_PT["page_number"])

# ── Even-Page Footer (ZIP post-processing) ─────────────────────────────────

def add_even_footer(output_path):
    """Post-process the saved docx to add an even-page footer (left-aligned).

    python-docx doesn't natively support even/odd footers, so we manipulate
    the .docx ZIP directly after saving.
    """
    import zipfile, io, re, shutil

    tmp_path = output_path + ".tmp"
    shutil.copy2(output_path, tmp_path)

    try:
        with zipfile.ZipFile(tmp_path, 'r') as zin:
            files = {name: zin.read(name) for name in zin.namelist()}

        # Locate the existing footer
        footer_names = sorted([n for n in files if n.startswith('word/footer') and n.endswith('.xml')])
        if not footer_names:
            return

        footer1_name = footer_names[0]
        footer1_xml = etree.fromstring(files[footer1_name])

        # Clone and change alignment to LEFT for even pages
        footer2_xml = copy.deepcopy(footer1_xml)
        jc = footer2_xml.find('.//{'+WML_NS+'}jc')
        if jc is not None:
            jc.set('{'+WML_NS+'}val', 'left')

        # Generate footer2 filename
        m = re.match(r'(word/footer)(\d+)(\.xml)', footer1_name)
        num = int(m.group(2)) if m else 1
        footer2_name = f'word/footer{num+1}.xml'

        files[footer2_name] = etree.tostring(footer2_xml, xml_declaration=True,
                                              encoding='UTF-8', standalone=True)

        # Update [Content_Types].xml
        ct_xml = etree.fromstring(files['[Content_Types].xml'])
        ct_ns = 'http://schemas.openxmlformats.org/package/2006/content-types'
        ov = etree.SubElement(ct_xml, '{'+ct_ns+'}Override')
        ov.set('PartName', '/' + footer2_name)
        ov.set('ContentType',
               'application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml')
        files['[Content_Types].xml'] = etree.tostring(ct_xml, xml_declaration=True,
                                                       encoding='UTF-8', standalone=True)

        # Update word/_rels/document.xml.rels
        rels_name = 'word/_rels/document.xml.rels'
        rels_xml = etree.fromstring(files[rels_name])
        rels_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
        max_id = 0
        for rel in rels_xml:
            rid = rel.get('Id', '')
            if rid.startswith('rId'):
                try: max_id = max(max_id, int(rid[3:]))
                except: pass
        new_rid = f'rId{max_id + 1}'
        nr = etree.SubElement(rels_xml, 'Relationship')
        nr.set('Id', new_rid)
        nr.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer')
        nr.set('Target', footer2_name.replace('word/', ''))
        files[rels_name] = etree.tostring(rels_xml, xml_declaration=True,
                                           encoding='UTF-8', standalone=True)

        # Update document.xml: add even footerReference to sectPr
        doc_xml = etree.fromstring(files['word/document.xml'])
        sectPr = doc_xml.find('.//{'+WML_NS+'}sectPr')
        if sectPr is not None:
            fr = etree.SubElement(sectPr, '{'+WML_NS+'}footerReference')
            fr.set('{'+WML_NS+'}type', 'even')
            fr.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', new_rid)
        files['word/document.xml'] = etree.tostring(doc_xml, xml_declaration=True,
                                                     encoding='UTF-8', standalone=True)

        # Write back
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for name, data in files.items():
                zout.writestr(name, data)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Main Pipeline ──────────────────────────────────────────────────────────

def run_pipeline(manifest, output_path):
    """Execute the full generation pipeline. Returns (success, report dict)."""
    report = {"steps": [], "errors": [], "fixes_applied": 0}

    # Step 0: Validate manifest
    ok, errs, quote_warnings = validate_manifest(manifest)
    if not ok:
        report["errors"].extend(errs)
        return False, report
    if quote_warnings:
        report["quote_warnings"] = quote_warnings
    report["steps"].append("validate")

    # Step 1: Create document
    doc = create_document(manifest)
    report["steps"].append("create")

    # Step 2: Apply tracked changes
    n_fixes, fix_errs = apply_tracked_changes(doc, manifest)
    report["fixes_applied"] = n_fixes
    report["errors"].extend(fix_errs)
    report["steps"].append("tracked_changes")

    # Step 3: Fix section properties
    fix_section_properties(doc)
    report["steps"].append("sectPr_fix")

    # Step 4: Setup page numbers
    setup_page_numbers(doc)
    report["steps"].append("page_numbers")

    # Step 5: Save
    doc.save(output_path)
    report["steps"].append("save")

    # Step 6: Add even-page footer (ZIP post-processing)
    add_even_footer(output_path)
    report["steps"].append("even_footer")

    return True, report

# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate formatted Chinese docx from JSON manifest")
    parser.add_argument("manifest", nargs="?", help="Path to JSON manifest file")
    parser.add_argument("--stdin", action="store_true", help="Read manifest from stdin")
    parser.add_argument("-o", "--output", default=None, help="Output .docx path")

    args = parser.parse_args()

    # Read manifest
    if args.stdin:
        manifest_str = sys.stdin.read()
    elif args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest_str = f.read()
    else:
        parser.print_help()
        sys.exit(1)

    try:
        manifest = json.loads(manifest_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    output_path = args.output or manifest.get("output", "output.docx")
    output_path = str(Path(output_path).with_suffix(".docx"))

    # Run pipeline
    ok, report = run_pipeline(manifest, output_path)

    # Report
    result = {
        "success": ok,
        "output": str(Path(output_path).absolute()),
        "fixes_applied": report["fixes_applied"],
        "steps": report["steps"],
        "errors": report["errors"],
    }
    if "quote_warnings" in report:
        result["quote_warnings"] = report["quote_warnings"]
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
