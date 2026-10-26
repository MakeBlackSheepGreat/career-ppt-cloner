# 赛事设计令牌

把挑战杯、中国国际大学生创新大赛、全国大学生职业规划大赛、学术答辩四类场合的配色与版式规律写成可复用的常量。令牌落在 `engine/palette_presets.py`，配色门 `engine/gate_palette.py` 与填充脚本 `engine/fill.py` 都从这里取角色色值与字号下限。

## 一、令牌怎么来的

### 1.1 三类来源

| 来源类型 | 具体位置 | 取到什么 |
| --- | --- | --- |
| 已抽好的风格包 | `styles/t-warm-orange`、`t-teal-tech`、`t-slate-serious`、`t-red-formal`、`t-green-eco`、`t-blue-academic`、`t-tech-deck` 的 `pack.pptx` | 实测填充色与字体色，逐个统计出现次数，取高频色作为赛事主色的实际依据 |
| MIT 许可的学术仓库 | Gabberflast/academic-pptx-skill 的 `slide_patterns.md`；M1n-n9/academic-ppt-master 的 `templates/brands/*/design_spec.md`；adithya-s-k/research-presentation-template 的 `src/themes/index.ts` | 完整的学术配色角色表、字号层级、页边距，以及深色与浅色成对的主题令牌 |
| 赛事官方口径与公开报道 | 挑战杯官网会徽征集启事、教育部职业规划大赛徽标发布稿、新华网吉祥物发布稿 | 赛事标识的标准色要求与主色倾向 |

### 1.2 三个 MIT 仓库的可用常量

**Gabberflast/academic-pptx-skill**（MIT，1360 star，`slide_patterns.md`）

```javascript
const COLORS = {
  bg:       "FFFFFF",   // 白底
  primary:  "1F4E79",   // 深藏青，标题
  accent:   "2E75B6",   // 中蓝，页眉与强调
  body:     "2D2D2D",   // 近黑，正文
  muted:    "777777",   // 灰，引注与图注
  rule:     "CCCCCC",   // 浅灰，分隔线
  highlight:"FFF2CC",   // 浅黄，提示框，慎用
};
const FONTS = {
  face: "Arial",
  title: 26,          // 动作标题 24 到 28 磅
  sectionHeader: 22,
  body: 20,           // 正文下限 20 磅
  label: 16,
  cite: 13,
};
const MARGIN = 0.5;   // 距页面边缘最小留白，单位英寸
```

交付前自检里还有两条硬指标：正文全程不低于 20 磅；单页正文文字不超过约 40 个单词。

**M1n-n9/academic-ppt-master**（MIT，277 star，`templates/brands/`）

三套品牌令牌各有完整的角色表，这里只列与令牌库直接相关的字段。

| 品牌 | primary | 强调色 | 背景 | 面板 | 分隔线 | 正文 | 弱化文字 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| academic-blue | `#14365C` | 只用 primary 一色 | `#FFFFFF` | `#F4F6F9` | `#E2E7EE` | `#1C2430` | `#5B6573` |
| academic-graphite | `#2B3138` | 只用 primary 一色 | `#FFFFFF` | `#F4F5F6` | `#E3E5E8` | `#1C2024` | `#5E646C` |
| academic-navy | `#16365C` | `#C0392B`（砖红，占全篇不超过 10%） | `#FFFFFF` | `#EEF3FA` | `#D8E0EC` | `#1C2430` | `#5B6573` |

academic-navy 另有固定的一组示意图节点色（蓝 `#DCE6F5`、绿 `#DCEBDC`、紫 `#E4DEF0`、黄 `#FBF1CE`、粉 `#F8DEE2`、中性 `#EEF1F5`），只用于流程图与架构图节点，不用于正文与面板。

三套品牌的字号口径一致：投影可读的无衬线字体，1280×720 画布上正文不小于 16 像素；academic-navy 的信息密度档另写正文不小于 15 像素、面板标签 16 到 18 像素加粗、章节标题 26 到 30 像素。

