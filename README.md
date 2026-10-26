# career-ppt-cloner

复刻大学生竞赛 PPT 的外观制式，用你自己的内容重排一份同款，并用六道量化门把「好不好看」变成可复核的数字与退出码。

适用于职业规划大赛（成长赛道 / 就业赛道）、挑战杯、中国国际大学生创新大赛，以及各类课程汇报与答辩。

## 它做什么

把一份参考 pptx 直接当母版，抽掉内容、留下外形：背景、装饰弧线、页眉带、章节大字、配色、字体、照片摆位全部保留，只替换文字与照片。然后按赛事评审口径排大纲、套版面、过量化门。

三件事是它的核心：

1. **外形照抄，内容全换。** 参考件的外观 100% 一致，别人的证书与图表全部删掉。
2. **文字塞得下。** 按字符类型估宽、按框宽折行、按框高收字，写超了明确报出来。
3. **量化门判定完成。** 版面、配色、内容、规格、数字、导出件六道门，任一失败退出码 1。

## 快速开始

```bash
# 1. 抽一套风格包（把自己的参考 pptx 变成可填的空壳版面）
python engine/build_style.py --src 参考.pptx --outdir styles/my-style --name "我的风格" --tier A

# 2. 看页面目录与缩略图，挑页
cat styles/my-style/catalog.md

# 3. 冻结页面规格
python engine/gate_spec.py --pptx styles/my-style/pack.pptx --spec-dir slide_specs --init

# 4. 写内容 JSON，先过内容门
python engine/gate_content.py --style styles/my-style --content 内容.json

# 5. 生成
python engine/fill.py --style styles/my-style --content 内容.json --out 成品.pptx

# 6. 过全部门
python engine/gate_all.py --pptx 成品.pptx --profile presentation
```

## 六道量化门

| 门 | 脚本 | 拦什么 |
| --- | --- | --- |
| 规格门 | `gate_spec.py` | 主张为空、`spec_complete` 不是 Y |
| 内容门 | `gate_content.py` | 字数超参考、字号跌破下限、照片缺失、封面缺标题 |
| 版面门 | `gate_layout.py` | 越界、溢出、遮挡、重叠、字号、层级、居中、图片变形 |
| 配色门 | `gate_palette.py` | 色觉缺陷可混淆、灰度不可分、对比度不足、单页色数过多 |
| 数字门 | `gate_numbers.py` | 页面上的数字在证据文件里找不到出处 |
| 导出件门 | `gate_exports.py` | 签名不符、dpi 不足、页数不符、像素超限 |

统一入口 `gate_all.py` 串起全部门，报告写到 `<pptx 同名>.gates.json`。判据阈值见
[`references/QUANT-RULES.md`](references/QUANT-RULES.md)，用法见
[`references/GATES-USAGE.md`](references/GATES-USAGE.md)。

## 赛事设计令牌

`engine/palette_presets.py` 内置九套配色令牌，覆盖挑战杯红金、国创赛科技蓝、职规成长暖橙、
职规就业青蓝、实业墨绿、深景科技，以及三套学术答辩配色。每套给九个角色色值
（主色、辅助色、强调色、正文、弱化文字、背景、面板、分隔线、反白色）与九个角色的字号下限。

```bash
python engine/palette_presets.py
```

九套令牌全部通过色觉缺陷与灰度判定：可混淆对合计 0，正文对背景对比度在 13.77 到 17.40 之间，
反白对主色在 5.32 到 13.13 之间。令牌来源与逐条出处见
[`references/CONTEST-DESIGN-TOKENS.md`](references/CONTEST-DESIGN-TOKENS.md)。

## 三档口径

同一份 PPT 在不同场合的可读性要求不同，字号下限按档位取值。

| 档位 | 场合 | 正文字号下限 |
| --- | --- | --- |
| `presentation` | 投影讲解，2 米幕布、8 米距离 | 16pt |
| `reading` | 1080p 屏幕自读 | 10pt |
| `paper` | 当论文插图导出 | 8pt |

## 真实材料上的基线

21 页院赛 PPT（33.87 × 19.05 cm）：

