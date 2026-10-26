---
name: career-ppt-cloner
description: 复刻历届大学生职业规划大赛（成长赛道/就业赛道）、挑战杯与中国国际大学生创新大赛参赛 PPT 的外观制式，用使用者自己的内容重排一份同款。内置七个已抽取好的风格包（封面、章节页、图文页、照片页、并列卡片页），每个风格包保留原作的背景、装饰图形、页眉带、配色与字体，只替换文字与照片。同时内置三套赛事叙事骨架，按官方评审口径先排大纲再套版面，并用六道量化门（页面规格、内容匹配、版面几何、配色可及性、数字追溯、导出件）把「好不好看」变成可复核的数字与退出码。当用户说「照着往届比赛的 PPT 做一份」「复刻这个风格」「要跟学长学姐那套一样的外形」「做参赛 PPT、职业规划大赛 PPT、生涯发展展示 PPT」「挑战杯路演 PPT」「国创赛 PPT」，或给了一份参考 pptx 要求同款外形时使用。
version: "1.1.0"
user-invocable: true
argument-hint: "[可选：参考 pptx 路径 / 风格名 / 自己的内容与照片目录]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# career-ppt-cloner：职业规划大赛 PPT 同款外形复刻

目标很明确：**外形照抄，内容全换**。背景、装饰弧线、页眉带、章节大字、配色、字体、照片摆位，跟往届参赛作品一致；文字讲的必须是使用者自己的经历。

## 0. 先搞清楚要复刻哪一套

内置风格包在 `styles/` 目录，每个都带 `catalog.md`（页面目录 + 缩略图 + 槽位表）。先读 `styles/README.md` 挑一个，再打开对应的 `catalog.md` 看实拍缩略图。

| 风格 id | 名称 | 外形特征 | 适合 |
| --- | --- | --- | --- |
| `t-warm-orange` | 橙暖生活 | 夜色家居背景，橙金弧形色块，页眉深色标题条 + 橙金进度条 | 成长赛道，温情叙事，讲兴趣起点与成长 |
| `t-teal-tech` | 青蓝科技 | 青蓝渐变城市天际线，整页大数字章节页，白底胶囊条正文 | 就业赛道，理工科技术岗 |
| `t-slate-serious` | 深蓝严谨 | 深色星空机器人主视觉，顶部四段导航 | 研究生就业赛道，科研项目密集 |
| `t-red-formal` | 赤红正式 | 红金对称构图，书法主标题，金色分隔线 | 正式汇报感强，金融/管理方向 |
| `t-green-eco` | 墨绿实业 | 墨绿配米色，稳重克制，几何色块 | 行业落地型叙事，新能源/制造 |
| `t-blue-academic` | 靛蓝学术 | 蓝白插画，顶部导航条常驻 | 成长赛道四段式（探索-目标-匹配-行动） |
| `t-tech-deck` | 科技深景 | 深色科技底，亮蓝描边卡片 | 硬件项目、竞赛成果为主 |

用户给了参考 pptx 但七个都不像时，用它现场抽一套，见 §5。

## 1. 工作流

1. **挑风格**：读 `styles/README.md`，按赛道与专业方向选一个。
2. **排大纲**：`python engine/plan.py --style styles/<id> --event <赛事> --out 大纲.json`。它按赛事评审口径给出每页讲什么，并配好风格包里对应的页码。
3. **看缩略图**：打开 `styles/<id>/catalog.md`，对着大纲里分到的页看 `thumbs/pNN.png`。**必须真的看图**，确认这页的版面装得下你要讲的那段。
4. **冻结页面规格**：`python engine/gate_spec.py --pptx styles/<id>/pack.pptx --spec-dir slide_specs --profile presentation --init` 生成骨架，逐页填主张、内容、槽位上限。**`spec_complete=Y` 之前不许生成**，见 §6。
5. **写内容 JSON**：按 `references/CONTENT-SCHEMA.md` 写。写文案前读 `references/WRITING-RULES.md`。
6. **先过内容门**：`python engine/gate_content.py --style styles/<id> --content 内容.json --profile presentation`。字数超参考、字号会跌破下限、照片缺失，都在这一步拦下来，不用等生成完再看。
7. **生成**：`python engine/fill.py --style styles/<id> --content 内容.json --out 成品.pptx`
8. **过量化门**：`python engine/gate_all.py --pptx 成品.pptx --profile presentation`。版面、配色、导出件逐项复核，见 §6。
9. **导出质检**：`python engine/qc.py --pptx 成品.pptx --outdir 质检目录`，打开 `sheet.jpg` 逐页看。**这一步不能省**，见 §7。
10. **交付**：把 pptx、`sheet.jpg`、`成品.gates.json` 与大纲一起给用户。