**adithya-s-k/research-presentation-template**（MIT，8 star，`src/themes/index.ts`）

三套主题，每套含深色与浅色两版，共 14 个色角色。这里取与深色投影页相关的三套深色版。

| 主题 | 背景 | 抬升面板 | 分隔线 | 强调色一 | 强调色二 | 正文 | 弱化文字 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| forge dark | `#07090F` | `#0E1422` | `#283149` | `#B06BFF` | `#10F0A4` | `#F8FAFD` | `#D0D8E6` |
| paper dark | `#12141A` | `#1B1E26` | `#333844` | `#7EA2FF` | `#FF8F6B` | `#F8FAFD` | `#D0D8E6` |
| carbon dark | `#0B0F12` | `#141A1F` | `#26313A` | `#38BDF8` | `#FBBF24` | `#F8FAFD` | `#D0D8E6` |

carbon 浅色版的强调色是 `#0369A1` 与 `#B45309`，正文 `#161D2B`，弱化文字 `#3D4657`。画布固定 1280×720，所有页面按同一比例缩放到任意投影仪。

该仓库的设计说明里有一条与本令牌库同向的纪律：三个令牌承担识别，背景、结构强调、正文内强调各一个，其余全部是灰阶。

### 1.3 赛事标识的公开口径

- 挑战杯官网的会徽征集启事要求应征作品提交「图形标志、名称的标准字体、标准色及辅助色、标识和标准字的组合规范以及标志在背景色上的使用规范」。赛事有独立的标准色体系，配色不能只用一种红。
- 教育部 2024 年 4 月 18 日发布全国大学生职业规划大赛徽标，公开报道写明「整体颜色采用极富年轻活力的蓝绿玫瑰红」。这是蓝、绿、玫红三色并置的官方口径。
- 新华网 2024 年 5 月 10 日的吉祥物发布稿写明「小业」的配色来自上海市花白玉兰，耳侧叶片「色彩取自本次大赛标志的渐变色」。

挑战杯与中国国际大学生创新大赛的标识色值没有公开的十六进制文档，令牌里的红金与科技蓝由已抽风格包的实测高频色归纳，并在每套令牌的 `source` 字段注明依据。

## 二、九套令牌

配色角色统一为九项：`primary`、`secondary`、`accent`、`body`、`muted`、`background`、`surface`、`rule`、`on_primary`。前三项参与色觉缺陷与灰度判定，后六项属中性层。

### 2.1 挑战杯红金 `challenge-cup-red`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#8E1220` | 页眉带、章节大字底、关键数字 |
| 辅助色 secondary | `#B06A1E` | 次级色块、进度条 |
| 强调色 accent | `#E3B34A` | 分隔线、奖项标识、单处强调 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#F7F2EA` | 卡片与关键信息条 |
| 正文 body | `#1B1B1B` | 正文与标题 |
| 弱化文字 muted | `#6E5A48` | 图注、出处、页码 |
| 分隔线 rule | `#E0D5C4` | 细线与表格网格 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限按路演档：章节大字 40 磅，页标题 28 磅，小标题 22 磅，正文 16 磅，注释 14 磅。页边距四边各 1.7 厘米。

来源：深红与金取自 `styles/t-red-formal` 实测填充色 `#E31503`、`#DF181D`、`#940219` 与金色分隔线 `#F2BA02`；标准色与辅助色的要求见挑战杯官网会徽征集启事。

### 2.2 国创赛科技蓝 `innovation-blue`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#0B4F9E` | 页眉、结构块、关键数字 |
| 辅助色 secondary | `#00A6C0` | 数据图与流程节点 |
| 强调色 accent | `#F2A900` | 结论条与唯一强调点 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#EEF3FA` | 卡片与表格斑马行 |
| 正文 body | `#1A1A1A` | 正文与标题 |
| 弱化文字 muted | `#55677D` | 图注、出处 |
| 分隔线 rule | `#D8E0EC` | 细线 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限同路演档，页边距四边各 1.7 厘米。

