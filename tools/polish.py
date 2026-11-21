#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""癸酉本后 28 回 · 行文规则润色器

只改行文；回目与诗词由 protect 机制硬保护，永不参与替换。

用法:
    python tools/polish.py source/ drafts/ [--report data/changes.json]
"""
import argparse
import glob
import json
import os
import re
import sys

LEXICON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lexicon.tsv")

VERSE_START = re.compile(r"(诗云|词曰|回前批|批语|联句|对句|口号|偈子|西江月)")
PROSE_START = re.compile(r"^(话说|且说|却说|原来|只见|如今|看官|不在话下|且说)")
DIALOG_VERB = re.compile(r"[说道问答笑骂哭喊嚷叫叹]")


def load_rules(path=LEXICON):
    rules = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            rid, cat, pat, rep = parts[0], parts[1], parts[2], parts[3]
            note = parts[4] if len(parts) > 4 else ""
            risk = parts[5] if len(parts) > 5 else "L"
            rules.append({"id": rid, "cat": cat, "pat": re.compile(pat), "rep": rep,
                          "note": note, "risk": risk})
    return rules


def is_verse_line(s):
    """短句分行型诗词判定（保守：宁可多保护）。"""
    s = s.strip()
    if len(s) < 7 or len(s) > 60:
        return False
    if DIALOG_VERB.search(s):
        return False
    if re.match(r"^[“「『]", s) or "“" in s or "‘" in s:
        return False
    core = s.strip("。！？；…")
    segs = [x for x in re.split(r"[，、；：]", core) if x]
    if len(segs) < 2:
        return False
    lens = [len(x) for x in segs]
    if not all(3 <= n <= 8 for n in lens):
        return False
    return sum(1 for n in lens if n in (5, 7)) >= max(1, len(lens) - 1)


def split_doc(text):
    m = re.match(r"^---\n([\s\S]*?)\n---\n+", text)
    meta = m.group(1) if m else ""
    body = text[m.end():] if m else text
    lines = body.split("\n")
    title = ""
    if lines and lines[0].startswith("# "):
        title = lines[0]
        lines = lines[1:]
    return meta, title, lines


def polish_lines(lines, rules):
    flags, in_verse = [], False
    for l in lines:
        s = l.strip()
        if s.startswith("#"):
            flags.append(True)
            continue
        # 对话行一律退出诗词保护态：诗词里不会有引号对白
        if PROSE_START.match(s) or len(s) > 120 or "“" in s or "‘" in s:
            in_verse = False
        elif VERSE_START.search(s) or is_verse_line(s):
            in_verse = True
        flags.append(in_verse)

    out, hits = [], {}
    for l, prot in zip(lines, flags):
        if prot or not l.strip():
            out.append(l)
            continue
        for r in rules:
            new, n = r["pat"].subn(r["rep"], l)
            if n:
                hits[r["id"]] = hits.get(r["id"], 0) + n
                l = new
        out.append(l)
    return out, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srcdir")
    ap.add_argument("outdir")
    ap.add_argument("--report", default="data/changes.json")
    a = ap.parse_args()

    rules = load_rules()
    os.makedirs(a.outdir, exist_ok=True)
    total, per_ch = {}, {}
    files = sorted(glob.glob(os.path.join(a.srcdir, "ch*.md")))
    for f in files:
        text = open(f, encoding="utf-8").read()
        meta, title, lines = split_doc(text)
        new_lines, hits = polish_lines(lines, rules)
        for k, v in hits.items():
            total[k] = total.get(k, 0) + v
        per_ch[os.path.basename(f)] = hits
        meta2 = meta.replace("来源:", "状态: 规则初稿（诗词、回目未改动）\n来源:")
        out = "---\n%s\n---\n\n%s\n\n%s\n" % (meta2, title, "\n".join(new_lines).strip())
        with open(os.path.join(a.outdir, os.path.basename(f)), "w", encoding="utf-8") as fh:
            fh.write(out)
        print("%s  替换 %d 处" % (os.path.basename(f), sum(hits.values())))

    os.makedirs(os.path.dirname(a.report) or ".", exist_ok=True)
    with open(a.report, "w", encoding="utf-8") as fh:
        json.dump({"total": total, "per_chapter": per_ch}, fh, ensure_ascii=False, indent=2)
    print("\n合计 %d 处；按规则：" % sum(total.values()))
    for k in sorted(total, key=lambda x: -total[x]):
        print("  %-4s %5d  %s" % (k, total[k], next(r["note"] for r in rules if r["id"] == k)))


if __name__ == "__main__":
    main()
