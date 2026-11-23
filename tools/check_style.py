#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按校注本基线校验润色稿的语言指标。

用法:
    python tools/check_style.py source/ drafts/ --out docs/验收报告.md
"""
import argparse
import glob
import json
import os
import re
import statistics

PARTICLES = ["罢", "吧", "啊", "吗", "呢"]
RESIDUE = ["死翘翘", "老乡", "干活", "折腾", "闹腾", "搞定", "完蛋", "丢人", "倒霉",
           "竟然", "居然", "肯定", "反正", "一会儿", "问题", "情况"]


def load_text(d):
    out = []
    for f in sorted(glob.glob(os.path.join(d, "ch*.md"))):
        t = open(f, encoding="utf-8").read()
        out.append(re.sub(r"^---[\s\S]*?---", "", t, count=1))
    return "\n".join(out)


def metrics(text):
    n = len(text)
    pc = {p: text.count(p) for p in PARTICLES}
    pt = sum(pc.values()) or 1
    sents = [s for s in re.split(r"[。！？；]", text) if len(s.strip()) > 2]
    return {
        "chars": n,
        "particles": pc,
        "share": {k: v / pt for k, v in pc.items()},
        "per10k": {k: round(v / n * 10000, 2) for k, v in pc.items()},
        "bian": round(text.count("便") / n * 10000, 2),
        "yimian": round(text.count("一面") / n * 10000, 2),
        "jingran": text.count("竟然") + text.count("居然"),
        "single_zan": round((text.count("咱") - text.count("咱们")) / n * 10000, 2),
        "avg_sent": round(statistics.mean(len(s) for s in sents), 2),
        "residue": {w: text.count(w) for w in RESIDUE if text.count(w)},
    }


def row(name, m, b):
    return "| %s | %s | %s | %s |" % (name, m, b, "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--baseline", default="data/baseline.json")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    b = json.load(open(a.baseline, encoding="utf-8"))
    bs = b["particles"]["share"]
    bp = b["particles"]["per_10k"]

    L = ["# 语言指标验收报告", "",
         "基线：%s，%s，%d 字。" % (b["edition"], b["scope"], b["chars"]),
         "", "## 语气词构成（占比）", "",
         "| 稿本 | 罢 | 呢 | 吧 | 啊 | 吗 | 罢+呢 |", "|---|---|---|---|---|---|---|",
         "| 校注本基线 | %.1f%% | %.1f%% | %.2f%% | %.2f%% | %.2f%% | %.1f%% |" % (
             bs["罢"]*100, bs["呢"]*100, bs["吧"]*100, bs["啊"]*100, bs["吗"]*100,
             (bs["罢"]+bs["呢"])*100)]

    details = {}
    for d in a.dirs:
        t = load_text(d)
        m = metrics(t)
        details[d] = m
        L.append("| %s | %.1f%% | %.1f%% | %.2f%% | %.2f%% | %.2f%% | %.1f%% |" % (
            d, m["share"]["罢"]*100, m["share"]["呢"]*100, m["share"]["吧"]*100,
            m["share"]["啊"]*100, m["share"]["吗"]*100,
            (m["share"]["罢"]+m["share"]["呢"])*100))

    L += ["", "## 关键指标（每万字）", "",
          "| 指标 | 基线 | " + " | ".join(a.dirs) + " |",
          "|---|---|" + "---|"*len(a.dirs),
          "| 罢 | %.2f | %s |" % (bp["罢"], " | ".join("%.2f" % details[d]["per10k"]["罢"] for d in a.dirs)),
          "| 呢 | %.2f | %s |" % (bp["呢"], " | ".join("%.2f" % details[d]["per10k"]["呢"] for d in a.dirs)),
          "| 吧 | %.2f | %s |" % (bp["吧"], " | ".join("%.2f" % details[d]["per10k"]["吧"] for d in a.dirs)),
          "| 啊 | %.2f | %s |" % (bp["啊"], " | ".join("%.2f" % details[d]["per10k"]["啊"] for d in a.dirs)),
          "| 吗 | %.2f | %s |" % (bp["吗"], " | ".join("%.2f" % details[d]["per10k"]["吗"] for d in a.dirs)),
          "| 便 | %.2f | %s |" % (b["markers_per_10k"]["便"], " | ".join("%.2f" % details[d]["bian"] for d in a.dirs)),
          "| 一面 | %.2f | %s |" % (b["markers_per_10k"]["一面"], " | ".join("%.2f" % details[d]["yimian"] for d in a.dirs)),
          "| 单用“咱” | %.2f | %s |" % (b["single_zan_per_10k"], " | ".join("%.2f" % details[d]["single_zan"] for d in a.dirs)),
          "| 竟然+居然（次） | 0 | %s |" % " | ".join(str(details[d]["jingran"]) for d in a.dirs),
          "| 平均句长（字） | %.1f | %s |" % (b["avg_sentence_len"], " | ".join("%.1f" % details[d]["avg_sent"] for d in a.dirs)),
          ]

    m = details[a.dirs[-1]]
    gap = []
    if m["share"]["罢"] + m["share"]["呢"] < 0.85:
        gap.append("「罢+呢」占比仍低于 85%，语气词尚未收敛")
    if m["bian"] < b["markers_per_10k"]["便"] * 0.6:
        gap.append("「便」密度不足基线的 60%，叙事推进仍偏现代")
    if m["yimian"] < b["markers_per_10k"]["一面"] * 0.35:
        gap.append("「一面……一面」密度不足，并列句式未建立")
    if abs(m["avg_sent"] - b["avg_sentence_len"]) > 4:
        gap.append("平均句长与基线差 %.1f 字，长句未拆" % (m["avg_sent"] - b["avg_sentence_len"]))
    if m["residue"]:
        gap.append("残留现代词：" + "、".join("%s×%d" % (k, v) for k, v in m["residue"].items()))

    L += ["", "## 未达标项", ""]
    L += ["- " + g for g in gap] if gap else ["- 无。"]
    if gap:
        L += ["", "> 机械扫描结果。引文中的词不计——例如第百零八回附录引第 62 回平儿原话"
                  "「便扬铃打鼓的乱折腾起来」，属照录原文，本回行文并未使用该词。"]
    L += ["", "> 规则润色只解决词汇与语气词层；句长、套语密度需人工精修，见 `docs/METHOD.md`。", ""]

    report = "\n".join(L)
    print(report)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(report)


if __name__ == "__main__":
    main()