来源：主色取自 `styles/t-blue-academic` 实测 `#0351D5` 与 `#0066FF`；青色取自 `styles/t-teal-tech` 实测 `#007D8B`；面板与分隔线沿用 M1n-n9/academic-ppt-master 的 academic-navy 令牌。

### 2.3 职规成长暖橙 `career-growth-warm`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#B34A0A` | 页眉标题条、章节大字 |
| 辅助色 secondary | `#1B5570` | 对照色块、时间轴 |
| 强调色 accent | `#F0A93C` | 进度条与金句底 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#FBF4EC` | 卡片 |
| 正文 body | `#1E1A17` | 正文与标题 |
| 弱化文字 muted | `#6B5B4E` | 图注与出处 |
| 分隔线 rule | `#E8DCCB` | 细线 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限同路演档。这一套的主色在白色背景上对比度 5.38，达到 WCAG 正文下限 4.5，未达舒适值 7.0，主色只用于 22 磅以上的标题与色块，正文一律用 `#1E1A17`。

来源：暖橙取自 `styles/t-warm-orange` 实测 accent1 `#F5794D`；青色辅助取自同包实测 accent2 `#269DD8`；三色并置的口径见教育部徽标发布稿。

### 2.4 职规就业青蓝 `career-employment-teal`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#0B6B70` | 页眉、胶囊条、关键数字 |
| 辅助色 secondary | `#2F86C8` | 数据图与卡片边 |
| 强调色 accent | `#E39B32` | 唯一强调点 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#EFF6F6` | 卡片 |
| 正文 body | `#12201F` | 正文与标题 |
| 弱化文字 muted | `#5C6B6A` | 图注与出处 |
| 分隔线 rule | `#D5E3E3` | 细线 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限同路演档。主色在白色背景上对比度 6.27，达到下限未达舒适值，主色用于 22 磅以上的标题与色块。

来源：青蓝取自 `styles/t-teal-tech` 实测 accent1 `#007D8B` 与 accent5 `#5B9BD5`；暖金取自同包实测 `#F5D274` 并压暗到可承载白字。

### 2.5 答辩藏青 `academic-defense-navy`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#16365C` | 页眉页脚框架、章节标题、表格表头 |
| 辅助色 secondary | `#B3261E` | 全篇唯一的关键事实或风险提示，占比不超过 10% |
| 强调色 accent | `#D4A72C` | 结论条与关键数字 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#EEF3FA` | 分组面板与关键信息条 |
| 正文 body | `#16202C` | 正文与标题 |
| 弱化文字 muted | `#55606E` | 图注、坐标轴标签 |
| 分隔线 rule | `#D8E0EC` | 细线与表格网格 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限按答辩档：章节大字 36 磅，页标题 24 磅，小标题 20 磅，正文 14 磅，注释 12 磅。信息密度比路演页高，正文字号按七个风格包实测下限取值。

来源：M1n-n9/academic-ppt-master 的 `templates/brands/academic-navy/design_spec.md`，primary `#16365C`、accent `#C0392B` 压暗到 `#B3261E`、panel-tint `#EEF3FA`、border `#D8E0EC`。

### 2.6 学术蓝白 `academic-blue-clean`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#1F4E79` | 标题与页眉 |
| 辅助色 secondary | `#2E75B6` | 页眉与图表强调 |
| 强调色 accent | `#C9A227` | 结论框与关键数字 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#F2F6FA` | 卡片 |
| 正文 body | `#2D2D2D` | 正文 |
| 弱化文字 muted | `#5A5A5A` | 引注与图注 |
| 分隔线 rule | `#CCCCCC` | 细线 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限按答辩档。这一套与原仓库的差别是把 `muted` 从 `#777777` 压暗到 `#5A5A5A`，原值在白底上对比度只有 4.48，低于 WCAG 正文下限。

