#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用五层风格模型给任意文本打分，量化「离曹雪芹有多远」。

用法:
    python tools/style_distance.py source/ drafts/ polished/ --out docs/风格距离.md
"""
import argparse
import json
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_style_model import FRAMES, TAGS, sentences, dialogue, per10k  # noqa: E402
from corpus import load_dir  # noqa: E402

EPS = 0.05


def dev(a, b):
    """对数偏差，0 为完全一致。"""
    return abs(math.log((a + EPS) / (b + EPS)))


def analyse(text, model):
    n = len(text)
    L = model["layers"]
    sents = sentences(text)
    lens = [len(s) for s in sents]
    spans, dchars = dialogue(text)

    fw = {w: per10k(text.count(w), n) for w in L["L1_function_words_per_10k"]}

    frames = {}
    for layer, name, kind, val, note in FRAMES:
        cnt = text.count(val) if kind == "lit" else len(re.findall(val, text))
        frames[name] = per10k(cnt, n)

    tag_pat = "|".join(sorted(TAGS, key=len, reverse=True))
    tags = {}
    for m in re.finditer(r"(?P<tag>" + tag_pat + r")：“", text):
        tags[m.group("tag")] = tags.get(m.group("tag"), 0) + 1
    tags = {k: per10k(v, n) for k, v in tags.items()}

    bins = {"<=10": 0, "11-20": 0, "21-30": 0, "31-40": 0, ">40": 0}
    for x in lens:
        if x <= 10:
            bins["<=10"] += 1
        elif x <= 20:
            bins["11-20"] += 1
        elif x <= 30:
            bins["21-30"] += 1
        elif x <= 40:
            bins["31-40"] += 1
        else:
            bins[">40"] += 1
    tot = len(lens) or 1

    return {
        "chars": n,
        "fw": fw,
        "frames": frames,
        "tags": tags,
        "avg_sent": statistics.mean(lens) if lens else 0,
        "dialogue_ratio": dchars / n if n else 0,
        "sent_count": len(lens),
        "dist": {k: v / tot for k, v in bins.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--model", default="data/style_model.json")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    model = json.load(open(a.model, encoding="utf-8"))
    L = model["layers"]
    base_fw = L["L1_function_words_per_10k"]
    base_frames = L["L2_frames_per_10k"]
    base_tags = L["L3_dialogue_tags_per_10k"]

    res = {d: analyse(load_dir(d), model) for d in a.dirs}

    lines = ["# 风格距离报告", "",
             "基线：%s，%s，%d 字。" % (model["meta"]["edition"], model["meta"]["scope"], model["meta"]["chars"]),
             "偏离度 = 各特征 |ln(文本/基线)| 的均值，0 为完全一致。（高频）= 仅统计基线 ≥5/万 的特征，剔除稀疏噪声。",
             "**不同字数、不同范围的稿本不可横向比较**（1 回 vs 28 回，对白占比与稀疏特征都会失真）。", "",
             "## 总览", "",
             "| 稿本 | 字数 | 偏离度 | 偏离度(高频) | 对白占比 | 平均句长 | 句数 |",
             "|---|---|---|---|---|---|---|"]

    score, score_hi = {}, {}
    for d, r in res.items():
        ds, hi = [], []
        for w in base_fw:
            x = dev(r["fw"][w], base_fw[w])
            ds.append(x)
            if base_fw[w] >= 5:
                hi.append(x)
        ds += [dev(r["frames"][k], base_frames[k]) for k in base_frames if k in r["frames"]]
        hi += [dev(r["frames"][k], base_frames[k]) for k in base_frames
               if k in r["frames"] and base_frames[k] >= 1]
        ds += [dev(r["tags"].get(k, 0), v) for k, v in base_tags.items()]
        hi += [dev(r["tags"].get(k, 0), v) for k, v in base_tags.items() if v >= 5]
        e = dev(r["avg_sent"], L["L4_sentence"]["avg"])
        o = dev(r["dialogue_ratio"], L["L5_voice"]["dialogue_ratio"])
        ds += [e, o]
        hi += [e, o]
        score[d] = statistics.mean(ds)
        score_hi[d] = statistics.mean(hi)

    for d, r in res.items():
        mark = "%.2f" % score[d] if r["chars"] >= 20000 else "—"
        markhi = "**%.2f**" % score_hi[d] if r["chars"] >= 20000 else "**%.2f**（样本 1 万字，仅供参考）" % score_hi[d]
        lines.append("| %s | %d | %s | %s | %.1f%% | %.1f | %d |" % (
            d, r["chars"], mark, markhi, r["dialogue_ratio"] * 100, r["avg_sent"], r["sent_count"]))

    # 功能词偏差
    lines += ["", "## L1 功能词：偏差最大的八项", "",
              "| 词 | 基线/万 | " + " | ".join(a.dirs) + " |",
              "|---|---|" + "---|" * len(a.dirs)]
    fw_dev = [(w, dev(res[a.dirs[0]]["fw"][w], base_fw[w])) for w in base_fw]
    for w, _ in sorted(fw_dev, key=lambda x: -x[1])[:8]:
        lines.append("| %s | %.2f | %s |" % (
            w, base_fw[w], " | ".join("%.2f" % res[d]["fw"][w] for d in a.dirs)))

    # 套语
    lines += ["", "## L2 套语与句式：偏差最大的八项", "",
              "| 名称 | 基线/万 | " + " | ".join(a.dirs) + " |",
              "|---|---|" + "---|" * len(a.dirs)]
    fr_dev = [(k, dev(res[a.dirs[0]]["frames"][k], base_frames[k])) for k in base_frames]
    for k, _ in sorted(fr_dev, key=lambda x: -x[1])[:8]:
        lines.append("| %s | %.2f | %s |" % (
            k, base_frames[k], " | ".join("%.2f" % res[d]["frames"][k] for d in a.dirs)))

    # 引语动词
    lines += ["", "## L3 引语动词", "",
              "| 动词 | 基线/万 | " + " | ".join(a.dirs) + " |",
              "|---|---|" + "---|" * len(a.dirs)]
    for k, v in sorted(base_tags.items(), key=lambda x: -x[1])[:6]:
        lines.append("| %s | %.2f | %s |" % (
            k, v, " | ".join("%.2f" % res[d]["tags"].get(k, 0) for d in a.dirs)))

    # 句长分布
    lines += ["", "## L4 句长分布", "",
              "| 区间 | 基线 | " + " | ".join(a.dirs) + " |",
              "|---|---|" + "---|" * len(a.dirs)]
    for b in ["<=10", "11-20", "21-30", "31-40", ">40"]:
        lines.append("| %s 字 | %.1f%% | %s |" % (
            b, L["L4_sentence"]["dist"][b] * 100,
            " | ".join("%.1f%%" % (res[d]["dist"][b] * 100) for d in a.dirs)))

    rep = "\n".join(lines)
    print(rep)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(rep)


if __name__ == "__main__":
    main()
