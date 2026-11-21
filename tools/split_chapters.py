#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把校注本 epub 拆成单回正文（剔除注释与校记），供逐回精读。

用法:
    python tools/split_chapters.py <hongloumeng.epub> corpus/
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus import cn2int, load_epub  # noqa: E402

CN = "一二三四五六七八九十百"


def strip_notes(text):
    keep = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\[\d{1,3}\]", s):          # 注释
            continue
        if re.match(r"^〔[一二三四五六七八九十]+〕", s):  # 校记
            continue
        keep.append(s)
    out = "\n".join(keep)
    # 行内残留的注号 [12]
    return re.sub(r"\[\d{1,3}\]", "", out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    epub, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    text = load_epub(epub)
    raw = list(re.finditer(r"^第([" + CN + r"]{1,5})回(.*)$", text, re.M))
    # 只认真标题：回目短且不含句读。正文里"第四回中既将薛家母子…"会被误判。
    marks = [m for m in raw
             if len(m.group(2)) <= 45 and not re.search(r"[，。；：、]", m.group(2))]
    best = {}
    for i, m in enumerate(marks):
        n = cn2int(m.group(1))
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start():end]
        if 1 <= n <= 80 and len(body) > 2000:
            if n not in best or len(body) > len(best[n][0]):
                best[n] = (body, m.group(2).strip())
    total = 0
    for n in sorted(best):
        body, title = best[n]
        body = re.sub(r"^第.*?回.*\n", "", body, count=1)
        body = strip_notes(body)
        path = os.path.join(outdir, "h%03d.txt" % n)
        with open(path, "w", encoding="utf-8") as f:
            f.write(title + "\n\n" + body)
        total += len(body.replace("\n", ""))
        print("h%03d %-28s %d 字" % (n, title, len(body.replace("\n", ""))))
    print("\n共 %d 个回次，正文 %d 字" % (len(best), total))
    missing = [i for i in range(1, 81) if i not in best]
    if missing:
        print("缺回次:", missing, "（第17、18回按底本未分回，属正常）")


if __name__ == "__main__":
    main()
