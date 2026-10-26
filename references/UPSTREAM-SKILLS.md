# 开源 PPT skill 做法调研

这份文档记录 2026 年 10 月对 GitHub 上六个开源 PPT skill 的调研结果，用途是把它们的可操作做法吸收进本 skill。
调研方式是用 `gh api` 读取仓库文件内容与许可证，没有克隆任何仓库。中间产物留在 `.tmp/upstream/`。

每个仓库给出四项：仓库信息、核心做法、能吸收的部分、不能吸收的部分。
第九节把这些做法映射到本 skill 的具体文件，并标注状态。

## 一、hugohe3/ppt-master

| 项目 | 内容 |
| --- | --- |
| 仓库地址 | https://github.com/hugohe3/ppt-master |
| 许可证 | MIT（`repos/hugohe3/ppt-master` 的 `license.spdx_id` 返回 MIT） |
| Star | 68829 |
| 分支与最近提交 | `main`，2026-10-24 |
| 规模 | 13284 个文件，约 139 MB |

### 核心做法

**1. 用一份 SVG 中间语言编译成原生 DrawingML。**
页面写成 `svg_output/<slide>.svg`，导出时逐元素编译为 DrawingML 形状、文本、图片。
单位只用一种：画布 `viewBox="0 0 1280 720"` 就是 1280×720 像素，导出时 `1 SVG px = 9525 EMU`。
字号在整条链路里都用无单位 px，导出时换算 `pt = px × 0.75`，保留一位小数，所以 PowerPoint 里出现 13.5pt、31.5pt 属于预期结果。
正文基准按阅读模式取固定值，`text` 20px（约 15pt）、`balanced` 24px（约 18pt）、`presentation` 32px（约 24pt）。
出处：`docs/powerpoint-svg-mapping.md` 第 1 节、`docs/faq.md` 的「Why are font sizes in px, not pt?」、`skills/ppt-master/references/canvas-formats.md`。

**2. 每一项 PowerPoint 能力都标注保真度等级。**
七个等级：`Native-stable`（用对应原生属性）、`Native-normalized`（可编辑但结构被归一化）、`Approximate`（没有精确对应，需要复核）、`Bake-required`（必须预渲染成图或重建几何）、`Sidecar/package`（属于旁挂文件而非页面）、`Direct preservation`（只在不改源 OOXML 的路线保留）、`Unsupported`（不猜）。
每一项能力都写明「项目里由谁表示、导出成什么、导入是否可还原、校验边界」。
出处：`docs/powerpoint-svg-mapping.md` 的开头说明与各节表格、`skills/ppt-master/references/shared-standards-core.md` 顶部的保真度标签表。

**3. 版面几何用根组边界与固定阈值判定。**
每个可见的顶层 `<g>` 必须声明 `data-pptx-bounds="x y width height"`，尺寸取该模块区域。
检查器判据：普通根组互相重叠超过 `1px`（两个轴都算）判失败；模块文字溢出边界 `1px` 以内忽略、`5%` 以内告警、超过 `5%` 判失败；超出根 `viewBox` 的文字溢出直接判失败。
`data-pptx-bounds` 只用于判定，不裁剪也不重排文字。
出处：`skills/ppt-master/scripts/docs/svg-contract.md` 第 4 节。

**4. 行距按角色给出起始区间，不用 CSS 行高。**
多行标题从 `1.2–1.3 ×` 字号起，密集小正文 `1.4–1.5 ×`，普通正文 `1.5–1.6 ×`，大字稀疏正文 `1.6–2.0 ×`。
行距写成 `<tspan dy>` 的正数，因为 CSS `line-height` 在 DrawingML 里没有对应属性。
出处：`skills/ppt-master/references/shared-standards-core.md` 第 4.2 节。

**5. 视觉复核是一张编号缺陷表。**
硬缺陷 H2 文字溢出容器、H3 两个文字框相交、H4 对比度低于 4.5（小字）或低于 3.0（字号 ≥24px）、H6 元素碰撞。
软缺陷 S1 同一文字块内相邻基线间距小于 `1.05 ×` 字号、S5 一行卡片的相邻 x 间距偏差超过平均值 `5%`、S6 CJK 的 `letter-spacing ÷ 字号` 超过 `5%`（应压到 `2%` 以内）。
每条缺陷都要求给出实测值，例如「letter-spacing=10 on font-size=84, ratio=11.9% > 5%」。
出处：`skills/ppt-master/references/visual-review.md`。

**6. 文字宽度先测量再落位。**
`text_measure.py` 提供 `measure`、`wrap`、`box`、`calibrate` 四个子命令。
宽度估计用内置 `font_advances.json` 的逐字前进量，不读本机安装的字体。
中英混排按「CJK 字数 ÷ CJK 速率 + 其他字符 ÷ 拉丁速率」× 100 估算，空格与 ASCII 标点算拉丁，全角标点算 CJK，数字单独一档速率。
给出的操作建议是「区域宽度应比边界宽度留出约 5% 余量」。
出处：`skills/ppt-master/scripts/docs/svg-pipeline.md` 的「Measuring, wrapping, and calibrating text before authoring」。

**7. 生成按页串行。**
一页一页写，不用并行。文档写明并行生成实测出现过风格不一致。
出处：`docs/faq.md` 的「How long does a presentation take to generate?」。

### 能吸收的部分

- px 与 pt 的换算关系（`0.75`）与「整条链路只用一种单位」的纪律。
- 保真度分级这套词汇。我们的 `gate_exports.py` 与 `gate_layout.py` 报缺陷时可以直接借用「精确对应 / 归一化 / 近似 / 必须预渲染」四档来描述能力边界。
- 字号锚点表：三档阅读模式各给一个固定 px 值与一个容许区间，与本 skill 的 `presentation`、`reading`、`paper` 三档口径结构一致。
- 根组重叠 `1px` 与文字溢出 `5%` 这两个具体阈值。
- 行距按角色分区间，比本 skill 现在统一的 `1.22` 更细。
- 视觉复核的编号缺陷表格式，包括「实测值 + 阈值」的写法。
- 「区域宽度留 5% 余量」这条测量余量建议。

### 不能吸收的部分及原因

- 整套 SVG 中间语言与 187 个 Office preset 形状的编译管线。这套管线的前提是「页面先写成 SVG 再编译」，而本 skill 的输入是现成的参赛 pptx，版面来自参考件，没有从零绘制的环节。
- 16 家图片生成后端与图片检索管线。本 skill 的照片槽只接受使用者自己提供的照片。
- 品牌 / 风格 / 版式 / Deck 四类模板 workspace 体系。本 skill 的风格包是「从参考 pptx 抽出来的一整套页面」，抽取流程见 `references/CLONING-MECHANISM.md` 与 `engine/build_style.py`，不需要再套一层模板分类。
- 动画、转场、旁白、视频导出。参赛 PPT 的交付件是 pptx 与导出图，评审不要求动画。
- 仓库体量本身（13284 个文件）无法吸收进一个 skill 目录。

## 二、Gabberflast/academic-pptx-skill

| 项目 | 内容 |
| --- | --- |
| 仓库地址 | https://github.com/Gabberflast/academic-pptx-skill |
| 许可证 | MIT |
| Star | 1360 |
| 分支与最近提交 | `main`，2026-07-14 |
| 规模 | 4 个 Markdown 文件，约 210 KB |

### 核心做法