已有大纲时直接按大纲里的页码写内容。大纲只是建议，按实际讲得清的内容调整。

## 2. 三个赛事的内容骨架

`python engine/plan.py --list` 打印完整清单。口径与出处见 `references/RESEARCH.md`。

| 赛事骨架 | 适用 | 主线 |
| --- | --- | --- |
| `职业规划成长` | 职业规划大赛成长赛道 | 自我认知、职业定位、职业匹配、未来规划 |
| `职业规划就业` | 职业规划大赛就业赛道 | 个人情况与意向、岗位认知、能力匹配、职业规划 |
| `挑战杯创业` | 挑战杯、中国国际大学生创新大赛 | 项目背景、产品与创新、市场与竞争、商业模式、团队与进展 |

某个版面不够用时，大纲会明确写「某页没有某版面，改用第 N 页」或「已跳过」。看到跳过就换个风格包，或把两段内容并成一页。

## 3. 内容 JSON 的最短写法

```json
{
  "style": "t-warm-orange",
  "pages": [
    { "page": 1, "slots": ["标题", "副标题", "一句话主张", "成长赛道"] },
    { "page": 2, "slots": ["页标题", "四字导航", ["第一段", "第二段", "第三段"], "压轴金句"] },
    { "page": 8, "slots": ["页标题", "四字导航"],
      "photos": [{"photo_slot": 5, "photo": "照片/实验室.jpg"}] }
  ]
}
```

- `slots` 是简写：按 `catalog.md` 里「短写顺序」那一行给出的顺序填，**不是**按槽位号大小。要精确指定某一槽就写完整形式 `"map": [{"slot": 3, "text": "..."}]`。
- 字符串里的换行或数组形式都是分段。**不要手动折行**，引擎会按文本框宽度自动折行。
- 照片槽用 `photo_slot` 编号，编号同样在 `catalog.md` 里。填进去会按占位框比例自动裁切，不会拉伸。
- 单条可覆盖字号字体颜色：`{"slot": 3, "text": "...", "font_size": 22, "color": "#FF8810"}`。除非确有需要，不要覆盖，参考页原来的字号就是这套设计的正解。

完整字段见 `references/CONTENT-SCHEMA.md`。

## 4. 排版的自动处理

这两件事引擎已经做好，写内容时不用管，但要知道它们存在：

- **文字与底衬框像素级居中。** 参考件里文字框和色块是两个独立形状，位置常差一两毫米。生成时会把每个文字框的中点严格对齐到它所在色块的中点，框内再设水平居中与垂直居中。命令行的「与底衬框对齐的槽位 N 个，偏差超限 0 个」就是这一步的复核结果，明细写在 `成品.alignreport.json`。
- **自动折行与自动收字号。** 内容比参考页长时，先按框宽折行，再按框高收字号。

## 5. 挑页与写文案的硬规矩

- **章节页（kind=section）只放章节名，不放正文。** 那页的大数字是装饰，已经保留原文。
- **一个槽位只讲一个意思。** 版面只给了那么大的框，塞两件事一定挤。
- **页标题不超过 12 字**，参考页的字数在 `catalog.md` 的「参考字数」列里，照那个量级写。
- **照片页必须填满照片**。空着的灰框交出去等于没做完。使用者没给照片时，明确问他要，不要拿网图。
- 讲稿另存，不放进页面。

## 6. 量化门：把「好不好看」变成可复核的数字

判据全部写在 `references/QUANT-RULES.md`，阈值集中在 `engine/rules.py`。五道门各自可单跑，
也可以一次跑完：

```bash
python engine/gate_all.py --pptx 成品.pptx --profile presentation \
  --spec-dir slide_specs --style styles/t-warm-orange --content 内容.json \
  --export 成品.pdf:pdf:21 --export 质检目录/sheet.jpg:jpeg
```