来源：Gabberflast/academic-pptx-skill 的 `slide_patterns.md` 的 `COLORS` 常量，primary `#1F4E79`、accent `#2E75B6`、body `#2D2D2D`、rule `#CCCCCC`；`muted` 与 `accent` 有调整。

### 2.7 学术石墨 `academic-graphite`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#2B3138` | 标题、页签、关键节点 |
| 辅助色 secondary | `#B3442C` | 唯一警示点 |
| 强调色 accent | `#D4A72C` | 结论条 |
| 背景 background | `#FFFFFF` | 正文页底 |
| 面板 surface | `#F4F5F6` | 卡片 |
| 正文 body | `#1C2024` | 正文 |
| 弱化文字 muted | `#5E646C` | 图注与出处 |
| 分隔线 rule | `#E3E5E8` | 细线 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限按答辩档。原品牌的强调靠明度差实现，令牌补了两项低饱和彩色，让关键事实在灰度打印里也能分出来。

来源：M1n-n9/academic-ppt-master 的 `templates/brands/academic-graphite/design_spec.md`，primary `#2B3138`、body `#1C2024`、muted `#5E646C`、border `#E3E5E8`、alert `#B3261E`；secondary 与 accent 在原 alert 基础上调整。

### 2.8 深景科技 `tech-deck-deep`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#0B8CE6` | 亮蓝描边、卡片边、关键数字 |
| 辅助色 secondary | `#F98E45` | 次级数据与对比项 |
| 强调色 accent | `#3FD3E3` | 图表高亮与描边 |
| 背景 background | `#0B1220` | 深色页底 |
| 面板 surface | `#16223A` | 卡片与分区 |
| 正文 body | `#E8EEF7` | 正文与标题 |
| 弱化文字 muted | `#9AAAC0` | 图注与出处 |
| 分隔线 rule | `#2A3A52` | 细线 |
| 反白 on_primary | `#04121F` | 主色块上的文字 |

字号下限按路演档。这是九套里唯一的深色底令牌，`on_primary` 用近黑而不用白色，因为白色压在 `#0B8CE6` 上对比度只有 3.55，低于正文下限。

来源：深底与亮蓝取自 `styles/t-tech-deck` 实测 `#0B8CE6` 与 `#0B9AF5`；橙取自同包 `#F98E45`；面板、分隔线与弱化文字沿用 adithya-s-k/research-presentation-template 的 carbon dark 令牌。

### 2.9 实业墨绿 `eco-enterprise-green`

| 角色 | 色值 | 用法 |
| --- | --- | --- |
| 主色 primary | `#0F5B3E` | 页眉、色块分区、关键数字 |
| 辅助色 secondary | `#4E9A3F` | 次级色块与图表 |
| 强调色 accent | `#D9B37A` | 分隔线与唯一强调点 |
| 背景 background | `#FBFDF9` | 正文页底 |
| 面板 surface | `#EEF4EA` | 卡片 |
| 正文 body | `#14231B` | 正文与标题 |
| 弱化文字 muted | `#5E6E62` | 图注与出处 |
| 分隔线 rule | `#D8E3D2` | 细线 |
| 反白 on_primary | `#FFFFFF` | 主色块上的文字 |

字号下限同路演档。弱化文字压在面板色上对比度 4.83，刚过正文下限，弱化文字只用于 14 磅以上的注释。

来源：墨绿取自 `styles/t-green-eco` 实测 accent1 `#017C46` 与 `#52A23A`；米金强调色由 `styles/t-red-formal` 的金色 `#F2BA02` 降低饱和得到。

## 三、色觉缺陷与灰度可读性自检

### 3.1 判据

三条判据与 `engine/gate_palette.py` 同一套口径：

| 判据 | 阈值 | 判定方式 |
| --- | --- | --- |
| 色觉缺陷可混淆 | deltaE < 12 | Machado 2009 线性 RGB 矩阵模拟 protanopia、deuteranopia、tritanopia，转 CIELAB 后算 CIE76 色差 |
| 灰度可混淆 | 亮度差 < 0.03 | Rec.709 亮度 0.2126R + 0.7152G + 0.0722B |
| 正文对比度 | 4.5 / 7.0 | WCAG 相对亮度比，低于 4.5 判失败，低于 7.0 判告警 |