**1. 每一页标题必须陈述结论。**
标题写成完整句子说明「所以呢」，不写主题词。对照示例：主题词 `Results` 改成 `Treatment effect is significant across all three cohorts`。
`ghost deck test`：只按顺序读全部标题，应当能读出完整论证；读不出来说明结构需要改。
标题长度一到两行，字号 24–28pt 粗体。
出处：`content_guidelines.md` 第 2 节。

**2. 每页信息量有硬数字。**
正文最多约 40 词；正文最小 20pt，文档明确写「这是下限，不是目标，装不下就删内容」；每页 3–5 条 bullet，超过 5 条是警告信号；每条 bullet 只放一个观点。
出处：`content_guidelines.md` 第 4 节。

**3. 字号与边距用一套常量。**
`title: 26`（区间 24–28）、`sectionHeader: 22`、`body: 20`、`label: 16`、`cite: 13`；页边距 `0.5` 英寸；全篇只用一种字体。
出处：`slide_patterns.md` 的「Global Defaults」。

**4. 配色给出一套学术口径常量。**
`bg: FFFFFF`、`primary: 1F4E79`（深海军蓝，标题）、`accent: 2E75B6`（中蓝，页眉与高亮）、`body: 2D2D2D`（近黑正文）、`muted: 777777`（灰，引用与图注）、`rule: CCCCCC`（浅灰分隔线）、`highlight: FFF2CC`（黄，标注框，要求少用）。
出处：`slide_patterns.md` 的「Global Defaults」。

**5. 图表纪律：一页一张，关键点直接标注。**
每页只放一张图表、表、示意图、公式块或地图。图表必须直接标注关键数据点（箭头、标注框、高亮区域、或给焦点序列换色），不能让观众自己找。
图放在页面左侧，解读文字放右侧，符合从左到右的阅读顺序。
引用放在页脚，字号 12–14pt，用弱化色。
出处：`content_guidelines.md` 第 3 节、`slide_patterns.md` 第 5 节的「Critical checks for results slides」。

**6. 页数按演讲时长配。**
每分钟最多一页。10 分钟 8–10 页内容页，15 分钟 12–14 页，20 分钟 15–18 页，45 分钟 30–40 页。
排练目标是比时限提前 1–2 分钟结束。
出处：`content_guidelines.md` 第 7 节。

**7. 交付前是一张勾选清单。**
12 条：标题页含完整标题、作者、单位、会议、日期；每页都有 action title；ghost deck 通过；结果页每页一张图表且关键点已标注；每处借用数据都有页内引用；参考文献页完整；结论页是最后一个主页面且在问答期间留在屏幕上；结论页有联系方式或二维码；全篇正文 ≥20pt；没有一页正文超过约 40 词；附录页有编号且预置问答答案；排练后比时限提前 1–2 分钟。
出处：`slide_patterns.md` 的「Quick Checks Before Delivery」。

### 能吸收的部分

- action title 与 ghost deck test 这两条判据。本 skill 的 `gate_spec.py` 已经要求「主张非空」，可以再加一条「主张是完整句子、不是主题词」的判定。
- 40 词、20pt、3–5 条 bullet、每页一张图表这组数字，可以直接进 `QUANT-RULES.md` 作为参考基线。
- 字号层级常量（26 / 22 / 20 / 16 / 13）与本 skill 的 `ROLE_MIN_PT` 对照。
- 学术配色常量作为 `gate_palette.py` 的一个输入样本。
- 页数按分钟配的换算表。
- 交付前勾选清单的条目组织方式。

### 不能吸收的部分及原因

- 仓库只有 Markdown 与 pptxgenjs 代码片段，没有生成引擎。它把「怎么写 pptxgenjs」交给读者，本 skill 已经有 `engine/fill.py` 直接操作现成 pptx，不需要引入 pptxgenjs。
- 坐标全部写死在 `LAYOUT_16x9`（10 × 5.625 英寸）。本 skill 的版面来自参考件的 16:9 宽屏（33.87 × 19.05 cm），坐标系不同。
- 没有量化门脚本，判据只以文字形式存在，无法直接执行。

## 三、adithya-s-k/research-presentation-template

| 项目 | 内容 |
| --- | --- |
| 仓库地址 | https://github.com/adithya-s-k/research-presentation-template |
| 许可证 | MIT |
| Star | 8 |
| 分支与最近提交 | `main`，2026-07-27 |
| 规模 | 174 个文件，约 11.9 MB |

### 核心做法

**1. 主题是一组令牌，深色浅色成对。**
一个主题定义两套 `Palette`，字段固定：`bg`、`bgRaised`、`border`、`borderStrong`、`white`（最高对比前景）、`text`、`textMuted`、`textDim`、`accent`（结构与页饰）、`accentDim`、`accent2`（正文内强调）、`accent2Dim`、`diffPlus`、`diffMinus`。
页面代码不按模式分支，只换令牌值。三个主题 `forge`、`paper`、`carbon` 各带深色与浅色。
出处：`src/themes/index.ts`。

**2. 固定画布再等比缩放。**
`STAGE_W = 1280`、`STAGE_H = 720`，所有页按这套坐标写，整体等比缩放到任意投影尺寸，所以在任何投影上版面一致。
出处：`src/themes/index.ts` 末尾的「Design canvas」。

**3. 溢出做成可见徽标。**
开发模式下任何内容超出画布的页显示红色徽标。文档把这枚徽标定义为设计信号，并明确禁止用缩小字号把它压下去。
出处：`README.md` 的「An overflow guard」、`CLAUDE.md` 的「The three things people get wrong」第 1 条。

**4. 字号下限换算到 PowerPoint 口径。**
正文 ≥22px、bullet 约 34px、页标题约 46px、大主张 54–92px。
文档写明 1280 宽画布下 22px 相当于 PowerPoint 的 14pt，并说明「在阶梯教室后排，这已经是下限」。
出处：`CLAUDE.md` 的「The three things people get wrong」第 2 条。

**5. 一页一个想法。**
需要一段话才能讲清的内容拆成两页。
出处：`CLAUDE.md` 同节。

**6. 导出截图时隐藏界面元素。**
导出用 headless Chromium 逐页截图，页标题写进演讲备注。
两处已处理好的陷阱：Playwright 的 element screenshot 是视口裁剪而非元素渲染，任何覆盖在舞台上的东西都会进画面，所以界面元素打 `data-chrome` 标记并在截图时隐藏；framer-motion 的 spring 由 rAF 驱动，不会向 `document.getAnimations()` 报告完成，所以导出同时等一个稳定判定与一个固定下限。
持续动画的页没有最终状态，在 `DWELL` 表里给该页更长的停留时间，让它停在有代表性的一帧。
出处：`CLAUDE.md` 的「Animation, and how it interacts with export」。

**7. 定义完成是一张可执行清单。**
`npx tsc --noEmit` 干净；深浅两种模式都能渲染；至少再换一个主题渲染；开发模式下没有溢出徽标；没有裸十六进制颜色、没有写死标题作者、没有写死章节号。
出处：`CLAUDE.md` 的「Definition of done」。

### 能吸收的部分

- 主题令牌的字段划分：正文字、弱化文字、更弱文字、两档强调、增删两个差异色。这套字段可以补进 `references/CONTEST-DESIGN-TOKENS.md` 的令牌结构。
- 「固定画布再缩放」的做法。本 skill 的画布来自参考件，但 `qc.py` 生成 contact sheet 时可以固定一套审阅尺寸再缩放，便于逐页对比。
- 把溢出做成可见标记，而不是静默缩字。本 skill 的 `qc.py` 已经在 `fitreport.json` 里记录被压缩的槽位，可以把这个信号也画进 contact sheet。
- 导出截图时隐藏界面元素的 `data-chrome` 做法。本 skill 的 `qc.py` 目前用 LibreOffice 导 PDF 再转图，没有覆盖层问题，但将来若引入 HTML 预览需要这条。
- 定义完成清单的组织方式。

