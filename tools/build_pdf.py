#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 polished/ 的二十八回合排成一本书，输出 A5 PDF。

用法:
    python tools/build_pdf.py                     # 默认 dist/guiyou-28-polished-v261123.01.pdf
    python tools/build_pdf.py --version v261123.01
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
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FONT_FILES = {
    "Song": r"C:\Windows\Fonts\STSONG.TTF",
    "Hei": r"C:\Windows\Fonts\STXIHEI.TTF",
    "Kai": r"C:\Windows\Fonts\STKAITI.TTF",
}

VERSION = "v261123.01"
TITLE = "石头记（癸酉本）后二十八回"
SUBTITLE = "按前八十回文风重写行文·润色本"
FRONT_PAGES = 4


def register_fonts():
    for name, path in FONT_FILES.items():
        if not os.path.exists(path):
            sys.exit("缺字体：%s" % path)
        pdfmetrics.registerFont(TTFont(name, path))


def is_verse(s):
    """诗行：短、以句号问叹收尾、含逗号。"""
    return len(s) <= 34 and s.endswith(("。", "？", "！")) and "，" in s


def load_chapters():
    chs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "polished/ch*.md"))):
        t = open(f, encoding="utf-8").read()
        body = re.sub(r"^---[\s\S]*?---\s*", "", t, count=1).strip()
        paras = [x.strip() for x in body.split("\n\n") if x.strip()]
        chs.append((paras[0].lstrip("# ").strip(), paras[1:]))
    return chs


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Book(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        self.chapter = ""
        self.pages = []
        self._no = ""
        self._up = ""

    def afterFlowable(self, flowable):
        name = getattr(getattr(flowable, "style", None), "name", "")
        if name == "ChapterNo":
            self._no = flowable.getPlainText()
        elif name == "ChapterMu":
            self._up = flowable.getPlainText()
        elif name == "ChapterMuLast":
            txt = "%s　%s %s" % (self._no, self._up, flowable.getPlainText())
            key = "ch%d" % self.page
            self.chapter = txt
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, level=0)
            self.pages.append((txt, self.page))

    def on_page(self, canv, doc):
        canv.saveState()
        if doc.page > FRONT_PAGES:
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


