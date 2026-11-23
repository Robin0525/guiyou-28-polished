#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归测试：口径、保护、指标三条线。

跑法：
    python -m unittest discover -s tests -v
    python tests/test_guard.py
"""
import glob
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import polish  # noqa: E402


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestBaselineConsistency(unittest.TestCase):
    """P0 的守护：两个 json 必须是同口径的正文统计。"""

    def setUp(self):
        with open(os.path.join(ROOT, "data/baseline.json"), encoding="utf-8") as f:
            self.b = json.load(f)
        with open(os.path.join(ROOT, "data/style_model.json"), encoding="utf-8") as f:
            self.m = json.load(f)

    def test_chars_match_corpus(self):
        corpus, nch = 0, 0
        for f in sorted(glob.glob(os.path.join(ROOT, "corpus/h*.txt"))):
            lines = read(f).split("\n")
            corpus += len("\n".join(lines[1:]).replace("\n", ""))
            nch += 1
        self.assertEqual(self.b["chars"], corpus, "baseline 字数与 corpus 不一致")
        self.assertEqual(nch, 79, "corpus 应为 79 个回次文件（第十七、十八合回）")

    def test_two_json_same_chars(self):
        self.assertEqual(
            self.b["chars"], self.m["meta"]["chars"],
            "baseline.json 与 style_model.json 口径不一致 —— 这正是 P0 那类 bug",
        )

    def test_no_legacy_scope(self):
        self.assertNotEqual(self.b["chars"], 753918, "仍在用含注释的旧口径")
        self.assertIn("corpus", self.b.get("source", ""), "baseline 来源未标注 corpus/")

    def test_marker_order(self):
        """便、一面 必须显著高于癸酉本，这是全部规则的地基。"""
        self.assertGreater(self.b["markers_per_10k"]["便"], 40)
        self.assertGreater(self.b["markers_per_10k"]["一面"], 10)


class TestVerseGuard(unittest.TestCase):
    """polish.py 的硬保护：回目、诗词、批语一个字都不能动。"""

    def setUp(self):
        self.rules = polish.load_rules()

    def _run(self, text):
        meta, title, lines = polish.split_doc(text)
        out, _ = polish.polish_lines(lines, self.rules)
        return meta, title, out

    def test_title_untouched(self):
        text = "---\na: 1\n---\n\n# 第八十一回 惜昵近公子做良媒\n\n话说那日的事吧。\n"
        _, title, _ = self._run(text)
        self.assertEqual(title, "# 第八十一回 惜昵近公子做良媒")

    def test_verse_block_untouched(self):
        verse = "百般颠倒相酬谋，千种幽思似水柔。\n鬼魅因何难尽驱，心魔桎梏自禁囚。"
        text = "---\na: 1\n---\n\n# 标题\n\n诗云：\n" + verse + "\n\n话说那日的事吧，他竟去了吧。\n"
        _, _, out = self._run(text)
        joined = "\n".join(out)
        self.assertIn("百般颠倒相酬谋，千种幽思似水柔。", joined, "标题诗被改动")
        self.assertIn("心魔桎梏自禁囚。", joined, "标题诗被改动")

    def test_comment_untouched(self):
        text = ("---\na: 1\n---\n\n# 标题\n\n[回前批：此回草成,须重写酌改方妥。畸笏叟]\n\n"
                "话说那日的事吧。\n")
        _, _, out = self._run(text)
        self.assertIn("[回前批：此回草成,须重写酌改方妥。畸笏叟]", "\n".join(out))

    def test_particle_replaced_in_prose(self):
        """语气词该改的地方必须改，否则保护逻辑把正文也冻住了。"""
        text = "---\na: 1\n---\n\n# 标题\n\n宝玉笑道：“你来了吧。”\n"
        _, _, out = self._run(text)
        joined = "\n".join(out)
        self.assertNotIn("来吧", joined, "正文中的「吧」未被替换")


class TestMetrics(unittest.TestCase):
    """精修稿的关键指标，防止手改后退化。"""

    def test_polished_ch081(self):
        path = os.path.join(ROOT, "polished/ch081.md")
        if not os.path.exists(path):
            self.skipTest("polished/ch081.md 不存在")
        body = re.sub(r"^---[\s\S]*?---", "", read(path), count=1)
        n = len(body.replace("\n", ""))
        self.assertGreater(n, 8000, "精修稿字数异常")

        self.assertGreaterEqual(body.count("便") / n * 1e4, 30, "「便」密度不足")
        self.assertGreaterEqual(body.count("一面") / n * 1e4, 7, "「一面」密度不足")

        for w in ("吧", "啊", "吗"):
            self.assertEqual(body.count(w), 0, f"残留语气词「{w}」")

        sents = [x for x in re.split(r"[。！？；]", body) if len(x.strip()) > 2]
        p40 = sum(1 for x in sents if len(x) > 40) / len(sents) * 100
        self.assertLessEqual(p40, 15, f">40 字句占 {p40:.1f}%，超过 15%")

    def test_verse_preserved_vs_source(self):
        """精修稿的标题诗必须与原文逐字一致。"""
        src = os.path.join(ROOT, "source/ch081.md")
        pol = os.path.join(ROOT, "polished/ch081.md")
        if not (os.path.exists(src) and os.path.exists(pol)):
            self.skipTest("缺文件")

        def verse(p):
            # 只比字，不比排版空行——空行是给 Markdown 渲染用的
            t = read(p)
            i = t.find("诗云：")
            j = t.find("话说", i)
            return re.sub(r"\s", "", t[i:j])

        self.assertEqual(verse(src), verse(pol), "标题诗与原文不一致")


class TestLayout(unittest.TestCase):
    """排版：段落之间必须有空行，否则 Markdown 里会挤成一片。"""

    def test_paragraph_gap(self):
        files = sorted(glob.glob(os.path.join(ROOT, "polished/ch*.md")))
        self.assertTrue(files, "polished/ 下没有稿本")
        for f in files:
            lines = read(f).split("\n")
            # 跳过 YAML 头部（--- ... ---）与标题行
            start = 0
            if lines and lines[0].strip() == "---":
                for j in range(1, len(lines)):
                    if lines[j].strip() == "---":
                        start = j + 1
                        break
            for i in range(start, len(lines) - 1):
                a, b = lines[i].strip(), lines[i + 1].strip()
                if len(a) > 30 and len(b) > 30:
                    self.fail(
                        "%s 第 %d、%d 行是两段正文却无空行分隔，"
                        "渲染时会挤成一段：\n  %s\n  %s"
                        % (os.path.basename(f), i + 1, i + 2, a[:30], b[:30])
                    )

    def test_no_trailing_blank_run(self):
        for f in sorted(glob.glob(os.path.join(ROOT, "polished/ch*.md"))):
            self.assertLessEqual(
                read(f).count("\n\n\n"), 0, "%s 有多余连续空行" % os.path.basename(f)
            )


class TestProtectedText(unittest.TestCase):
    """回目、诗、批语一字未动——全量核验，不是抽样。"""

    def test_all_protected_blocks_intact(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "verify_protected.py")],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(
            r.returncode, 0,
            "回目／诗／批语出现改动或缺失：\n" + (r.stdout[-1500:] or r.stderr[-1500:]),
        )
        self.assertIn("缺失或改动 | 0 处", r.stdout, "核验汇总异常")


if __name__ == "__main__":
    unittest.main(verbosity=2)