### 不能吸收的部分及原因

- React 组件体系与 framer-motion 动画。本 skill 的输出是 pptx，不是网页。
- Playwright 加 Chromium 的导出链。本 skill 的导出链是 python-pptx 存盘，再经 LibreOffice 转 PDF 与图。
- 它的主题令牌是给代码用的 TypeScript 类型，不能直接变成 Python 常量。

## 四、tristan-mcinnis/pptx-from-layouts-skill

| 项目 | 内容 |
| --- | --- |
| 仓库地址 | https://github.com/tristan-mcinnis/pptx-from-layouts-skill |
| 许可证 | MIT |
| Star | 38 |
| 分支与最近提交 | `main`，2026-08-30 |
| 规模 | 116 个文件，约 844 KB |

### 核心做法

**1. 三步管线，每一步都能单独校验。**
第一步 profile：把一份 pptx 变成版式目录 `catalog.md` 与渲染配置 `config.json`，每个模板做一次。
第二步 author：写 `slides.md`，每页写 `[HINT: layout_name]` 指定版式，`lint_hints.py` 校验提示名是否在目录里；提示名写错会退回自动推断并给出警告。
第三步 render：`generate.py` 按命名版式填充，再用 `validate.py` 校验。
出处：`SKILL.md` 的「The 3-step pipeline」。

**2. 核心命题是套用模板的母版版式与占位符，不在页面上叠文本框。**
出处：`SKILL.md` 开头。

**3. 版式目录按用途分类。**
随仓库的 Inner Chapter 模板有 59 个版式（索引 0–58），按 Title/Cover、Standard Content、Columns、Grids（图 + 文）、Image Layouts、Contact/Closing、Team、Special 分类，每类给出用途说明。
出处：`references/layouts.md`。

**4. 版式选择有固定顺序。**
依次问：有先后顺序吗 → `process-N-phase`；有对比吗 → `comparison-N`；是并列项吗 → `cards-N`；两个数字之间有张力吗 → `data-contrast`；是引言吗 → `quote-hero`；真是表格数据吗 → `table`；是一句话主张吗 → `hero-statement`；都不是 → `bullets`。
`bullets` 是最后手段，不是默认值。
出处：`rules/visual-types.md` 的「Decision Framework」。

**5. 每种版式给出内容长度上限。**
`timeline-horizontal` 的阶段描述 30 字符；`hero-statement` 主张 100 字符；`comparison-tables` 表头 25 字符；`process-N-phase` 每阶段 50 字符、最多 3–4 条；`cards-N` 每卡 60 字符、最多 4–5 条。
超出上限时的处理顺序：拆成多页、压缩措辞、换一个更宽松的版式。
出处：`rules/visual-types.md` 的「Content Length Guidelines」。

**6. 先度量再缩字，缩字有 70% 下限。**
先用 `check_text_overflow` 按目标字号量一次（快路径）。溢出时在 `70%` 下限与目标字号之间二分，找最大的能放下的整数磅值。字号只取整数磅，不用小数。
表格另算：同时收缩字号与行高，让全部行放进可用高度。
出处：`scripts/content_fitter.py` 的 `calculate_fit_font_size`，文档字符串写明「respecting a 70% floor」。

**7. 页边距用四边常量。**
13.333 × 7.5 英寸画布；左右各 `0.25` 英寸（文档注明 18pt 标准）、上 `0.40` 英寸（页眉带以下）、下 `0.50` 英寸；形状最小 0.5 英寸，避免退化形状。
出处：`lib/margins.py` 的 `DEFAULT_MARGINS` 与 `MIN_WIDTH_INCHES`。

**8. 编辑与重生成有分界线。**
文字级改动且少于 30% 页，用 `edit.py`（先导出行清单，改 JSON，再套回文件）；版式变化、增删页、超过 30% 页，用 `generate.py` 重生成。
出处：`rules/decisions.md` 的「Edit vs Regenerate」。

### 能吸收的部分

- 「版式目录 + 提示名校验」这一层结构。本 skill 的 `catalog.md` 加 `slots.json` 已经承担同样职责，`gate_content.py` 的「槽位存在」判据就是这套校验；可以补一条「提示名写错要给出明确报错」。
- 版式选择的固定顺序，可以进 `engine/plan.py` 作为「某段内容该用哪类版面」的判定依据。
- 每类版式的内容长度上限。本 skill 的 `slots.json` 里已有 `chars` 与 `per_paragraph`，`gate_content.py` 用 1.5 / 2.0 / 2.5 倍判据，可以再补一层「按版式类别的绝对上限」。
- 70% 缩字下限与整数磅二分。本 skill 的 `fit.py` 有 `ROLE_MIN_PT` 下限，但没有「相对目标字号的百分比下限」，这一条值得补。
- 四边页边距常量。本 skill 的 `gate_layout.py` 用 `MIN_MARGIN_CM = 0.25` 判页边留白，与它的左右 0.25 英寸口径接近，可以对照。
- 30% 编辑与重生成的分界线。本 skill 目前一律重生成，这条作为「小改动怎么办」的参考。

### 不能吸收的部分及原因

- pydantic schema 与九个 agent 定义（outline-architect、template-onboarder、deck-qa 等）。本 skill 是单 agent 流程，不需要再拆子角色。
- `content_fitter.py` 依赖同目录的 `visual_validator` 字体度量模块，那个模块没有随仓库公开完整路径，无法直接移植；做法可以照抄，代码不能照搬。
- Inner Chapter 模板本体（59 个版式）是第三方品牌模板，版权不在 MIT 覆盖范围内。

## 五、anthropics/skills 的 skills/pptx

| 项目 | 内容 |
| --- | --- |
| 仓库地址 | https://github.com/anthropics/skills（子目录 `skills/pptx`） |
| 许可证 | 仓库没有顶层 LICENSE（`license.spdx_id` 返回 null）。`skills/pptx/LICENSE.txt` 写明「© 2025 Anthropic, PBC. All rights reserved.」，使用受 Anthropic 服务协议约束 |
| Star | 183921 |
| 分支与最近提交 | `main`，2026-10-09 |
| 规模 | 仓库 541 个文件；`skills/pptx` 子目录 6 个 Markdown 与脚本文件 |

这个仓库的许可不允许复制代码与提示词正文。下面只记录它披露的做法与陷阱清单，本 skill 不引入任何一行它的代码。

### 核心做法（只读）