### 3.2 结论

九套令牌的分类色（主色、辅助色、强调色）两两之间，在三型色觉缺陷模拟与灰度口径下都没有可混淆对。九套的可混淆对合计为 0。

| 令牌 | 分类色数 | 可混淆对 | 正文/背景 | 弱化/背景 | 弱化/面板 | 反白/主色 |
| --- | --- | --- | --- | --- | --- | --- |
| 学术蓝白 | 3 | 0 | 13.77 | 6.90 | 6.35 | 8.66 |
| 答辩藏青 | 3 | 0 | 16.44 | 6.39 | 5.73 | 12.24 |
| 学术石墨 | 3 | 0 | 16.39 | 5.97 | 5.47 | 13.13 |
| 职规就业青蓝 | 3 | 0 | 16.77 | 5.58 | 5.09 | 6.27 |
| 职规成长暖橙 | 3 | 0 | 17.28 | 6.50 | 5.96 | 5.38 |
| 挑战杯红金 | 3 | 0 | 17.22 | 6.52 | 5.85 | 9.30 |
| 实业墨绿 | 3 | 0 | 15.96 | 5.28 | 4.83 | 8.12 |
| 国创赛科技蓝 | 3 | 0 | 17.40 | 5.80 | 5.20 | 8.00 |
| 深景科技 | 3 | 0 | 16.05 | 7.92 | 6.71 | 5.32 |

正文字号一律用 `body` 色，九套的正文对背景对比度都在 13.77 以上，远高于 7.0 的舒适值。弱化文字对背景在 5.28 到 7.92 之间，全部达到 4.5 的正文下限，其中八套未达 7.0 的舒适值，弱化文字只承载图注与出处这类非关键信息。

反白对主色一项，三套低于 7.0：职规成长暖橙 5.38、职规就业青蓝 6.27、深景科技 5.32。前两套仍高于 4.5 的正文下限，主色块上的文字按 22 磅以上使用；深景科技的 `on_primary` 已改成近黑 `#04121F`，取值 5.32，白字方案只有 3.55，不采用。

### 3.3 调整过程留痕

初版九套里有四套报出可混淆对，调整依据如下。

| 初版问题 | 实测值 | 处理 |
| --- | --- | --- |
| 职规成长暖橙的主色与辅助色灰度差过小 | 0.0161 | 辅助色由 `#175E78` 压暗到 `#1B5570`，灰度差升到 0.0670 |
| 职规就业青蓝的主色、辅助色、强调色三对都可混淆 | tritanopia 11.28、灰度 0.0017 与 0.0293 | 主色由 `#00696E` 调到 `#0B6B70`，辅助色由 `#2A7FC1` 调到 `#2F86C8`，三色灰度差升到 0.1307 |
| 答辩藏青的主色与正文灰度差过小 | 0.0220 | 正文由 `#16202C` 保留，辅助色由 `#9E2B1F` 改到 `#B3261E`，灰度差升到 0.0685 |
| 学术石墨的主色与正文在三型模拟下都可混淆 | 8.36、8.21、8.19 | 原品牌强调靠明度差，令牌补入 `#B3442C` 与 `#D4A72C` 两项彩色，最差色差升到 33.51 |
| 深景科技的辅助色与强调色灰度差过小 | 0.0221 | 强调色由 `#00C2D1` 提到 `#3FD3E3`，灰度差升到 0.0832 |
| 学术蓝白的弱化文字对比度不足 | `#777777` 在白底上 4.48 | 压暗到 `#5A5A5A`，对比度 6.90 |

## 四、赛事与令牌的对照

