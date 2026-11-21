#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从校注本前八十回建立五层风格模型，供润色与验收调用。

用法:
    python tools/build_style_model.py <hongloumeng.epub> data/

产出:
    data/style_model.json     五层指标（L1 功能词 / L2 套语框架 / L3 引语动词 / L4 句长 / L5 声口）
    data/patterns.tsv         套语与句式模板（含频次、每万字、首例）
    data/dialogue_tags.tsv    引语动词分布
    data/char_profiles.tsv    人物声口档案
"""
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus import front80, load_epub  # noqa: E402

FUNCTION_WORDS = list("的了便又也都只倒竟才还就因遂方且却将把被与和及若虽则乃着过得地之其此这那么呢罢")

TAGS = ["冷笑道", "陪笑道", "忙笑道", "点头道", "摇头道", "接着道", "因道", "忙道", "哭道",
        "叹道", "骂道", "答道", "回道", "问道", "说道", "笑道", "又道", "道"]

FRAMES = [
    ("L2", "一言起句·话说", "lit", "话说", "每回起首第一层套语"),
    ("L2", "转段·且说", "lit", "且说", "另起一头"),
    ("L2", "转段·却说", "lit", "却说", "同上"),
    ("L2", "并列框架·一面…一面", "re", r"一面[^，。]{1,12}，[^，。]{0,10}一面", "两事并行，曹雪芹的骨架句"),
    ("L2", "顺承·听了便", "re", r"(?:听了|见了|想罢|说罢|看毕|念毕)[，]?便", "听完即接动作"),
    ("L2", "因果·因…遂", "re", r"因[^，。]{1,14}，?遂", "文言式因果链"),
    ("L2", "趋动·便…起来", "re", r"便[^，。]{0,8}(?:起来|出去|进来|下去)", "动作起势"),
    ("L2", "提示·只见", "lit", "只见", "视角切换"),
    ("L2", "提示·原来", "lit", "原来", "补叙缘由"),
    ("L2", "转折·谁知", "lit", "谁知", "意外转折"),
    ("L2", "转折·岂知", "lit", "岂知", "同上，更文"),
    ("L2", "时间·一时", "lit", "一时", "短时"),
    ("L2", "时间·不一时", "lit", "不一时", "片刻"),
    ("L2", "时间·少顷", "lit", "少顷", "同上"),
    ("L2", "时间·须臾", "lit", "须臾", "同上"),
    ("L2", "收束·不在话下", "lit", "不在话下", "略过不提"),
    ("L2", "收束·自不必说", "lit", "自不必说", "同上"),
    ("L2", "限定·只得", "lit", "只得", "别无他法"),
    ("L2", "限定·只好", "lit", "只好", "同上"),
    ("L2", "语尾·罢了", "lit", "罢了", "不过如此"),
    ("L2", "反问·不成", "lit", "不成", "句末反问"),
    ("L2", "程度·越发", "lit", "越发", "递进"),
    ("L2", "语气·索性", "lit", "索性", "决断"),
    ("L2", "语气·倒", "lit", "倒", "反诘副词"),
    ("L2", "语气·竟", "lit", "竟", "出乎意料"),
    ("L2", "语气·偏", "lit", "偏", "执拗"),
    ("L2", "揣度·打量", "lit", "打量", "估量，非『看』"),
    ("L2", "揣度·估着", "lit", "估着", "猜想"),
    ("L2", "恍然·怪道", "lit", "怪道", "难怪"),
]

PAUSES = ["罢", "呢", "吧", "啊", "吗", "么", "呀"]

ALIAS = {"凤姐儿": "凤姐", "林黛玉": "黛玉", "薛宝钗": "宝钗", "史湘云": "湘云",
         "贾探春": "探春", "贾迎春": "迎春", "贾惜春": "惜春", "李宫裁": "李纨",
         "老太太": "贾母", "平儿": "平儿"}


def per10k(n, total):
    return round(n / total * 10000, 3) if total else 0.0


def sentences(text):
    return [s for s in re.split(r"[。！？；]", text) if len(s.strip()) > 2]


def dialogue(text):
    spans = re.findall(r"“([^”]{1,400})”", text)
    return spans, sum(len(s) for s in spans)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    epub, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    text, nch = front80(load_epub(epub))
    n = len(text)
    sents = sentences(text)
    lens = [len(s) for s in sents]
    spans, dchars = dialogue(text)

    # L1 功能词
    l1 = {w: per10k(text.count(w), n) for w in FUNCTION_WORDS}

    # L2 套语与框架
    l2, pattern_rows = {}, []
    for layer, name, kind, val, note in FRAMES:
        if kind == "lit":
            cnt = text.count(val)
            ex = ""
            i = text.find(val)
            if i >= 0:
                ex = text[max(0, i - 12):i + 20].replace("\n", "")
        else:
            ms = list(re.finditer(val, text))
            cnt = len(ms)
            ex = ms[0].group(0) if ms else ""
        l2[name] = per10k(cnt, n)
        pattern_rows.append((layer, name, kind, val, cnt, per10k(cnt, n), note, ex))

    # L3 引语动词
    tag_pat = "|".join(sorted(TAGS, key=len, reverse=True))
    say_re = re.compile(r"(?P<tag>" + tag_pat + r")：“(?P<say>[^”]{1,300})”")
    tag_counts = {t: 0 for t in TAGS}
    for m in say_re.finditer(text):
        tag_counts[m.group("tag")] += 1
    l3 = {k: per10k(v, n) for k, v in tag_counts.items() if v}

    # L4 句长
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
    tot = len(lens)
    l4 = {
        "avg": round(statistics.mean(lens), 2),
        "median": round(statistics.median(lens), 2),
        "dist": {k: round(v / tot, 4) for k, v in bins.items()},
    }

    # L5 声口
    who_re = re.compile(r"(?:^|[，。！？；：\n”])(?P<who>[\u4e00-\u9fa5]{2,3}?)"
                        r"(?P<tag>" + tag_pat + r")：“(?P<say>[^”]{1,300})”")
    prof = {}
    for m in who_re.finditer(text):
        who = ALIAS.get(m.group("who"), m.group("who"))
        tag, say = m.group("tag"), m.group("say")
        d = prof.setdefault(who, {"lines": 0, "chars": 0, "len": [], "tags": {}, "pauses": {}})
        d["lines"] += 1
        d["chars"] += len(say)
        d["len"].append(len(say))
        d["tags"][tag] = d["tags"].get(tag, 0) + 1
        for p in PAUSES:
            d["pauses"][p] = d["pauses"].get(p, 0) + say.count(p)
    profiles = []
    for who, d in prof.items():
        if d["lines"] < 15:
            continue
        pc = d["chars"] or 1
        profiles.append({
            "who": who,
            "lines": d["lines"],
            "avg_len": round(statistics.mean(d["len"]), 1),
            "pause_per_100": round(sum(d["pauses"].values()) / pc * 100, 2),
            "top_tags": sorted(d["tags"].items(), key=lambda x: -x[1])[:3],
        })
    profiles.sort(key=lambda x: -x["lines"])

    l5 = {
        "dialogue_ratio": round(dchars / n, 4),
        "dialogue_spans": len(spans),
        "speakers": len(prof),
        "profiles": profiles,
    }

    model = {
        "meta": {
            "edition": "人民文学出版社《红楼梦》 中国艺术研究院红楼梦研究所校注（彩皮定本）",
            "scope": "前八十回正文",
            "chars": n,
            "chapter_units": nch,
            "generated_by": "tools/build_style_model.py",
        },
        "layers": {
            "L1_function_words_per_10k": l1,
            "L2_frames_per_10k": l2,
            "L3_dialogue_tags_per_10k": l3,
            "L4_sentence": l4,
            "L5_voice": l5,
        },
    }
    with open(os.path.join(outdir, "style_model.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)

    with open(os.path.join(outdir, "patterns.tsv"), "w", encoding="utf-8") as f:
        f.write("层\t名称\t类型\t模式\t次数\t每万字\t说明\t首例\n")
        for r in pattern_rows:
            f.write("\t".join(str(x) for x in r) + "\n")

    with open(os.path.join(outdir, "dialogue_tags.tsv"), "w", encoding="utf-8") as f:
        f.write("引语动词\t次数\t每万字\n")
        for k, v in sorted(tag_counts.items(), key=lambda x: -x[1]):
            if v:
                f.write("%s\t%d\t%.3f\n" % (k, v, per10k(v, n)))

    with open(os.path.join(outdir, "char_profiles.tsv"), "w", encoding="utf-8") as f:
        f.write("人物\t说话次数\t平均句长\t语气词/百字\t常用引语动词\n")
        for p in profiles:
            f.write("%s\t%d\t%.1f\t%.2f\t%s\n" % (
                p["who"], p["lines"], p["avg_len"], p["pause_per_100"],
                "、".join("%s%d" % (t[0], t[1]) for t in p["top_tags"])))

    print("字数 %d，句 %d，句长均值 %.2f，对白占比 %.1f%%，人物 %d" % (
        n, len(lens), l4["avg"], l5["dialogue_ratio"] * 100, len(profiles)))
    print("\nL3 引语动词前八：")
    for k, v in sorted(tag_counts.items(), key=lambda x: -x[1])[:8]:
        print("  %-4s %5d  %.2f/万" % (k, v, per10k(v, n)))
    print("\nL2 套语前八：")
    for name, v in sorted(l2.items(), key=lambda x: -x[1])[:8]:
        print("  %-16s %.2f/万" % (name, v))


if __name__ == "__main__":
    main()