**1. pptxgenjs 的损坏陷阱清单。**
`pres.layout` 必须在加页之前设定；默认画布是 `LAYOUT_16x9` = 10 × 5.625 英寸，不是 13.3 英寸，超出的坐标会被写进文件但形状不显示。
十六进制颜色不能带 `#`、不能写成 8 位；把透明度烘进十六进制（例如 `00000020`）会损坏文件；半透明要用 `transparency: 0-100`，阴影用 `opacity: 0.0-1.0`，两者互换会被静默忽略。
pptxgenjs 会就地改写传入的选项对象（首次使用时把值转成 EMU），同一个 `shadow` 或选项对象不能跨两次 `add*` 调用复用，必须每次新建。
阴影 `offset` 必须 ≥ 0，负值损坏文件；要向上投影用 `angle: 270` 配正的 offset。
`letterSpacing` 会被静默忽略，真实选项名是 `charSpacing`。
列表要在每一项上写 `bullet: true`，不要写字符 `•`（会渲染成双层圆点）；数组里除最后一项都要设 `breakLine: true`；段落间距用 `paraSpaceAfter`，用 `lineSpacing` 会撑出巨大空隙。
一个输出文件只建一个 `new pptxgen()` 实例。
`rectRadius` 只对 `ROUNDED_RECTANGLE` 生效，对 `RECTANGLE` 无效。
不支持渐变填充，需要渐变时用一张渐变图做背景。
文本框自带内边距；文字需要与形状、线、图标在同一条 x 上对齐时，必须设 `margin: 0`。
演讲备注写进 `slide.addNotes("...")`，不要放到页面上的文本框里。
堆叠柱状图或堆叠柱图的 `dataLabelPosition` 只能是 `ctr`、`inEnd`、`inBase`，写 `outEnd` 会损坏文件。
组合图用 `secondaryValAxis` / `secondaryCatAxis` 时，必须同时给 `valAxes` 与 `catAxes` 各两项；只给 `valAxes` 不够，pptxgenjs 会写出它没有声明的坐标轴 id，PowerPoint 会丢弃整张图表并把文件报为损坏。
不要重排 `<p:presentation>` 的子元素顺序；pptxgenjs 把 `<p:notesMasterIdLst>` 写在 `<p:sldIdLst>` 之后并让两个母版共用同一个主题部件，PowerPoint 能读，把元素挪位之后同一份文件会打不开。
出处：`skills/pptx/SKILL.md` 的「Creating with pptxgenjs — gotchas」。

**2. python-pptx 的三处做不到。**
不能复制页，唯一入口是 `add_slide(layout)`。
`text_frame.text = "..."` 会把整段压成一个无格式 run，要保留格式必须逐个改 `run.text`。
读不了模板美术常用的 SVG 与 EMF，`add_picture` 会抛 `UnidentifiedImageError`。
出处：`skills/pptx/SKILL.md` 的「Editing existing decks and templates」。

**3. 结构改动先做完，再改内容。**
`add_slide.py` 原样复制页文件，所以先编辑再复制会克隆已编辑的内容；`clean.py` 会删掉不在 `<p:sldIdLst>` 里的页，包括刚写好的那一页。
不要手工复制页文件；`add_slide.py` 会完成新页需要的全部注册并打印它做了什么。直接对文件用时必须传 `-o`，否则会就地改写输入文件。
复制出来的页仍然引用源页的图表、SmartArt、嵌入对象部件，不复制那些部件，所以改其中一页的图表会连带改另一页。
出处：`skills/pptx/SKILL.md` 同节。

**4. 模板填槽的删减纪律。**
模板里画了 4 个成员而实际只有 3 个时，要删掉第 4 个成员的整组（图片加文本框），不能只删文字，删完要在质检里查有没有留下孤立视觉元素。
一个列表项对应一个 `<a:p>`，不要把所有项拼进一个段落；复制兄弟 `<a:pPr>` 保留间距；标题、小标题、行内标签（`Status:`、`Owner:`）要在 `<a:rPr>` 上写 `b="1"`。
列表符号从版式继承，只在需要覆盖时写 `<a:buChar>`、`<a:buAutoNum>`、`<a:buNone>`，永远不要在文字里写字符 `•`。
带前后空格的文字需要在 `<a:t>` 上写 `xml:space="preserve"`。
出处：`skills/pptx/SKILL.md` 的「When filling in a template」。

**5. 校验脚本的判据清单。**
`validate.py` 依次做：XML 合法性、命名空间、唯一 id、UUID、文件引用、版式 id、content-type、XSD、备注页引用、关系 id、重复版式、母版主题唯一性、图表、逐页检查。
模板派生的成品必须传 `--original`：模板自身可能带有 XSD 不接受的部分，不传会把模板自己的错误报成你的错误，真正的回归会藏在里面。
结构性检查（关系、content-type、图表）忽略 `--original`，模板继承来的问题照报。
出处：`skills/pptx/SKILL.md` 的「QA (Required)」与 `scripts/office/validators/pptx.py`。

**6. 缩略图网格的参数。**
每页缩略图宽 300px、转换 100 dpi、最多 6 列（默认 3 列）、JPEG 质量 95、网格内边距 20、边框 2、标签字号按缩略图宽 0.10 比例。超过 12 页拆成多张。
出处：`scripts/thumbnail.py` 顶部常量。

**7. 视觉质检的检查顺序。**
先查文字溢出或被裁（最常见且一定被看见）；再查元素重叠、引用与页脚与上方内容碰撞、元素间距小于 0.3 英寸、距页边小于 0.5 英寸、列不对齐、低对比度文字、模板装饰在替换文字后错位（例如标题下划线按一行画，替换后的标题折成两行）、低对比度图标、文本框过窄导致折行过多、遗留占位内容。
出处：`skills/pptx/SKILL.md` 的「Visual QA」。

### 能吸收的部分

- pptxgenjs 的陷阱清单本身。本 skill 不用 pptxgenjs，但同类问题在 python-pptx 与直接改 OOXML 时同样成立（负偏移、颜色格式、选项对象复用、元素顺序）。这份清单可以作为 `references/GATES-USAGE.md` 之外的「已知损坏源」附录。
- python-pptx 的三处做不到。本 skill 的 `fill.py` 走的是逐 run 改写与复制形状的路线，这三条正好解释了为什么不能走捷径。
- 「结构改动先做完再改内容」的顺序纪律。`engine/make_pack.py` 一次性分离装饰与正片，符合这条。
- 模板填槽删整组。`make_pack.py` 清空文字后把照片换成同尺寸灰框，思路一致，可以补一条「删掉多余成员的整组」。
- `--original` 基线对比的思路。`gate_exports.py` 目前没有基线对比，值得补。
- 缩略图网格的具体参数，可直接对照 `qc.py` 的 contact sheet 参数。
- 视觉质检的检查顺序（文字溢出优先）。

### 不能吸收的部分及原因

- 任何代码与提示词正文。许可写明保留全部权利，只能读做法。
- `markitdown` + `soffice` + `pdftoppm` 这条依赖链。本 skill 用 LibreOffice 直接转 PDF 再转图，不引入 markitdown。
- 它的 `unpacked/` 解包改 XML 再打包的编辑路线。本 skill 用 python-pptx 对象模型改写，避免手工改 XML 带来的命名空间与前缀损坏风险。

## 六、addsumtech/slides_maker

| 项目 | 内容 |
| --- | --- |
| 仓库地址 | https://github.com/addsumtech/slides_maker |
| 许可证 | MIT |
| Star | 629 |
| 分支与最近提交 | `main`，2026-10-23 |
| 规模 | 495 个文件，约 322 MB |

### 核心做法

**1. 交付模式记录成文件，不靠命令行开关。**
`dk.declare_delivery(OUT, "presented")` 把交付模式写进 `<deck 目录>/.deck-gates.json`，可选值 `presented`、`textheavy`、`selfread`、`surface`、`briefing`。
`lint_deck.py` 与 `render_deck.py --gate-check` 都读这个文件，记录值优先于冲突的命令行开关，并且会说明冲突来自哪个文件。
理由写得很直白：模式只活在命令行开关里就变成「靠记忆携带的事实」，一定会被漏掉。实测一份 14 页自读稿在无开关时输出 20 行统计，加 `--selfread` 后只剩 10 行，多出来的 10 行是把约 40 词的「讲解」预算套到没人讲的稿子上。
出处：`skills/slide-maker/SKILL.md` 相关段落。

