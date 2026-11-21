#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从前八十回正文提取语言基线指标。

用法:
    python tools/build_baseline.py corpus/ data/baseline.json        # 推荐：已剔注释
    python tools/build_baseline.py <hongloumeng.epub> data/baseline.json  # 旧法，含注释，勿用

产出 JSON 供 polish.py / check_style.py 读取，指标口径见 docs/METHOD.md。
"""
import json
import os
import re
import statistics
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CN = "一二三四五六七八九十百"
PARTICLES = ["罢", "吧", "啊", "吗", "呢"]
MARKERS = ["便", "一面", "竟", "竟然", "居然", "地", "得", "的话", "一会", "结果"]


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


def front80(text):
    marks = list(re.finditer(r"^第([" + CN + r"]{1,5})回(.*)$", text, re.M))
    best = {}
    for i, m in enumerate(marks):
        n = cn2int(m.group(1))
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start():end]
        if 1 <= n <= 80 and len(body) > 2000:
            if n not in best or len(body) > len(best[n]):
                best[n] = body
    return "\n".join(best[k] for k in sorted(best)), len(best)


def sent_len(text):
    sents = [s for s in re.split(r"[。！？；]", text) if len(s.strip()) > 2]
    return statistics.mean(len(s) for s in sents)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    if os.path.isdir(src):
        from corpus import load_corpus
        text, nch = load_corpus(src)
        source_note = "corpus/ 分回正文（已剔注释与校记）"
    else:
        text, nch = front80(load_epub(src))
        source_note = "epub 原文（含注释，密度指标会被稀释，不推荐）"
        print("警告：从 epub 直读会把 19.1%% 注释算进正文，密度指标系统性偏低。请改用 corpus/。")
    total = len(text.replace("\n", ""))  # 口径：不含换行符，与文档一致

    def rate(word):
        return round(text.count(word) / total * 10000, 3)

    p_counts = {p: text.count(p) for p in PARTICLES}
    p_total = sum(p_counts.values())
    zm = text.count("咱们")

    baseline = {
        "edition": "人民文学出版社《红楼梦》 中国艺术研究院红楼梦研究所校注（彩皮定本）",
        "scope": "前八十回正文",
        "source": source_note,
        "chapter_units": nch,
        "chars": total,
        "particles": {
            "counts": p_counts,
            "share": {k: round(v / p_total, 4) for k, v in p_counts.items()},
            "per_10k": {k: rate(k) for k in PARTICLES},
        },
        "markers_per_10k": {m: rate(m) for m in MARKERS},
        "single_zan_per_10k": round((text.count("咱") - zm) / total * 10000, 3),
        "avg_sentence_len": round(sent_len(text), 2),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    print(json.dumps(baseline, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
