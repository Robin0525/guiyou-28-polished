# 癸酉本《石头记》后二十八回 · 行文润色工程

把《癸酉本石头记》后二十八回的行文，按人民文学出版社《红楼梦》（中国艺术研究院红楼梦研究所校注，彩皮定本）前八十回的语言结构重新润色一遍。

**先读这三条，否则会误解本项目：**

- 癸酉本不是曹雪芹原稿，学界基本无争议地判定为现代续书。本项目**不主张**它是真本。
- 本项目**不是**校勘本、不是学术整理本，是一次**语言层的改写实验**。
- 润色稿是**现代人写的仿作**，不是文物，不是"还原"。请勿引用为原作。

## 原稿来源

`source/` 下的正文，取自：

> **《石头记癸酉本（后二十八回）三周年纪念版·凡第六版》**
> 发布：何莉莉　整理：刘俊俊　发布时间：2011 年 9 月 22 日

原书标注为"三周年纪念版 凡第六版"，即该网络文本的第六次修订。其自称清代抄本，学界不采信；本项目仅按原样收录作为语言研究对象，不对其权利归属作任何主张。详见 [NOTICE.md](NOTICE.md)。

## 许可

**源码公开，禁止商用。** 本项目不是 OSI 意义上的开源项目。

- 代码（`tools/`）：PolyForm Noncommercial License 1.0.0
- 文本（`source/` `drafts/` `polished/` `docs/` `data/`）：CC BY-NC-SA 4.0

允许个人阅读、学习、研究、教学、非商业转载（须署名并以相同许可发布）；禁止售卖、付费订阅、广告变现、打包进商业产品。全文见 [LICENSE](LICENSE)。

## 项目规则

1. **回目不改**。原回目的生造词、错字（如"行狭义""大瘐岭"）一律保留。
2. **诗词不改**。标题诗、联句、曲词、批语一并原样保留。
3. **只动行文**。叙述、对白、连接词、语气词、句长。

程序侧：`polish.py` 用块级 + 行级双保护，标题行直接跳过。已校验 ch081 标题诗与原文逐字一致。

## 底层逻辑：五层风格模型

润色依据不是"读得多所以有语感"，而是一份从校注本前八十回算出来的统计模型，见 **[docs/STYLE_MODEL.md](docs/STYLE_MODEL.md)**。

| 层 | 内容 | 产物 |
|---|---|---|
| L1 | 36 个功能词密度 | `style_model.json` |
| L2 | 29 个套语与句式框架 | `patterns.tsv` |
| L3 | 18 种引语动词分布 | `dialogue_tags.tsv` |
| L4 | 句长均值与五档分布 | `style_model.json` |
| L5 | 对白占比、45 人物声口档案 | `char_profiles.tsv` |

模型测出四件肉眼看不出的差异：

- **「被」超用 5.7 倍**（17.62 vs 3.09，每万字）
- **「把」超用 2.6 倍**（27.89 vs 10.59）
- **裸「道」翻倍、「笑道」腰斩**（72.29 vs 34.59；14.66 vs 26.74）
- **>40 字长句占比翻倍**（22.9% vs 11.2%）

同时测出对白占比：正文口径 **46.0% vs 39.4%**，癸酉本对白偏少。

> 口径更正：初版把校注本的注释（占 19.1%）也算进正文，得出"对白占比几乎一致"的错误结论。剔除注释后已推翻，详见 `docs/STYLE_MODEL.md` 顶部。

定性层的蒸馏结果见 **[docs/文风档案·红楼梦前80回.md](docs/文风档案·红楼梦前80回.md)**（用 `book-style-distill` skill 产出，16 维逐条附原文例句）。

## 目录

```
source/     原稿，28 回，未改动
drafts/     规则初稿：28/28 回，词汇与语气词层
polished/   人工精修稿（当前 ch081 节选）
data/       baseline.json  lexicon.tsv  style_model.json  patterns.tsv
            dialogue_tags.tsv  char_profiles.tsv  changes.json
tools/      extract  build_baseline  build_style_model  polish
            check_style  style_distance  corpus
docs/       STYLE_MODEL 文风档案·红楼梦前80回 STYLE_GUIDE METHOD  验收报告  风格距离
```

## 用法

```bash
# 1. 抽取原文
python tools/extract.py <guiyou.pdf> source/

# 2. 建基线（词汇层）与风格模型（五层）
python tools/build_baseline.py    <hongloumeng.epub> data/baseline.json
python tools/build_style_model.py <hongloumeng.epub> data/

# 3. 规则润色
python tools/polish.py source/ drafts/

# 4. 验收
python tools/check_style.py    source/ drafts/ --out docs/验收报告.md
python tools/style_distance.py source/ drafts/ polished/ --out docs/风格距离.md
```

只依赖标准库。抽取 PDF 时若未装 `pypdf`/`PyMuPDF`，回退到命令行 `workbuddy-pdf`。

## 效果

| 指标 | 校注本前80回 | 原稿 | 规则初稿 |
|---|---|---|---|
| 罢+呢 占语气词 | 99.1% | 54.6% | **97.7%** |
| 吧（每万字） | 0.08 | 5.03 | **0.98** |
| 啊（每万字） | 0.12 | 4.47 | **0.98** |
| 吗（每万字） | 0.07 | 4.34 | **0.39** |
| 单用"咱"（每万字） | 0.16 | 5.37 | **0.30** |
| 便（每万字） | 36.00 | 14.83 | 14.82 |
| 一面…一面（每万字） | 3.26 | 0.21 | 0.21 |
| 被（每万字） | 3.09 | 17.62 | 17.44 |
| >40 字句占比 | 11.2% | 22.9% | 22.9% |

前四项由规则解决。后四项是语法层，机器改不了，只能在 `polished/` 里逐句重写——这也是本项目真正的工作量所在。

## 进度

见 [progress.md](progress.md)。规则初稿 28/28 回；人工精修目前仅 ch081 开头节选（约 1200 / 10226 字）。

## 免责

本项目不是考证、不是校勘、不是新版本。任何以本项目产出作为"红学证据"或"曹雪芹原文"的引用，均属误用。详见 [NOTICE.md](NOTICE.md)。