**2. 每页阅读量有预算，按交付模式分档。**
阅读量算法：拉丁词数 + CJK 字数 ÷ 2。
预算：`presented` 约 40 词、`selfread` 约 90 词、`briefing` 约 150 词、`surface`（海报、单页）不设每页预算；超过预算给 `TEXT WALL` 警告。
出处：`scripts/lint_deck.py` 的预算计算段与 `SKILL.md`。

**3. 版面占用率按页角色给区间。**
封面与分隔页 25–35%、执行摘要 45–60%、技术页与证据页 55–70%；超过约 70–75% 判 `CROWDED`。
占用率按墨迹面积算，不是按留白面积算，文档专门提醒读区间时要按墨迹理解。
出处：`SKILL.md` 的 DECK STATS 段。

**4. 字号纪律。**
正文中位数字号低于「画布相对的约 18pt 等效下限」判 `SMALL TYPE`，处理方式是减少字数、放大字号，不允许缩字硬塞。
单页不同字号数超过 3–4 判 `SIZE SPRAWL`。
正文必须明显小于页标题，不能同号也不能更大；层级比约 1.4–1.8×（标题 24–30pt、正文 16–18pt）；公式、大数字、卡片标签可以超过正文，但作为辅助信息时仍要小于标题。
出处：`references/design-principles.md` 的「Visual hierarchy」与 `scripts/lint_deck.py` 的 `_size_clusters`。

**5. 对比度判据按 WCAG 1.4.3 的「大字」定义写死。**
正文（小于 14pt 任意字重，或小于 18pt 且不是粗体）对底衬低于 4.5:1 判失败；大字（≥18pt，或 ≥14pt 粗体）按 3:1。
非文字元素（实心标记、线条、图标）按 WCAG 1.4.11 的 3:1。
文字压在照片或渐变上且没有实底时单独估一档：低于 1.5:1 判失败，1.5–3.0 给警告。
弱化色不等于低对比：建议压低饱和度、保留明度差，并给出例子 `#6E6557` 在米色上是 4.6:1，`#9A927F` 是 2.7:1。
出处：`scripts/lint_deck.py` 的对比度段、`references/design-principles.md` 的「Accessibility」、`scripts/palette_audit.py` 顶部注释。

**6. 版面硬缺陷族。**
越界、文字溢出卡片、卡片内边距不足（`PAD = 0.09` 英寸，同时抓「压过卡片」与「贴住卡片边缘」两种）、同行卡片高度不均、两个实心块或图重叠且互不包含、页脚碰撞、孤行标点（避头尾，最后一行只剩 `。` 或 `，`）、孤字（最后一行只剩一个 CJK 字）、CJK 文字没有东亚字体（这是避头尾失效的根因）、整页图片、空白页或只有背景的页。
另有软警告：图片缺 alt 文本、公式字体缺字、分组内内容过多导致难以编辑、缺页标题、页标题重复、阅读顺序异常。
出处：`scripts/lint_deck.py` 的几何与文字检查段、`SKILL.md` 的 lint 说明。

**7. OOXML 安全：PowerPoint 会修复或删除的值。**
`outerShdw` / `innerShdw` / `prstShdw` / `reflection` / `lin` 的 `dir`、`ang`、`fadeDir` 必须在 `0..21599999`（`ST_PositiveFixedAngle`），负值会被 PowerPoint 删掉。
`blurRad`、`dist`、`rad` 不能为负（`ST_PositiveCoordinate`）。
`gs pos` 必须在 `0..100000`（`ST_PositiveFixedPercentage`）；`alpha val` 必须在 `0..100000`。
`rPr` / `defRPr` / `endParaRPr` 的 `spc` 必须在 `-400000..400000`。
`spPr` 的子元素必须按 `xfrm, custGeom, prstGeom, noFill, solidFill, gradFill, blipFill, pattFill, grpFill, ln, effectLst, effectDag, scene3d, sp3d, extLst` 顺序；`rPr` 的子元素必须按 `ln, noFill, solidFill, ..., latin, ea, cs, sym, hlinkClick, hlinkMouseOver, rtl, extLst` 顺序。
同一页上 `p:cNvPr` 的 id 不能重复。
`beyond_page()` 报出超出页面边缘 0.02 英寸以上的非文字形状，旋转的形状按旋转后的外接框算；声明过出血（`bleed_intent`）的形状不报。
出处：`scripts/ooxml_safety.py` 顶部注释与常量、`xml_findings`、`beyond_page`。
这份清单的价值在于它的成因记录：某份稿在 LibreOffice 里渲染干净、全部 lint 通过，PowerPoint 打开时提示「无法读取部分内容，已修复并删除」，原因就是软阴影写成了 `dir="-5400000"`。所有基于渲染的检查都看不见这一类缺陷，只能从 XML 里读。

**8. 渲染后必须看图。**
python-pptx 静默排字：不报溢出、不报标注压在页脚上、不报低对比、不报缺字形。确认一页对不对的唯一办法是渲染成图再看。
出处：`references/design-principles.md` 末节。

### 能吸收的部分

- 交付模式记录成文件的做法。本 skill 的 `--profile` 三档（`presentation`、`reading`、`paper`）目前只活在命令行，可以写进 `成品.gates.json`，让后续复跑读到同一个档位。
- 每页阅读量的三档数字（40 / 90 / 150 词）与「拉丁词 + CJK 字数 ÷ 2」这个混排算法。本 skill 的 `MAX_PAGE_CHARS = 220` 只有一档，且按字符数算。
- 版面占用率区间（25–35 / 45–60 / 55–70%）。这是一条本 skill 没有的判据。
- 字号层级比 1.4–1.8× 与「正文不得与标题同号或更大」这条硬约束。
- WCAG 1.4.3 的「大字」阈值（≥18pt 或 ≥14pt 粗体按 3:1）。本 skill 的 `gate_palette.py` 只有 4.5 与 7.0 两档，缺这一档。
- 卡片内边距 0.09 英寸这条判据，抓的是「贴住边缘」而非「压过边缘」。
- 孤行标点与孤字的检测。中文 PPT 里「。」被挤到单独一行是最常见的排版瑕疵，本 skill 的 `gate_layout.py` 没有这条。
- OOXML 取值范围与子元素顺序清单。这是本次调研里最可直接执行的一组判据，可以扩成 `gate_exports.py` 的一节，或单独一个 `gate_ooxml.py`。
- 「渲染后必须看图」这条纪律，与本 skill 的 `qc.py` 分工一致，可以互相印证。

### 不能吸收的部分及原因

- `vl_specs` 的 29 套视觉语言与 `vl_langs` 的 16 套实现。本 skill 的七个风格包来自真实参赛件，不需要再造一套视觉语言分类。
- agent 与 critic panel 体系（arbiter、blind-reader、critic、content-planner 等）。本 skill 是单 agent 流程。
- `deckkit` 组件库与 `deckkit.lint_layout` 的进程内检查。本 skill 的检查全部针对已存盘的 pptx，不构建中间对象。
- 图片生成、图片溯源、图片序列一致性那套体系。本 skill 的照片来自使用者。
- 仓库体量（322 MB，其中大量是视觉语言样例与测试）。

## 七、许可不允许内化的仓库

下面三个仓库只记录定位与许可，不吸收任何做法与代码。