def _build(out_path, version, toc_entries):
    register_fonts()
    chs = load_chapters()

    body = ParagraphStyle("Body", fontName="Song", fontSize=10.5, leading=18.5,
                          firstLineIndent=21, alignment=TA_JUSTIFY, wordWrap="CJK",
                          spaceAfter=2)
    verse = ParagraphStyle("Verse", parent=body, fontSize=10, leading=16.5,
                           firstLineIndent=0, leftIndent=24)
    verse_label = ParagraphStyle("VerseLabel", parent=body, fontSize=9.5, leading=16,
                                 firstLineIndent=0, spaceBefore=6, spaceAfter=4)
    crit = ParagraphStyle("Crit", parent=body, fontName="Kai", fontSize=9, leading=15,
                          firstLineIndent=0, leftIndent=12, rightIndent=12,
                          textColor="#444444", spaceBefore=2, spaceAfter=2)
    ch_no = ParagraphStyle("ChapterNo", fontName="Kai", fontSize=11, leading=18,
                           alignment=TA_CENTER, spaceBefore=6, spaceAfter=8,
                           wordWrap="CJK")
    ch_mu = ParagraphStyle("ChapterMu", fontName="Hei", fontSize=14.5, leading=24,
                           alignment=TA_CENTER, spaceAfter=2, wordWrap="CJK")
    ch_mu_last = ParagraphStyle("ChapterMuLast", parent=ch_mu, spaceAfter=22)
    toc1 = ParagraphStyle("TOC1", fontName="Song", fontSize=9, leading=15,
                          firstLineIndent=0, wordWrap="CJK")
    toc2 = ParagraphStyle("TOC2", parent=toc1, alignment=TA_RIGHT)
    toc_title = ParagraphStyle("TOCTitle", fontName="Hei", fontSize=16, leading=30,
                               alignment=TA_CENTER, spaceAfter=14)
    qb_title = ParagraphStyle("QBTitle", fontName="Hei", fontSize=9.5, leading=16,
                              firstLineIndent=0, spaceBefore=7, spaceAfter=3,
                              wordWrap="CJK")
    qb_list = ParagraphStyle("QBList", parent=body, fontSize=10, leading=17,
                             firstLineIndent=0, leftIndent=12, rightIndent=6)
    note = ParagraphStyle("Note", fontName="Song", fontSize=9.5, leading=17,
                          firstLineIndent=0, alignment=TA_JUSTIFY, wordWrap="CJK",
                          spaceAfter=6)

    doc = Book(out_path, pagesize=A5,
               leftMargin=20 * mm, rightMargin=20 * mm,
               topMargin=22 * mm, bottomMargin=20 * mm,
               title=TITLE, author="何莉莉 发布／刘俊俊 整理（原稿）",
               subject=SUBTITLE, creator="guiyou-28-polished " + version)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="front", frames=[frame], onPage=doc.on_page),
        PageTemplate(id="main", frames=[frame], onPage=doc.on_page),
    ])

    S = []
    S.append(Spacer(1, 40 * mm))
    S.append(Paragraph(TITLE, ParagraphStyle("T1", fontName="Hei", fontSize=22,
                                             leading=34, alignment=TA_CENTER)))
    S.append(Spacer(1, 6 * mm))
    S.append(Paragraph(SUBTITLE, ParagraphStyle("T2", fontName="Kai", fontSize=12,
                                                leading=20, alignment=TA_CENTER)))
    S.append(Spacer(1, 58 * mm))
    for line in ["原稿：石头记癸酉本（后二十八回）三周年纪念版·凡第六版",
                 "发布 何莉莉　整理 刘俊俊　2011-09-22"]:
        S.append(Paragraph(line, ParagraphStyle("T3", fontName="Kai", fontSize=9,
                                                leading=16, alignment=TA_CENTER,
                                                textColor="#555555")))
    S.append(Spacer(1, 16 * mm))
    S.append(Paragraph(version, ParagraphStyle("T5", fontName="Song", fontSize=10,
                                               alignment=TA_CENTER, textColor="#666666")))
    S.append(PageBreak())

    S.append(Paragraph("几点说明", ParagraphStyle("NT", fontName="Hei", fontSize=13,
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
        "五、本书文本以 CC BY-NC-SA 4.0 发布，禁止商业使用。",
    ]:
        S.append(Paragraph(t, note))
    S.append(PageBreak())

    S.append(Paragraph("目　录", toc_title))
    entries = toc_entries if toc_entries is not None else \
        [(title, 0) for title, _ in chs]
    rows = [[Paragraph(esc(x), toc1), Paragraph(str(n), toc2)] for x, n in entries]
    tbl = Table(rows, colWidths=[doc.width - 34, 34])
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

    for idx, (title, paras) in enumerate(chs):
        if idx:
            S.append(PageBreak())
        m = re.match(r"^(第[^回]*回)\s+(.+)$", title)
        if m and " " in m.group(2):
            no, mu = m.group(1), m.group(2)
            up, down = mu.split(" ", 1)
            S.append(Paragraph(esc(no), ch_no))
            S.append(Paragraph(esc(up), ch_mu))
            S.append(Paragraph(esc(down), ch_mu_last))
        else:
            S.append(Paragraph(esc(title), ch_mu_last))
        in_verse = False
        for p in paras:
            mq = re.match(r"^([“]?(?:-{2,}|—{1,2})金陵十二[^-—\n]+?-{2,})(.*)$", p, re.S)
            if mq:
                S.append(Paragraph(esc(mq.group(1)), qb_title))
                rest = mq.group(2).strip()
                if rest:
                    S.append(Paragraph(esc(rest).replace("\n", "<br/>"), qb_list))
                in_verse = False
                continue
            if p.startswith(("诗云：", "词云：")):
                S.append(Paragraph(esc(p), verse_label))
                in_verse = True
                continue
            if p.startswith(("[", "（批语", "（此", "（应", "（第", "（芦", "（清", "（妙", "（红")):
                S.append(Paragraph(esc(p), crit))
                in_verse = False
                continue
            if in_verse and is_verse(p):
                S.append(Paragraph(esc(p), verse))
                continue
            in_verse = False
            S.append(Paragraph(esc(p), body))

    doc.build(S)
    return doc.pages if toc_entries is None else out_path


def build(out_path, version=VERSION):
    pages = _build(out_path, version, None)
    entries = [(t, max(1, p - FRONT_PAGES)) for t, p in pages]
    return _build(out_path, version, entries)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist",
                                                  "guiyou-28-polished-v261123.01.pdf"))
    ap.add_argument("--version", default=VERSION)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    p = build(a.out, a.version)
    print("生成 %s（%.1f MB）" % (p, os.path.getsize(p) / 1048576))


if __name__ == "__main__":
    main()