| 赛事或场合 | 令牌名 | 适用场景 | 与现有七个风格包的对应 |
| --- | --- | --- | --- |
| 挑战杯（大挑、小挑） | `challenge-cup-red` | 创业计划竞赛路演，正式汇报感强，金融与管理方向 | `t-red-formal` 最接近，红金对称构图与金色分隔线同源；配色可直接替换 `t-red-formal` 的填充色 |
| 中国国际大学生创新大赛 | `innovation-blue` | 科技类项目路演，需要强调技术先进性 | `t-blue-academic` 与 `t-teal-tech` 都可用；科技蓝令牌按 `t-blue-academic` 的蓝白插画底取色 |
| 职业规划大赛成长赛道 | `career-growth-warm` | 从兴趣起点讲到成长，温情叙事 | `t-warm-orange` 直接对应，橙色与深色标题条同源 |
| 职业规划大赛就业赛道 | `career-employment-teal` | 理工科技术岗求职，青蓝胶囊条 | `t-teal-tech` 直接对应 |
| 职业规划大赛就业赛道（研究生） | `academic-defense-navy` | 科研项目密集，顶部四段导航 | `t-slate-serious` 可用；藏青令牌沿用其深色星空底与顶部导航的明度关系 |
| 学位论文答辩、开题与中期报告 | `academic-defense-navy`、`academic-blue-clean` | 信息密度高，需要评委逐条对照 | 七个风格包没有纯答辩版式，按现有风格包改色后使用 |
| 文献汇报与组会 | `academic-blue-clean`、`academic-graphite` | 学术报告，白底为主 | `t-blue-academic` 可改色使用 |
| 硬件项目与竞赛成果 | `tech-deck-deep` | 深色科技底，亮蓝描边卡片 | `t-tech-deck` 直接对应 |
| 新能源、制造与工程实施类项目 | `eco-enterprise-green` | 稳重克制，几何色块分区 | `t-green-eco` 直接对应 |

## 五、字号与页边距

### 5.1 两档字号下限

| 角色 | 路演档 DECK_FLOOR_PT | 答辩档 DEFENSE_FLOOR_PT | `rules.ROLE_MIN_PT["presentation"]` |
| --- | --- | --- | --- |
| display | 40 | 36 | 36 |
| headline | 28 | 24 | 24 |
| title | 22 | 20 | 18 |
| body | 16 | 14 | 16 |
| text | 14 | 12 | 14 |
| label | 14 | 12 | 12 |
| backdrop_note | 14 | 12 | 12 |
| glyph | 14 | 12 | 12 |
| chrome | 10 | 10 | 10 |

路演档按投影幕布两米宽、观众八米外取可读性，章节大字提到 40 磅，页标题提到 28 磅。答辩档按信息密度高的学术页面取值，正文放到 14 磅，与七个风格包实测的正文下限一致。

七个风格包的实测字号分布如下，令牌取值落在每一档的低端，给自动折行留出余量。

| 风格包 | 正文实测 | 标题实测 | 章节大字实测 |
| --- | --- | --- | --- |
| `t-warm-orange` | 16 到 20 磅 | 22 到 28 磅 | 32 到 44 磅 |
| `t-teal-tech` | 14 到 20 磅 | 24 到 28 磅 | 32 到 44 磅 |
| `t-slate-serious` | 12 到 20 磅 | 22 到 28 磅 | 32 到 44 磅 |
| `t-red-formal` | 14 到 16 磅 | 24 到 28 磅 | 32 到 40 磅 |
| `t-green-eco` | 14 到 20 磅 | 24 到 28 磅 | 32 到 44 磅 |
| `t-blue-academic` | 14 到 20 磅 | 24 到 28 磅 | 32 到 44 磅 |
| `t-tech-deck` | 14 到 18 磅 | 24 到 28 磅 | 32 到 44 磅 |

### 5.2 页边距

`MARGIN_CM` 四边各 1.7 厘米。这个值来自 Gabberflast/academic-pptx-skill 的 `MARGIN = 0.5` 英寸，画布宽 10 英寸，占 5%，换算到 33.87 厘米宽是 1.69 厘米。