| 仓库 | 地址 | 许可证 | Star | 定位 |
| --- | --- | --- | --- | --- |
| GordenSun/GordenPPTSkill | https://github.com/GordenSun/GordenPPTSkill | 仓库 API 返回 `NOASSERTION`。`LICENSE` 正文是 MIT，但明确写明「The MIT license above applies to the **source code only**」，`templates/` 下的 PPT 模板另有非商业声明，仅供个人学习与研究 | 3796 | 17 套中文 PPTX 模板加基于 python-pptx 的非破坏性改文字工具，选模板后写 `edits.json` 生成 pptx |
| op7418/guizang-ppt-skill | https://github.com/op7418/guizang-ppt-skill | AGPL-3.0 | 28703 | 单文件 HTML 横向翻页 PPT，两套视觉系统（电子杂志 × 电子墨水、瑞士国际主义），配图与封面生成 |
| chuspeeism/dashi-ppt-skill | https://github.com/chuspeeism/dashi-ppt-skill | AGPL-3.0 | 10045 | 浏览器内可编辑的网页 PPT，12 套视觉主题，可导出 HTML、PDF 与 PPTX |

排除原因：
GordenPPTSkill 的模板部分是非商业许可，内化模板会违反许可；代码部分虽然可用 MIT，但它的核心价值在模板，剥掉模板后剩下的改文字工具与 `engine/fill.py` 职责重叠。
两个 AGPL-3.0 仓库的传染性条款会覆盖本 skill 的分发方式，本 skill 要作为可自由分发的 skill 目录存在，不能引入 AGPL 代码。
三者都没有本 skill 需要而前六个仓库缺失的判据。

## 八、可操作知识汇总

这一节把散在各仓库的具体数字与陷阱集中列出，便于直接对照实现。

### 字号下限

| 来源 | 角色 | 数值 | 折算到 16:9 宽屏 |
| --- | --- | --- | --- |
| Gabberflast | 正文 | 20pt | 20pt（下限，不是目标） |
| Gabberflast | 标题 | 24–28pt | 24–28pt |
| addsumtech | 正文 | 画布相对的 ≈18pt 等效 | ≈18pt（13.333 in 宽画布） |
| addsumtech | 标题 | 24–30pt | 24–30pt |
| adithya-s-k | 正文 | 22px | ≈14pt |
| adithya-s-k | bullet | ≈34px | ≈22pt |
| adithya-s-k | 页标题 | ≈46px | ≈30pt |
| adithya-s-k | 大主张 | 54–92px | ≈36–62pt |
| tristan-mcinnis | 缩字下限 | 目标字号的 70% | 相对值 |
| hugohe3 | 正文锚点 | 20px / 24px / 32px（三档阅读模式） | 15pt / 18pt / 24pt |

对照本 skill 的 `ROLE_MIN_PT`：`presentation` 档正文 16pt、标题 18pt、headline 24pt、display 36pt。Gabberflast 与 addsumtech 的正文下限（18–20pt）比本 skill 的 16pt 更严，本 skill 取 16pt 是因为参赛件的参考页本身就是这个量级，改高会挤压复刻出来的版面。

### 行数与每页信息量

| 来源 | 判据 | 数值 |
| --- | --- | --- |
| Gabberflast | 每页正文词数 | 约 40 词 |
| Gabberflast | 每页 bullet 条数 | 3–5 条，超过 5 条是警告 |
| addsumtech | 每页阅读量（讲解档） | 约 40 词（拉丁词 + CJK 字数 ÷ 2） |
| addsumtech | 每页阅读量（自读档） | 约 90 词 |
| addsumtech | 每页阅读量（数据简报档） | 约 150 词 |
| addsumtech | 版面占用率 | 封面 25–35%、执行摘要 45–60%、技术页 55–70%，超过 70–75% 判拥挤 |
| 本 skill | 单页可见字数 | 220 字 |
| 本 skill | 正文折行行数 | 6 行 |
| tristan-mcinnis | 每类版式的内容长度上限 | timeline 30 字符、hero 100 字符、表头 25 字符、process 50 字符/条、cards 60 字符/条 |

### 字号层级与间距

| 来源 | 判据 | 数值 |
| --- | --- | --- |
| addsumtech | 标题与正文字号比 | 1.4–1.8× |
| addsumtech | 单页不同字号数 | 不超过 3–4 |
| addsumtech | 卡片内边距 | 0.09 英寸 |
| addsumtech | 行距（CJK 正文） | `line_spacing` 1.08–1.21（约 1.3–1.45× 字号） |
| hugohe3 | 多行标题行距 | 1.2–1.3× 字号 |
| hugohe3 | 密集小正文行距 | 1.4–1.5× 字号 |
| hugohe3 | 普通正文行距 | 1.5–1.6× 字号 |
| hugohe3 | 大字稀疏正文行距 | 1.6–2.0× 字号 |
| hugohe3 | 相邻基线最小间距 | 1.05× 较大字号（低于此值告警） |
| tristan-mcinnis | 左右页边距 | 0.25 英寸（18pt） |
| tristan-mcinnis | 上边距 | 0.40 英寸（页眉带以下） |
| tristan-mcinnis | 下边距 | 0.50 英寸 |
| 本 skill | 页边留白下限 | 0.25 cm |
| 本 skill | 行高比例 | 1.22 |

### 对比度

| 来源 | 判据 | 数值 |
| --- | --- | --- |
| addsumtech | 正文（WCAG 1.4.3 非大字） | ≥4.5:1 |
| addsumtech | 大字（≥18pt，或 ≥14pt 粗体） | ≥3:1 |
| addsumtech | 非文字元素（WCAG 1.4.11） | ≥3:1 |
| addsumtech | 文字压在照片或渐变上 | <1.5:1 失败，1.5–3.0 警告 |
| hugohe3 | 小字 | ≥4.5 |
| hugohe3 | 字号 ≥24px | ≥3.0 |
| 本 skill | 正文对背景 | 低于 4.5 失败，低于 7.0 警告 |

### pptx 与 OOXML 的损坏陷阱

| 来源 | 陷阱 | 后果 |
| --- | --- | --- |
| anthropics | 十六进制颜色带 `#` 或写成 8 位（含 alpha） | 文件损坏 |
| anthropics | 阴影 `offset` 为负 | 文件损坏 |
| anthropics | 同一个选项对象跨两次 `add*` 复用 | 值被就地改写成 EMU，第二次调用拿到错误数值 |
| anthropics | 堆叠图的 `dataLabelPosition` 写 `outEnd` | 文件损坏 |
| anthropics | 组合图只给 `valAxes` 不给 `catAxes` | 写出未声明的坐标轴 id，PowerPoint 丢弃整张图表并报文件损坏 |
| anthropics | 重排 `<p:presentation>` 的子元素 | 文件打不开 |
| anthropics | 用 `text_frame.text = "..."` 整段赋值 | 段落被压成单个无格式 run |
| anthropics | 手工复制页文件、编辑后再复制 | 克隆已编辑内容；`clean.py` 删掉刚写好的页 |
| addsumtech | `outerShdw dir` 写成负数 | PowerPoint 删掉该效果并提示修复 |
| addsumtech | `blurRad` / `dist` / `rad` 为负 | 同上 |
| addsumtech | `gs pos` 或 `alpha val` 超出 0..100000 | 同上 |
| addsumtech | `rPr spc` 超出 -400000..400000 | 同上 |
| addsumtech | `spPr` 与 `rPr` 的子元素顺序错 | 同上 |
| addsumtech | 同页 `p:cNvPr` id 重复 | 同上 |
| 本 skill | 这三个仓库的陷阱都发生在「LibreOffice 渲染干净、基于渲染的检查全部通过」之后 | 只有从 XML 里读才能发现 |

### 模板母版与版式继承

