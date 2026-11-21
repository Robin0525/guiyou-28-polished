#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引语标签统计：区分"具体标签"与"裸道"。

之前的临时脚本用固定词表匹配，会把「泣道」「怒道」「诉道」这类
**具体化标签**错算成裸「道」，导致"裸道占比"虚高。
本脚本按"道"前的最长修饰后缀归类，找不到修饰才算裸道。

用法:
    python tools/tag_stats.py corpus/ polished/ch081.md polished2/ch081.md
"""
import collections
import glob
import os
import re
import sys

# 修饰词：凡"X道"中的 X 在此表内，即为具体标签
MODIFIERS = [
    "笑道", "冷笑道", "陪笑道", "忙笑道", "点头道", "摇头道", "接着道", "因道",
    "忙道", "哭道", "泣道", "叹道", "骂道", "答道", "回道", "问道", "说道",
    "又道", "喝道", "啐道", "嚷道", "嗔道", "斥道", "恨道", "劝道", "念道",
    "应道", "催道", "怒道", "诉道", "笑道", "叫道", "喊道", "骂道", "恨道",
    "咬牙道", "点头叹道", "点头笑道", "摇头笑道", "拍手笑道", "含泪道",
    "落泪道", "流泪道", "哭着道", "悄悄道", "低声道", "正色道", "淡淡的笑",
    "淡淡的道", "嗤的一声笑道", "嗤的笑道", "一面道", "忙陪笑道",
]
MOD_SET = sorted(set(m.rstrip("道") for m in MODIFIERS if m.endswith("道")), key=len, reverse=True)

PAT = re.compile(r"([\u4e00-\u9fa5]{1,4})道[：:]“")


def load(path):
    if os.path.isdir(path):
        return "\n".join(
            "\n".join(open(f, encoding="utf-8").read().split("\n")[1:])
            for f in sorted(glob.glob(os.path.join(path, "h*.txt")))
        )
    t = open(path, encoding="utf-8").read()
    return re.sub(r"^---[\s\S]*?---", "", t, count=1)


def classify(prefix):
    """返回命中的修饰词；找不到则返回 '' 表示裸道（但需排除人名）。"""
    for mod in MOD_SET:
        if prefix.endswith(mod):
            return mod + "道"
    return ""


def stats(text):
    n = len(text.replace("\n", ""))
    c = collections.Counter()
    bare = 0
    for m in PAT.finditer(text):
        tag = classify(m.group(1))
        if tag:
            c[tag] += 1
        else:
            # 前缀可能是人名（宝玉/袭人/王夫人…）或短语——都归为裸道
            bare += 1
    total = sum(c.values()) + bare
    return n, total, c, bare


def main():
    paths = sys.argv[1:] or ["corpus/"]
    print("%-24s %8s %6s %8s %8s %8s" % ("稿本", "字数", "标签", "裸道%", "笑道%", "标签/万"))
    for p in paths:
        n, total, c, bare = stats(load(p))
        xd = c.get("笑道", 0)
        print("%-24s %8d %6d %7.1f%% %7.1f%% %8.1f" % (
            p[:24], n, total, bare / total * 100, xd / total * 100, total / n * 10000))
        top = "  ".join("%s×%d" % (k, v) for k, v in c.most_common(10))
        print("    " + top)


if __name__ == "__main__":
    main()