判定用的下限仍是 `rules.MIN_MARGIN_CM` 的 0.25 厘米。七个风格包实测的文字框距页面边缘最小值在 0 到 0.46 厘米之间，装饰形状还有出血到页面外的，说明往届作品的留白并不统一。1.7 厘米是排新页时的推荐值。

## 六、怎么用

```python
import palette_presets

preset = palette_presets.get("challenge-cup-red")
preset["colors"]["primary"]          # '#8E1220'
palette_presets.floor_pt("challenge-cup-red", "body")   # 16.0
palette_presets.categorical("challenge-cup-red")        # 三个分类色的列表
palette_presets.confusable("challenge-cup-red")         # 可混淆对，空列表表示通过
```

命令行自检：

```bash
python engine/palette_presets.py
```

自检打印每套令牌的色数、可混淆对数与四组对比度，末行为可混淆对合计，合计不为 0 时退出码 1。

单独查一套分类色：

```bash
python engine/gate_palette.py --colors "#8E1220,#B06A1E,#E3B34A"
```

## 七、调研过程与取舍

### 7.1 检索过的仓库

用 `gh api "search/repositories?q=<关键词>&sort=stars&per_page=8"` 检索下列关键词，按 star 排序取前八条。

| 关键词 | 命中条数 | 采用的仓库 |
| --- | --- | --- |
| 挑战杯 PPT | 3 | `helloo1568/slidemuse`（MIT，146 star）只读做法，用于确认赛事作品集的组织方式 |
| 互联网+ 大学生创新创业 PPT | 0 | 无 |
| 国创赛 PPT | 2 | `KarlHeinrich-jpg/Business-Plan-and-PPT`（无许可证）、`PlantaryWindsystem/red-journey-public-welfare-coach`（无许可证），都不内化 |
| 大学生竞赛 路演 PPT | 1 | `TZUKWAN/ares`（MIT，1 star），只读赛事清单的组织方式 |
| 学术答辩 PPT 模板 | 2 | `jasonbian97/Academic-Report-Beamer-Template`（无许可证）、`Nofearli/lsh-academic-ppt`（无许可证），都不内化 |

任务里列出的三个 MIT 仓库全部读取到具体文件：`Gabberflast/academic-pptx-skill` 的 `slide_patterns.md` 与 `content_guidelines.md`、`adithya-s-k/research-presentation-template` 的 `src/themes/index.ts`、`M1n-n9/academic-ppt-master` 的三份 `design_spec.md` 与 `brands_index.json`。

### 7.2 没有吸收的部分

- `helloo1568/slidemuse` 的做法是先生成整页图片再拼 pptx，与本地母版填充的路线不同。它的「四套缩略图总览选型」与「风格库以可见页面为事实源」两条纪律与本 skill 一致，但不需要引入。
- `adithya-s-k/research-presentation-template` 的 `glow` 发光样式依赖浏览器 CSS，导出成 pptx 后无法保留，只取色值与画布尺寸。
- M1n-n9/academic-ppt-master 的示意图节点色板没有并入令牌，因为它只服务流程图节点，与页面主配色是两件事。
- 没有许可证的仓库（`KarlHeinrich-jpg/Business-Plan-and-PPT`、`PlantaryWindsystem/red-journey-public-welfare-coach`、`jasonbian97/Academic-Report-Beamer-Template`、`Nofearli/lsh-academic-ppt`）只记录检索到，不引用任何色值或结构。

### 7.3 局限

- 挑战杯与中国国际大学生创新大赛没有公开的十六进制标准色文档，令牌里的红金与科技蓝由七个风格包的实测高频色归纳，赛事组委会换标识后需要复核。
- 七个风格包来自职业规划大赛的往届作品，挑战杯与国创赛的版式规律没有对应的实测样本，对照表里的版式建议按通用路演结构给出。
- 令牌只覆盖配色、字号与页边距，不涉及字体选择。七个风格包的字体沿用母版，没有单独抽取。