| 来源 | 做法 |
| --- | --- |
| tristan-mcinnis | 三步管线：把模板 profile 成版式目录（名称 + 索引 + 用途），作者只写版式名，渲染器按名填充；提示名写错时退回自动推断并告警 |
| tristan-mcinnis | 核心命题：使用模板的 slide-master layout 与 placeholder，不在页面上叠文本框 |
| anthropics | 填模板时删掉多余成员的整组（图 + 文本框），不是只删文字；删完查孤立视觉元素 |
| anthropics | 一个 `<a:p>` 一个列表项；复制兄弟 `<a:pPr>` 保留间距；行内标签在 `<a:rPr>` 写 `b="1"` |
| anthropics | 列表符号从版式继承，只在需要覆盖时写 `buChar` / `buAutoNum` / `buNone` |
| anthropics | 带前后空格的文字需要 `xml:space="preserve"` |
| anthropics | 模板派生的成品校验必须传 `--original` 做基线，否则模板自带的 XSD 错误会被报成自己的错误 |
| hugohe3 | 平铺结构（`flat`）与结构化结构（`structured`）二选一；需要可复用母版时先用 create-template 造一份 workspace，导出器不猜母版与占位符拓扑 |
| 本 skill | `engine/make_pack.py` 清空文字保留版面，装饰与正片分离，生成 `slots.json`；`engine/fill.py` 按槽位改写 run |

### 溢出检测的实现方式

| 来源 | 方式 |
| --- | --- |
| tristan-mcinnis | 先按目标字号度量一次，溢出则在 70% 下限与目标字号之间二分找最大整数磅值；字号只取整数 |
| hugohe3 | 根组声明 `data-pptx-bounds`，判根组互相重叠超过 1px、模块文字溢出超过 5%；文字宽度用内置字形前进量估算，区域宽度留 5% 余量 |
| addsumtech | 进程内 `lint_layout` 先清纯几何缺陷，存盘后 `lint_deck.py` 再按渲染像素复核一遍；卡片内边距 0.09 英寸；旋转形状按旋转后外接框算 |
| adithya-s-k | 开发模式下超画布的页显示红色徽标，作为设计信号 |
| 本 skill | `engine/fit.py` 按框宽折行再按框高收字号；`gate_layout.py` 判溢出 8%、越界 0.05 cm、重叠 30%、遮挡 25%；`qc.py` 导出 contact sheet 供人眼复核 |

### 校验脚本的判据

| 来源 | 判据 |
| --- | --- |
| anthropics `validate.py` | XML 合法性、命名空间、唯一 id、UUID、文件引用、版式 id、content-type、XSD、备注页引用、关系 id、重复版式、母版主题唯一性、图表、逐页检查；`--original` 做基线 |
| anthropics `thumbnail.py` | 缩略图宽 300px、100 dpi、最多 6 列、JPEG 95、网格内边距 20、边框 2、标签字号 0.10 比例、超过 12 页拆分 |
| addsumtech `lint_deck.py` | 越界、文字溢出卡片、内边距不足、卡片高度不均、实心块重叠、页脚碰撞、孤行标点、孤字、CJK 无东亚字体、整页图片、空白页、文字墙、拥挤、字号蔓延、字号下限、层级比、对比度、缺标题、重复标题、阅读顺序 |
| addsumtech `ooxml_safety.py` | 角度范围、正坐标范围、百分比范围、字符间距范围、`spPr` 与 `rPr` 子元素顺序、同页 shape id 重复、超出页面边缘 0.02 英寸 |
| hugohe3 `svg_quality_checker.py` | 只接受白名单属性、XML 必须合法、根组必须有 bounds、重叠与溢出阈值、标记必须闭合 |
| 本 skill | `gate_spec` 主张非空与 `spec_complete=Y`；`gate_content` 字数倍率与字号下限；`gate_layout` 越界、溢出、遮挡、重叠、字号、层级、居中、变形；`gate_palette` 色觉缺陷、灰度、对比度、单页色数；`gate_numbers` 数字可追溯；`gate_exports` 签名、dpi、页数、像素上限、体积 |

## 九、吸收清单

「落到哪个文件」指本 skill 目录 `C:/Users/876762330/.dsh/skills/career-ppt-cloner` 下的相对路径。
状态取值：已实现（现有代码已覆盖）、待实现（判据明确但尚未写进代码或文档）、不适用（与本 skill 的输出形态或输入形态不匹配）。

