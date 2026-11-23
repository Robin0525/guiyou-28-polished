#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 polished/ 的二十八回与附录合排成一本书，输出 A5 PDF。

排版约定：
- 正文宋体，诗词黑体，回目隶书，批语楷体朱色；
- 标点避头尾（行首不放收尾标点，行尾不放起首标点），逐行手工断；
- 附录单列，不计入第百零八回。

用法:
    python tools/build_pdf.py --version v261123.02
"""
import argparse
import glob
import os
import re
import sys

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FONTS = {
    "Song": (r"C:\Windows\Fonts\simsun.ttc", 0),      # 宋体
    "Hei": (r"C:\Windows\Fonts\simhei.ttf", None),    # 黑体
    "Li": (r"C:\Windows\Fonts\SIMLI.TTF", None),      # 隶书
    "Kai": (r"C:\Windows\Fonts\STKAITI.TTF", None),   # 楷体
}

VERSION = "v261123.02"
TITLE = "石头记（癸酉本）后二十八回"
SUBTITLE = "按前八十回文风重写行文·润色本"
FRONT_PAGES = 4

# 避头尾：不可出现在行首 / 不可出现在行尾
NO_START = "，。、；：？！）〕〉》」』】”’·…％‰℃"
NO_END = "（〔〈《「『【“‘"


def register_fonts():
    for name, (path, idx) in FONTS.items():
        if not os.path.exists(path):
            sys.exit("缺字体：%s" % path)
        f = TTFont(name, path) if idx is None else TTFont(name, path, subfontIndex=idx)
        pdfmetrics.registerFont(f)


def _tokens(text):
    """把「字＋后随标点」绑成不可分单元；开引号则与后一字绑定。"""
    toks, i, n = [], 0, len(text)
    while i < n:
        j = i + 1
        while j < n and text[j] in NO_START:
            j += 1
        if text[i] in NO_END and j < n:
            k = j + 1
            while k < n and text[k] in NO_START:
                k += 1
            j = k
        toks.append(text[i:j])
        i = j
    return toks


def wrap_cjk(text, width, font, size, indent=0.0):
    """按不可分单元断行：标点不起行、开引号不收行。"""
    lines, cur, w = [], "", indent
    limit = width - indent - 1.5 if indent else width - 1.5
    for tk in _tokens(text):
        tw = pdfmetrics.stringWidth(tk, font, size)
        if cur and w + tw > limit:
            if tk[0] in NO_END and len(cur) > 1:     # 开引号不起行
                k = len(cur) - 1                     # 连同「末字＋后随标点」整体下移
                while k > 0 and cur[k] in NO_START:
                    k -= 1
                tail = cur[k:]
                lines.append(cur[:k])
                cur = tail + tk
                w = pdfmetrics.stringWidth(cur, font, size)
                continue
            lines.append(cur)
            cur, w = tk, tw
            limit = width - 1.5
        else:
            cur += tk
            w += tw
    if cur:
        lines.append(cur)
    return lines


def is_verse(s):
    return len(s) <= 34 and s.endswith(("。", "？", "！")) and "，" in s


def load_md(path):
    t = open(path, encoding="utf-8").read()
    body = re.sub(r"^---[\s\S]*?---\s*", "", t, count=1).strip()
    return [x.strip() for x in body.split("\n\n") if x.strip()]


def load_book():
    chs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "polished/ch*.md"))):
        paras = load_md(f)
        chs.append((paras[0].lstrip("# ").strip(), paras[1:]))
    app = load_md(os.path.join(ROOT, "polished/appendix.md"))
    return chs, (app[0].lstrip("# ").strip(), app[1:])


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Book(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        self.chapter = ""
        self.front = 0                 # 前置页数，首遍为 0（不显示页码）
        self.pages = []
        self._no = ""
        self._up = ""

    def afterFlowable(self, flowable):
        name = getattr(getattr(flowable, "style", None), "name", "")
        if name == "ChapterNo":
            self._no = flowable.getPlainText()
            self._up = ""
        elif name == "ChapterMu":
            self._up = flowable.getPlainText()
        elif name == "ChapterMuLast":
            tail = flowable.getPlainText()
            txt = "%s　%s" % (self._no, tail) if not self._up else \
                "%s　%s %s" % (self._no, self._up, tail)
            self.chapter = txt
            key = "k%d" % self.page
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, level=0)
            self.pages.append((txt, self.page))

    def on_page(self, canv, doc):
        canv.saveState()
        if doc.page > doc.front:
            canv.setFont("Kai", 8.5)
            canv.setFillGray(0.38)
            canv.drawCentredString(A5[0] / 2, A5[1] - 14 * mm, doc.chapter)
            canv.setStrokeGray(0.78)
            canv.setLineWidth(0.4)
            canv.line(20 * mm, A5[1] - 17 * mm, A5[0] - 20 * mm, A5[1] - 17 * mm)
            canv.setFont("Song", 9)
            canv.setFillGray(0.3)
            canv.drawCentredString(A5[0] / 2, 12 * mm, str(doc.page - FRONT_PAGES))
        canv.restoreState()


def _build(out_path, version, toc_entries, front=0):
    register_fonts()
    chs, app = load_book()

    def P(text, style, font, size, width, indent=0.0):
        text = text.replace(" ", "\u00a0")      # 空格不参与断行
        lines = wrap_cjk(text, width, font, size, indent)
        return Paragraph("<br/>".join(esc(x) for x in lines), style)

    W = A5[0] - 40 * mm

    body = ParagraphStyle("Body", fontName="Song", fontSize=10.5, leading=18.5,
                          firstLineIndent=21, alignment=TA_JUSTIFY, wordWrap=None,
                          spaceAfter=2)
    verse = ParagraphStyle("Verse", fontName="Hei", fontSize=10, leading=16.5,
                           leftIndent=24, wordWrap=None)
    verse_label = ParagraphStyle("VerseLabel", fontName="Hei", fontSize=9.5, leading=16,
                                 spaceBefore=6, spaceAfter=4, wordWrap=None)
    crit = ParagraphStyle("Crit", fontName="Kai", fontSize=9, leading=15,
                          leftIndent=12, rightIndent=12, wordWrap=None,
                          textColor="#B00000", spaceBefore=2, spaceAfter=2)
    ch_no = ParagraphStyle("ChapterNo", fontName="Li", fontSize=12, leading=18,
                           alignment=TA_CENTER, spaceBefore=6, spaceAfter=8)
    ch_mu = ParagraphStyle("ChapterMu", fontName="Li", fontSize=15, leading=25,
                           alignment=TA_CENTER, spaceAfter=2)
    ch_mu_last = ParagraphStyle("ChapterMuLast", parent=ch_mu, spaceAfter=22)
    qb_title = ParagraphStyle("QBTitle", fontName="Hei", fontSize=9.5, leading=16,
                              spaceBefore=7, spaceAfter=3)
    qb_list = ParagraphStyle("QBList", fontName="Song", fontSize=10, leading=17,
                             leftIndent=12, rightIndent=6, wordWrap=None)
    toc1 = ParagraphStyle("TOC1", fontName="Song", fontSize=9, leading=15, wordWrap=None)
    toc2 = ParagraphStyle("TOC2", parent=toc1, alignment=2)
    toc_title = ParagraphStyle("TOCTitle", fontName="Li", fontSize=17, leading=30,
                               alignment=TA_CENTER, spaceAfter=14)
    note = ParagraphStyle("Note", fontName="Song", fontSize=9.5, leading=17,
                          alignment=TA_JUSTIFY, wordWrap=None, spaceAfter=6)

    for st in (body, verse, verse_label, crit, ch_no, ch_mu, ch_mu_last,
               qb_title, qb_list, toc1, toc2, toc_title, note):
        st.splitLongWords = 0          # 行已手工断好，禁止 reportlab 二次切

    doc = Book(out_path, pagesize=A5,
               leftMargin=20 * mm, rightMargin=20 * mm,
               topMargin=22 * mm, bottomMargin=20 * mm,
               title=TITLE, author="何莉莉 发布／刘俊俊 整理（原稿）",
               subject=SUBTITLE, creator="guiyou-28-polished " + version)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="front", frames=[frame], onPageEnd=doc.on_page),
        PageTemplate(id="main", frames=[frame], onPageEnd=doc.on_page),
    ])

    S = []
    S.append(Spacer(1, 38 * mm))
    S.append(Paragraph(TITLE, ParagraphStyle("T1", fontName="Li", fontSize=20,
                                             leading=30, alignment=TA_CENTER)))
    S.append(Spacer(1, 6 * mm))
    S.append(Paragraph(SUBTITLE, ParagraphStyle("T2", fontName="Kai", fontSize=12,
                                                leading=20, alignment=TA_CENTER)))
    S.append(Spacer(1, 48 * mm))
    for line in ["原稿：石头记癸酉本（后二十八回）三周年纪念版·凡第六版",
                 "发布 何莉莉　整理 刘俊俊　2011-09-22"]:
        S.append(Paragraph(line, ParagraphStyle("T3", fontName="Kai", fontSize=9,
                                                leading=16, alignment=TA_CENTER,
                                                textColor="#555555")))
    S.append(Spacer(1, 14 * mm))
    S.append(Paragraph(version, ParagraphStyle("T5", fontName="Song", fontSize=10,
                                               alignment=TA_CENTER, textColor="#666666")))
    S.append(PageBreak())

    S.append(Paragraph("几点说明", ParagraphStyle("NT", fontName="Li", fontSize=14,
                                                  leading=22, spaceAfter=12)))
    for t in [
        "一、本书是《石头记》癸酉本后二十八回的润色本。原稿的回目、诗、词、批语一字未动，"
        "所改者仅为行文——句法、词汇、标点，按人民文学出版社《红楼梦》前八十回"
        "（中国艺术研究院红楼梦研究所校注本）的语言统计特征重写。",
        "二、原稿的文字问题不代为遮掩：回目中的错字（如「行狭义」「大瘐岭」）、"
        "批语中的误植（如「如梗在喉」）、回前诗不合近体诗格律，均按原样保留，"
        "另见项目文档《勘误与保留说明》。",
        "三、原稿并非曹雪芹手笔，其真伪与来源在学界有争议。本书只处理语言，"
        "不主张任何考证结论；以本书作为「曹雪芹原文」或红学证据的引用，均属误用。",
        "四、正文中少量原稿误植已改正（如「丫鬓」改「丫鬟」、「阂府」改「阖府」），"
        "逐条列于《勘误与保留说明》。",
        "五、正文后附《前八十回批语摘录与版本备忘录》，系原稿编者所附，"
        "不属第百零八回正文，单列为附录。附录内原文与批语混排，不另标色。",
        "六、本书文本以 CC BY-NC-SA 4.0 发布，禁止商业使用。",
    ]:
        S.append(P(t, note, "Song", 9.5, W))
    S.append(PageBreak())

    S.append(Paragraph("目　录", toc_title))
    entries = toc_entries if toc_entries is not None else \
        [(t, 0) for t, _ in chs] + [("附录　" + app[0].split("　", 1)[-1], 0)]
    rows = [[P(x, toc1, "Song", 9, W - 34), Paragraph(str(n), toc2)] for x, n in entries]
    tbl = Table(rows, colWidths=[W - 34, 34])
    tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    S.append(tbl)
    S.append(NextPageTemplate("main"))
    S.append(PageBreak())

    def emit(title, paras):
        if title.startswith("附录"):
            no, _, mu = title.partition("　")
            S.append(Paragraph(esc(no), ch_no))
            S.append(Paragraph(esc(mu or title), ch_mu_last))
            for p in paras:
                S.append(P(p, body, "Song", 10.5, W, indent=21))
            return
        m = re.match(r"^(第[^回]*回)\s+(.+)$", title)
        if m and " " in m.group(2):
            S.append(Paragraph(esc(m.group(1)), ch_no))
            up, down = m.group(2).split(" ", 1)
            S.append(Paragraph(esc(up), ch_mu))
            S.append(Paragraph(esc(down), ch_mu_last))
        else:
            S.append(Paragraph(esc(title), ch_mu_last))
        in_verse = False
        for p in paras:
            mq = re.match(r"^([“]?(?:-{2,}|—{1,2})金陵十二[^-—\n]+?-{2,})(.*)$", p, re.S)
            if mq:
                S.append(P(mq.group(1), qb_title, "Hei", 9.5, W))
                rest = mq.group(2).strip()
                for seg in rest.split("\n"):
                    if seg.strip():
                        S.append(P(seg, qb_list, "Song", 10, W - 12))
                in_verse = False
                continue
            if p.startswith(("诗云：", "词云：")):
                S.append(P(p, verse_label, "Hei", 9.5, W))
                in_verse = True
                continue
            if p.startswith(("[", "（批语", "（此", "（应", "（第", "（芦", "（清", "（妙", "（红")):
                S.append(P(p, crit, "Kai", 9, W - 24))
                in_verse = False
                continue
            if in_verse and is_verse(p):
                S.append(P(p, verse, "Hei", 10, W - 24))
                continue
            in_verse = False
            S.append(P(p, body, "Song", 10.5, W, indent=21))

    for idx, (title, paras) in enumerate(chs):
        if idx:
            S.append(PageBreak())
        emit(title, paras)

    S.append(PageBreak())
    emit(app[0], app[1])

    doc.front = front
    doc.build(S)
    return doc.pages if toc_entries is None else out_path


def build(out_path, version=VERSION):
    pages = _build(out_path, version, None, 0)          # 首遍不印页码
    front = pages[0][1] - 1                             # 正文首页物理页 - 1
    entries = [(t, max(1, p - front)) for t, p in pages]
    return _build(out_path, version, entries, front)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist",
                                                  "guiyou-28-polished-%s.pdf" % VERSION))
    ap.add_argument("--version", default=VERSION)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    p = build(a.out, a.version)
    print("生成 %s（%.1f MB）" % (p, os.path.getsize(p) / 1048576))


if __name__ == "__main__":
    main()
