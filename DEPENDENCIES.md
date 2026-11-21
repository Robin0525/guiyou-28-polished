# 依赖说明

## Python

**3.9 以上，只用标准库。** 无需 pip install 即可运行：

```bash
python tools/build_baseline.py corpus/ data/baseline.json
python tools/build_style_model.py corpus/ data/
python tools/polish.py source/ drafts/
python tools/check_style.py source/ drafts/
python tools/style_distance.py source/ drafts/ polished/
python -m unittest discover -s tests -v
```

## 唯一的外部依赖：`extract.py`

只有从 PDF 抽取原文那一步需要外部 CLI `workbuddy-pdf`（不在本仓库内提供）：

```bash
workbuddy-pdf guiyou.pdf out.txt --format txt
python tools/extract.py out.txt source/
```

**这一步只做一次，产物已提交在 `source/`。** 想复现抽取才需要它；只想跑统计、润色、验收，不需要。

## 语料前置

`corpus/` 下的 79 个回次文件由 `tools/split_chapters.py` 从校注本 epub 生成：

```bash
python tools/split_chapters.py "红楼梦.epub" corpus/
```

**`corpus/` 已提交**，正常使用不必重跑。

## 口径警告

**不要从 epub 直读算基线。** epub 全文 753,918 字里 19.1% 是校注与校记（`〔一〕……从蒙府本改` 这类现代学术文字），会把 `便`、`一面`、语气词等所有密度指标稀释，阈值系统性偏松。

`build_baseline.py` 与 `build_style_model.py` 现在只接受 `corpus/` 目录；传 epub 会打印警告并产出不可用结果。

正确口径：**590,940 字**（前八十回正文，不含注释、校记、换行符；第十七、十八回按底本合为一回，故 79 个回次文件对应 80 回）。
