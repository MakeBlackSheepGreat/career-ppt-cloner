# 量化门使用说明

五道门加两道扩展门，全部返回退出码：`0` 通过，`1` 有失败项。判据手册见
`QUANT-RULES.md`，页面规格契约见 `SLIDE-SPEC.md`。

## 一条命令跑全部门

```bash
python engine/gate_all.py --pptx 成品.pptx --profile presentation \
  --spec-dir slide_specs \
  --style styles/t-warm-orange --content 内容.json \
  --evidence 数据/metrics.csv \
  --export 成品.pdf:pdf:21 --export 质检目录/sheet.jpg:jpeg
```

只给 `--pptx` 时跑版面门与配色门；给 `--spec-dir` 加跑规格门；给 `--style` 与 `--content`
加跑内容门；给 `--evidence` 加跑数字门；给 `--export` 加跑导出件门。报告写到
`<pptx 同名>.gates.json`。

## 单独跑

```bash
python engine/gate_spec.py    --pptx styles/t-warm-orange/pack.pptx --spec-dir slide_specs --profile presentation --init
python engine/gate_content.py --style styles/t-warm-orange --content 内容.json --profile presentation
python engine/gate_layout.py  --pptx 成品.pptx --profile presentation
python engine/gate_palette.py --pptx 成品.pptx --profile presentation
python engine/gate_palette.py --colors "#4477AA,#66CCEE,#228833,#CCBB44,#EE6677,#AA3377"
python engine/gate_numbers.py --content 内容.json --evidence 数据/metrics.csv --warn
python engine/gate_exports.py --file 成品.pdf:pdf:21 --file sheet.jpg:jpeg --file p01.png:png:300
```

## 三档口径

`--profile` 决定字号下限。同一份 PPT 换档跑，通过情况不一样。

| 档位 | 场合 | 正文字号下限 |
| --- | --- | --- |
| presentation | 投影讲解，2 米幕布、8 米距离 | 16pt |
| reading | 1080p 屏幕自读 | 10pt |
| paper | 当论文插图导出 | 8pt |

## 输入文件的格式

**内容 JSON**：`references/CONTENT-SCHEMA.md`。

**spec 目录**：`slide_specs/spec_pNN.md`，每页一份。用 `--init` 生成骨架，填完把
`spec_complete` 改成 `Y`。

**证据文件**：`.csv` 每格都当候选值；`.json` 递归取全部数值与数值字符串；`.md`/`.txt`
用正则抽数字字面量。页面上的数字在证据集合里找不到就报出来。序号、年份、班级编号、
页眉导航里的数字不参与追溯。

**导出件**：`PATH:TYPE[:PAGES或DPI]`。TYPE 取 `png` / `jpeg` / `pdf` / `svg`。
第三段是整数时：栅格件当 dpi，矢量件当页数。

## 怎么读输出

每条判据一行：`FAIL|WARN|PASS  位置  判据  实测值  阈值`。末尾一行汇总。有 `FAIL` 时退出码 1。

```text
FAIL 页3   字号下限   槽位 15「综合测评 99.81，专」角色 body 实际 12.8pt  实测=12.76 阈值=16.0
WARN 页17  居中     槽位 8「3 项」与底衬 Rounded Rectangle 17 偏差 dx=-2.54 dy=0.00  实测=2.54 阈值=0.15
```

实测值在阈值哪一侧，差多少，都在行里。处理顺序：先删字，再换槽位，最后才调字号。
**不要为了全绿而放宽阈值**，放宽之后判据就失去意义。

## 在真实材料上的基线

21 页院赛 PPT（`杨智杰_职业生涯规划.pptx`，33.87 × 19.05 cm）：

| 档位 | 版面门 | 配色门 |
| --- | --- | --- |
| presentation | FAIL=23 WARN=14 | FAIL=15 WARN=23 PASS=26 |
| reading | FAIL=0 WARN=14 | 同上 |
| paper | FAIL=0 WARN=14 | 同上 |

presentation 档的 23 项失败全是字号下限：这一版有 23 个槽位实际字号在 11 到 13pt，
投影讲解时读者看不清。配色门的 15 项失败集中在三组：白字 `#FFFFFF` 压橙底 `#C48B2C`
（对比度 2.97）、`#C48B2C` 字压 `#F2F7FD` 底（2.76）、灰字 `#6E7B8A` 压 `#F2F7FD` 底（4.01）。

四个风格包的版面门基线（presentation 档）：`t-slate-serious` FAIL=0 WARN=2、
`t-warm-orange` FAIL=2 WARN=7、`t-blue-academic` FAIL=31 WARN=49、`t-teal-tech`
FAIL=49 WARN=35。teal 包的失败集中在溢出与变形，是那个参考件本身把长句塞进小框、
把图片拉伸使用的痕迹，不是门的问题。

这一版在 reading 档下版面全过，说明字号问题是「投影场合」与「屏幕自读」的差别，
不是排版缺陷。

## 与 qc.py 的分工

门给出数字与失败项，`qc.py` 给出可以看的图。两者都要过。门说没问题但图看着别扭，
以图为准；图看着还行但门报失败，先查门报的那一项实测值。