| 档位 | 版面门 | 配色门 |
| --- | --- | --- |
| presentation | FAIL=23 WARN=14 | FAIL=15 WARN=23 PASS=26 |
| reading | FAIL=0 WARN=14 | 同上 |
| paper | FAIL=0 WARN=14 | 同上 |

presentation 档的 23 项失败全是字号下限：23 个槽位实际字号在 11 到 13pt，投影讲解时看不清。
配色门的 15 项失败是三组真实对比度不足：白字 `#FFFFFF` 压橙底 `#C48B2C`（2.97）、
`#C48B2C` 字压 `#F2F7FD` 底（2.76）、灰字 `#6E7B8A` 压 `#F2F7FD` 底（4.01）。

## 目录

```
SKILL.md                 技能入口：工作流、硬规矩、量化门说明
engine/rules.py          共享判据：口径档位、阈值常量、主题色解析、对比度、底衬查找
engine/fit.py            量文字、自动折行、按框收字号
engine/align.py          文字框与底衬框像素级居中
engine/make_pack.py      清空文字、分离装饰与正片、检测底衬框、生成 slots.json
engine/build_style.py    一条命令抽出整套风格包
engine/fill.py           JSON + 风格包 -> 成品 pptx，支持填照片
engine/plan.py           按赛事评审口径排大纲
engine/qc.py             pptx -> PDF -> PNG + contact sheet
engine/shrink_media.py   压缩风格包内嵌媒体，便于分发
engine/verify_styles.py  检查风格包结构完整性
engine/palette_presets.py 九套赛事配色令牌与字号下限
engine/gate_*.py         六道量化门
engine/gate_all.py       统一入口
references/              内容 schema、写作规则、复刻原理、量化判据、页面规格、
                         上游 skill 调研（UPSTREAM-SKILLS.md）、赛事设计令牌（CONTEST-DESIGN-TOKENS.md）
```

## 依赖

Python 3 与 `python-pptx`、`Pillow`、`lxml`；导出质检另需 LibreOffice（`soffice`）与 `pymupdf`。

```bash
pip install python-pptx Pillow lxml pymupdf
```

## 关于风格包

本仓库**不分发**任何风格包文件。`styles/` 下的 `pack.pptx` 是从他人参赛作品抽出的版面，
包含他人设计的背景、装饰图形与照片占位，版权归原作者，不随本仓库发布。

自己抽风格包：

```bash
python engine/build_style.py --src 你的参考.pptx --outdir styles/my-style --name "我的风格" --tier A
```

抽完看 `styles/my-style/catalog.md` 里的缩略图，确认版式可用再写内容。

## 致谢与许可

本项目以 MIT 许可发布，详见 [LICENSE](LICENSE)。

设计判据与量化门的思路来自以下开源项目，具体吸收内容见
[`references/UPSTREAM-SKILLS.md`](references/UPSTREAM-SKILLS.md)：

- [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)（MIT）— 原生可编辑 PPTX 与 SVG→DrawingML 管线
- [Gabberflast/academic-pptx-skill](https://github.com/Gabberflast/academic-pptx-skill)（MIT）— 学术汇报的版式模式与字号层级
- [adithya-s-k/research-presentation-template](https://github.com/adithya-s-k/research-presentation-template)（MIT）— 主题令牌与溢出守卫
- [tristan-mcinnis/pptx-from-layouts-skill](https://github.com/tristan-mcinnis/pptx-from-layouts-skill)（MIT）— 严格套模板母版
- [addsumtech/slides_maker](https://github.com/addsumtech/slides_maker)（MIT）— 论文转原生 PPTX
- [M1n-n9/academic-ppt-master](https://github.com/M1n-n9/academic-ppt-master)（MIT）— 学术品牌令牌，进入赛事配色库
- [anthropics/skills](https://github.com/anthropics/skills) 的 pptx skill — 只参考做法与陷阱清单，未复制代码
- [gitbrent/PptxGenJS](https://github.com/gitbrent/PptxGenJS)（MIT）与 [scanny/python-pptx](https://github.com/scanny/python-pptx)（MIT）— 底层库

以下项目因许可证限制**未**内化：`GordenSun/GordenPPTSkill`（非商业使用）、
`op7418/guizang-ppt-skill` 与 `chuspeeism/dashi-ppt-skill`（AGPL-3.0）。
