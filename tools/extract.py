#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PDF 抽取癸酉本后 28 回，切分为单回 Markdown。

用法:
    python tools/extract.py <guiyou.pdf> source/

依赖任一: pypdf / PyMuPDF / 命令行 workbuddy-pdf
"""
import os
import re
import subprocess
import sys
import tempfile

CN_NUM = "〇一二三四五六七八九"


def pdf_to_text(pdf_path):
    for mod in ("fitz", "pypdf", "pdfminer"):
        try:
            __import__(mod)
        except ImportError:
            continue
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(pdf_path).pages)
    except Exception:
        pass
    out = os.path.join(tempfile.mkdtemp(), "raw.txt")
    subprocess.run(["workbuddy-pdf", pdf_path, out, "--format", "txt"], check=True)
    return open(out, encoding="utf-8").read()


def clean(raw):
    keep = []
    for line in raw.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.fullmatch(r"\d{1,4}", s):                      # 页码
            continue
        if s.startswith("癸酉本石头记"):                       # 页眉
            continue
        if re.search(r"\.{5,}\s*\d+$", s):                    # 目录行
            continue
        keep.append(s)
    return "\n".join(keep)


def split_chapters(text):
    pat = re.compile(r"^第\s*(\d{1,3})\s*回\s*(.*)$", re.M)
    marks = list(pat.finditer(text))
    best = {}
    for i, m in enumerate(marks):
        n = int(m.group(1))
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start():end]
        if 81 <= n <= 108 and (n not in best or len(body) > len(best[n][1])):
            best[n] = (m.group(2).strip(), body)
    return best


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pdf_path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    chapters = split_chapters(clean(pdf_to_text(pdf_path)))
    for n in sorted(chapters):
        title, body = chapters[n]
        body = re.sub(r"^第\s*\d{1,3}\s*回\s*.*\n", "", body, count=1)
        # 去掉行内残留的页眉
        body = re.sub(r"癸酉本石头记[^\n]*\n", "", body)
        body = re.sub(r"\n{2,}", "\n", body).strip()
        path = os.path.join(outdir, "ch%03d.md" % n)
        with open(path, "w", encoding="utf-8") as f:
            f.write("---\n回次: %d\n回目: %s\n字数: %d\n来源: 《石头记癸酉本（后二十八回）三周年纪念版·凡第六版》，发布 何莉莉，整理 刘俊俊，2011-09\n---\n\n# 第%s回 %s\n\n%s\n"
                    % (n, title, len(body), _cn(n), title, body))
        print("ch%03d %s %d 字" % (n, title, len(body)))


def _cn(n):
    d = "〇一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n % 10] if n % 10 else "")
    if n < 100:
        return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")
    h, r = divmod(n, 100)
    s = ("" if h == 1 else d[h]) + "百"
    if r == 0:
        return s
    if r < 10:
        return s + "零" + d[r]
    return s + _cn(r)


if __name__ == "__main__":
    main()