| 门 | 脚本 | 拦什么 |
| --- | --- | --- |
| 规格门 | `gate_spec.py` | 主张为空、spec_complete 不是 Y |
| 内容门 | `gate_content.py` | 字数超参考、字号跌破下限、照片缺失、封面缺标题 |
| 版面门 | `gate_layout.py` | 越界、溢出、遮挡、重叠、字号、层级、居中、图片变形 |
| 配色门 | `gate_palette.py` | 色觉缺陷可混淆、灰度不可分、对比度不足、单页色数过多 |
| 数字门 | `gate_numbers.py` | 页面上的数字在证据文件里找不到出处 |
| 导出件门 | `gate_exports.py` | 签名不符、dpi 不足、页数不符、像素超限 |

**口径档位**决定字号下限：`presentation` 按投影讲解（正文 16pt），`reading` 按屏幕自读
（正文 10pt），`paper` 沿用论文画图的 8 磅下限。同一份 PPT 换档跑，通过情况会不一样，
按实际使用场合选档。

判定纪律：`FAIL` 必须改，`WARN` 知道就行。**不为了全绿而放宽阈值**，放宽之后判据就失去意义。
每处失败都报实测值与阈值，读者自己看差多少。

完整用法见 `references/GATES-USAGE.md`，判据阈值表见 `references/QUANT-RULES.md`。

## 7. 交付前的质检

`engine/qc.py` 会导出 `sheet.jpg`（全部页面拼成一张图）与每页 PNG。**必须自己看 sheet.jpg**，重点看四件事：

1. 文字有没有压到装饰图形或照片上。
2. 有没有哪页文字明显比别的页小（说明字数写超了，回去删字）。
3. 照片有没有变形或留白。
4. 章节页、封面页是不是只有标题没有正文。
5. 文字是不是都在各自的色块正中。

`fill.py` 同时会写一份 `成品.fitreport.json`，命令行也会打印「字号被压缩的槽位」。被压缩说明内容超了，优先改文案，**不要靠缩字号硬塞**。

量化门与 `qc.py` 的分工：门给出数字与失败项，`qc.py` 给出可以看的图。两者都要过。门说没问题但
图看着别扭，以图为准；图看着还行但门报失败，先查门报的那一项实测值。

## 7. 现场抽一套新风格

```bash
python engine/build_style.py --src 参考.pptx --outdir styles/<新id> --name "名字" --tier A --note "外形一句话描述"
```

它会：清空全部文字（保留字体字号行距）、把别人的证书截图与图表删掉、把照片换成同尺寸灰框、渲染每页缩略图、生成 `catalog.md`。

`--pages 1-12,15` 只取要用的页。抽完先看 `catalog.md` 的缩略图，确认版式确实可用再写内容。

## 8. 目录

```
engine/plan.py          按赛事评审口径排大纲，配风格包页码
engine/make_pack.py     清空文字、分离装饰与正片、检测底衬框、生成 slots.json
engine/fit.py           量文字、自动折行、按框收字号
engine/align.py         文字框与底衬框像素级居中
engine/fill.py          JSON + 风格包 -> 成品 pptx，支持填照片
engine/qc.py            pptx -> PDF -> PNG + contact sheet
engine/build_style.py   一条命令抽出整套风格包
engine/verify_styles.py 检查风格包结构完整性
engine/rules.py          共享判据：口径档位、阈值常量、主题色解析、对比度、底衬查找
engine/gate_spec.py      页面规格契约门（spec_complete=Y 才许生成）
engine/gate_content.py   内容与版面匹配门（字数、字号、照片、标题）
engine/gate_layout.py    版面几何门（越界、溢出、遮挡、字号、层级、居中、变形）
engine/gate_palette.py   配色门（色觉缺陷、灰度、对比度、单页色数）
engine/gate_exports.py   导出件门（签名、dpi、页数、像素、体积）
engine/gate_all.py       统一入口，跑全部门并写 <pptx>.gates.json
styles/<id>/            风格包：pack.pptx、slots.json、catalog.md、thumbs/
references/             内容 schema、写作规则、复刻原理、量化判据手册、量化门用法、页面规格契约、同类工具调研与赛事依据
```

## 9. 依赖

Python 3 与 `python-pptx`、`Pillow`、`pymupdf`；导出质检另需 LibreOffice（`soffice`）。没装 soffice 时 `qc.py` 会明确报错，按提示指定 `--soffice` 路径即可。
