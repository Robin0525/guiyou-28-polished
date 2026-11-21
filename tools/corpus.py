#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语料装载工具：校注本 epub 与本地分回 md 共用。"""
import glob
import os
import re
import zipfile

CN = "一二三四五六七八九十百"


def strip_tags(html):
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", "", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</p>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", "", html)
    for a, b in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')]:
        html = html.replace(a, b)
    return html


def cn2int(s):
    d = {c: i for i, c in enumerate("〇一二三四五六七八九")}
    d["零"] = 0
    s = s.strip()
    # 逐位数字串：一一九→119、一〇八→108
    if s and all(c in d for c in s) and not re.search(r"[十百]", s):
        return int("".join(str(d[c]) for c in s))
    if "百" in s:
        a, _, b = s.partition("百")
        return (d.get(a, 1) if a else 1) * 100 + (cn2int(b) if b else 0)
    if "十" in s:
        a, _, b = s.partition("十")
        return (d.get(a, 1) if a else 1) * 10 + (d.get(b, 0) if b else 0)
    return d.get(s[0], 0) if s else 0


def load_epub(path):
    z = zipfile.ZipFile(path)
    buf = []
    for name in sorted(n for n in z.namelist() if n.endswith((".xhtml", ".html"))):
        try:
            buf.append(strip_tags(z.read(name).decode("utf-8", "ignore")))
        except Exception:
            continue
    text = "\n".join(buf)
    text = re.sub(r"[ \t\u3000]+", "", text)
    return re.sub(r"\n{2,}", "\n", text)


def front80(text, lo=1, hi=80):
    marks = list(re.finditer(r"^第([" + CN + r"]{1,5})回(.*)$", text, re.M))
    best = {}
    for i, m in enumerate(marks):
        n = cn2int(m.group(1))
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start():end]
        if lo <= n <= hi and len(body) > 2000:
            if n not in best or len(body) > len(best[n]):
                best[n] = body
    return "\n".join(best[k] for k in sorted(best)), len(best)


def load_dir(d):
    out = []
    for f in sorted(glob.glob(os.path.join(d, "ch*.md"))):
        t = open(f, encoding="utf-8").read()
        out.append(re.sub(r"^---[\s\S]*?---", "", t, count=1))
    return "\n".join(out)


def load_corpus(d):
    """读取 split_chapters.py 产出的分回正文（已剔注释与校记）。

    这是唯一的正文口径来源：753,918 字含 19.1% 注释，用它算基线会把
    所有密度指标稀释，是不可用的。
    """
    out = []
    for f in sorted(glob.glob(os.path.join(d, "h*.txt"))):
        lines = open(f, encoding="utf-8").read().split("\n")
        out.append("\n".join(lines[1:]))  # 首行是回目，不入正文
    return "\n".join(out), len(out)