| 做法 | 落到哪个文件 | 状态 |
| --- | --- | --- |
| 字号下限按角色与口径档位取值 | `engine/rules.py` 的 `ROLE_MIN_PT`、`references/QUANT-RULES.md` | 已实现 |
| 字号层级比判据 | `engine/rules.py` 的 `HIERARCHY_RATIO = 1.2`、`engine/gate_layout.py` | 已实现 |
| 正文与标题不得同号 | `engine/gate_layout.py` | 待实现 |
| 层级比取 1.4–1.8×（比现有 1.2 更严） | `engine/rules.py` 的 `HIERARCHY_RATIO` | 待实现 |
| 单页不同字号数上限 3–4 | `engine/gate_layout.py`、`references/QUANT-RULES.md` | 待实现 |
| 每页可见字数上限 | `engine/rules.py` 的 `MAX_PAGE_CHARS = 220`、`engine/gate_content.py` | 已实现 |
| 每页阅读量按交付模式分三档（40 / 90 / 150 词） | `engine/rules.py`、`engine/gate_content.py` | 待实现 |
| 混排阅读量算法（拉丁词 + CJK 字数 ÷ 2） | `engine/gate_content.py` | 待实现 |
| 正文折行行数上限 6 | `engine/rules.py` 的 `MAX_BODY_LINES` | 已实现 |
| 每类版式的绝对内容长度上限 | `styles/*/slots.json` 的 `chars`、`per_paragraph`，`engine/gate_content.py` | 已实现（按倍率判定） |
| 缩字 70% 相对下限 | `engine/fit.py`、`engine/gate_content.py` | 待实现 |
| 缩字只取整数磅 | `engine/fit.py` | 待实现 |
| 行距按角色分区间 | `engine/rules.py` 的 `LINE_HEIGHT_RATIO`、`engine/fit.py` | 待实现 |
| 行距写成正数 `dy` 而非 CSS 行高 | `engine/fill.py` | 不适用（本 skill 操作 pptx 段落属性） |
| 页边留白下限 | `engine/rules.py` 的 `MIN_MARGIN_CM = 0.25`、`engine/gate_layout.py` | 已实现 |
| 四边页边距各自取值（上 0.40 / 下 0.50 英寸） | `engine/gate_layout.py` | 待实现 |
| 卡片内边距下限 0.09 英寸 | `engine/gate_layout.py` | 待实现 |
| 溢出比例判据 | `engine/gate_layout.py` 的 8% | 已实现 |
| 越界判据 | `engine/rules.py` 的 `BOUNDARY_TOLERANCE_CM = 0.05`、`engine/gate_layout.py` | 已实现 |
| 遮挡与重叠判据 | `engine/rules.py` 的 `OCCLUSION_RATIO = 0.25`、`engine/gate_layout.py` | 已实现 |
| 根组重叠 1px、模块文字溢出 5% 两档阈值 | `engine/gate_layout.py` | 待实现（现有阈值是 8% 单档） |
| 文字宽度估算留 5% 余量 | `engine/fit.py` | 待实现 |
| 文字与底衬框居中容差 | `engine/rules.py` 的 `CENTRE_TOLERANCE_CM = 0.15`、`engine/align.py` | 已实现 |
| 对比度 4.5 / 7.0 两档 | `engine/rules.py` 的 `CONTRAST_MIN`、`CONTRAST_COMFORT`、`engine/gate_palette.py` | 已实现 |
| 大字按 3:1（≥18pt 或 ≥14pt 粗体） | `engine/gate_palette.py` | 待实现 |
| 非文字元素按 3:1 | `engine/gate_palette.py` | 待实现 |
| 文字压在照片或渐变上的单独档（1.5 / 3.0） | `engine/gate_palette.py` | 待实现 |
| 色觉缺陷与灰度可混淆判据 | `engine/gate_palette.py` 的 Machado 矩阵与 deltaE 12、灰度差 0.03 | 已实现 |
| 单页配色数上限 6 | `engine/rules.py` 的 `MAX_PAGE_COLORS`、`engine/gate_palette.py` | 已实现 |
| 交付模式记录成文件（复跑读到同一档位） | `engine/gate_all.py` 写 `成品.gates.json`、`references/GATES-USAGE.md` | 待实现 |
| 主张必须陈述结论（action title） | `engine/plan.py`、`engine/gate_spec.py` 的主张非空判据、`references/SLIDE-SPEC.md` | 待实现（现有只判非空，不判句式） |
| ghost deck 检查（只读标题能否读出完整论证） | `engine/gate_spec.py` | 待实现 |
| 页数按演讲时长配（每分钟最多一页） | `engine/plan.py` | 待实现 |
| 版式目录加提示名校验 | `styles/*/catalog.md`、`styles/*/slots.json`、`engine/gate_content.py` 的槽位存在判据 | 已实现 |
| 版式选择的固定顺序（顺序 → 对比 → 并列 → 数字张力 → 引言 → 表格 → 单句 → bullet） | `engine/plan.py` | 待实现 |
| 结构改动先做完再改内容 | `engine/make_pack.py`（一次性分离装饰与正片） | 已实现 |
| 模板填槽删掉多余成员的整组 | `engine/make_pack.py` | 待实现 |
| 照片槽未填时换成同尺寸灰框 | `engine/make_pack.py`、`engine/build_style.py` | 已实现 |
| 一个列表项一个 `<a:p>`、复制兄弟 `<a:pPr>` | `engine/fill.py` | 已实现 |
| 带前后空格的文字写 `xml:space="preserve"` | `engine/fill.py` | 待实现 |
| 不手工复制页、不手工改 XML | `engine/fill.py` 走 python-pptx 对象模型 | 已实现 |
| 逐 run 改写而非整段赋值 | `engine/fill.py` | 已实现 |
| `--original` 基线对比 | `engine/gate_exports.py` | 待实现 |
| OOXML 角度、坐标、百分比、字符间距取值范围 | `engine/gate_exports.py` | 待实现 |
| OOXML `spPr` 与 `rPr` 子元素顺序 | `engine/gate_exports.py` | 待实现 |
| 同页 `p:cNvPr` id 重复 | `engine/gate_exports.py` | 待实现 |
| 超出页面边缘 0.02 英寸的形状（旋转按外接框） | `engine/gate_layout.py` | 待实现 |
| 孤行标点与孤字（避头尾） | `engine/gate_layout.py` | 待实现 |
| CJK 文字缺东亚字体 | `engine/gate_layout.py` | 待实现 |
| 整页图片导致不可编辑 | `engine/gate_layout.py` | 待实现 |
| 空白页或只有背景的页 | `engine/gate_layout.py` | 已实现（规格门与内容门间接覆盖） |
| 版面占用率区间 | `engine/gate_layout.py` | 待实现 |
| 缩略图网格参数（宽 300px、100 dpi、最多 6 列、JPEG 95、超过 12 页拆分） | `engine/qc.py` | 已实现（参数可对照调整） |
| 视觉质检顺序（文字溢出优先） | `SKILL.md` 第 7 节、`references/GATES-USAGE.md` | 已实现 |
| 渲染后必须看图 | `engine/qc.py`、`SKILL.md` 第 7 节 | 已实现 |
| 导出截图时隐藏界面元素 | `engine/qc.py` | 不适用（无 HTML 覆盖层） |
| 固定画布再缩放 | `engine/qc.py` | 不适用（画布来自参考 pptx） |
| px 与 pt 的 0.75 换算 | `engine/fit.py` | 不适用（直接操作 pt 与 EMU） |
| 保真度四级词汇（精确 / 归一化 / 近似 / 必须预渲染） | `references/QUANT-RULES.md`、`references/GATES-USAGE.md` | 待实现 |
| 主题令牌字段划分（正文字、两档弱化、两档强调、增删差异色） | `references/CONTEST-DESIGN-TOKENS.md` | 待实现 |
| 学术配色常量（`1F4E79` / `2E75B6` / `FFF2CC` 等） | `engine/palette_presets.py`、`references/CONTEST-DESIGN-TOKENS.md` | 待实现 |
| 一页一张图表、关键点直接标注 | `references/WRITING-RULES.md` | 待实现 |
| 图表放左、解读放右 | `references/WRITING-RULES.md` | 不适用（版面来自参考页，位置已固定） |
| 引用放页脚 12–14pt | `references/WRITING-RULES.md` | 待实现 |
| 生成按页串行 | `engine/fill.py` | 已实现（单进程按页填充） |
| 主题令牌是深色浅色成对 | `references/CONTEST-DESIGN-TOKENS.md` | 待实现 |
| 30% 编辑与重生成的分界线 | `SKILL.md` 第 1 节工作流 | 不适用（本 skill 一律重生成整份） |
| 九个子 agent 的职责拆分 | `SKILL.md` | 不适用（单 agent 流程） |
| 视觉语言库（29 套 spec、16 套实现） | `styles/` | 不适用（风格包来自真实参赛件） |
| 图片生成与溯源体系 | `engine/fill.py` 的照片槽 | 不适用（照片由使用者提供） |
| SVG 中间语言与 187 preset 形状编译 | `engine/fill.py` | 不适用（输入是现成 pptx） |
| 动画、转场、旁白、视频导出 | `SKILL.md` | 不适用（交付件是 pptx 与导出图） |

## 十、调研方法与本 skill 的差异

调研只用 `gh api` 读文件内容，没有克隆仓库，也没有安装任何上游工具。
每个仓库的 star 数与许可证取自 `gh api repos/<owner>/<repo>` 的 `stargazers_count` 与 `license.spdx_id`；没有 SPDX 标识的仓库（`anthropics/skills`）另外读了子目录里的 `LICENSE.txt` 正文确认权利状态。

本 skill 与这六个仓库在输出形态上有三处结构差异，这决定了大部分做法只能吸收判据、不能吸收实现：

1. 本 skill 的输入是现成的参赛 pptx，版面来自参考件，没有「从零设计版面」的环节。所以所有关于构图、视觉语言、版式选择的实现层做法都不适用，只有阈值类判据适用。
2. 本 skill 的输出是 pptx 与导出图，没有网页形态。所以 HTML 与 React 相关的做法全部不适用。
3. 本 skill 是单 agent 顺序流程，没有子 agent 与评审团。所以所有多角色编排的做法不适用。

在这三条约束下，本次调研真正新增的可执行判据集中在四类：交付模式与阅读量预算的分档、对比度的 WCAG 大字阈值与非文字元素阈值、版面几何的细化阈值（内边距、孤行标点、东亚字体、旋转外接框）、以及 OOXML 取值范围与子元素顺序清单。这四类已经进入第九节的吸收清单，标注为待实现。
