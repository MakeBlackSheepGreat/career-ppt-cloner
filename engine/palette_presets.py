# 赛事设计令牌：九套配色预设与字号下限。
# 供 gate_palette.py 取分类色查可混淆对，供 fill.py 取角色色值与字号下限。
# 色值出处逐条写在 references/CONTEST-DESIGN-TOKENS.md 的「令牌来源」一节。

# 参与色觉缺陷与灰度判定的分类色。正文、弱化文字、背景、分隔线属中性，不参与分类判定。
CATEGORICAL_ROLES = ("primary", "secondary", "accent")

# 令牌按 16:9 宽屏、赛场投影讲解取值，与七个风格包的 slide_cm 一致。
PAGE_CM = (33.87, 19.05)

# 页边距，单位厘米。取自 Gabberflast/academic-pptx-skill 的 MARGIN = 0.5 英寸
# （10 英寸宽画布，占 5%），换算到 33.87 厘米宽是 1.69 厘米，四边取同一个值。
# 这是排新页时的推荐值；判定用的下限仍是 rules.MIN_MARGIN_CM 的 0.25 厘米。
MARGIN_CM = {"left": 1.7, "right": 1.7, "top": 1.7, "bottom": 1.7}

# 路演类场合的字号下限，单位磅。七个风格包实测正文 14 到 20 磅、标题 24 到 28 磅、
# 章节大字 32 到 44 磅，令牌在下限一侧取值并留一档余量。投影幕布两米宽、观众八米外。
DECK_FLOOR_PT = {
    "display": 40.0,
    "headline": 28.0,
    "title": 22.0,
    "body": 16.0,
    "text": 14.0,
    "label": 14.0,
    "backdrop_note": 14.0,
    "glyph": 14.0,
    "chrome": 10.0,
}

# 答辩与学术汇报类的字号下限。这类页面信息密度高，正文实测可到 14 磅，令牌取实测下限，
# 仍高于 rules.ROLE_MIN_PT["reading"] 的同角色下限。
DEFENSE_FLOOR_PT = {
    "display": 36.0,
    "headline": 24.0,
    "title": 20.0,
    "body": 14.0,
    "text": 12.0,
    "label": 12.0,
    "backdrop_note": 12.0,
    "glyph": 12.0,
    "chrome": 10.0,
}

PRESETS = {
    "challenge-cup-red": {
        "name": "挑战杯红金",
        "venue": "挑战杯（大挑、小挑）与中国国际大学生创新大赛路演",
        "colors": {
            "primary": "#8E1220",
            "secondary": "#B06A1E",
            "accent": "#E3B34A",
            "body": "#1B1B1B",
            "muted": "#6E5A48",
            "background": "#FFFFFF",
            "surface": "#F7F2EA",
            "rule": "#E0D5C4",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DECK_FLOOR_PT),
        "source": "深红与金取自 styles/t-red-formal 实测主色 #E31503 与 #940219；"
                  "会徽征集要求「标准色及辅助色」，见 tiaozhanbei.net article/15734",
    },
    "innovation-blue": {
        "name": "国创赛科技蓝",
        "venue": "中国国际大学生创新大赛（国创赛）路演",
        "colors": {
            "primary": "#0B4F9E",
            "secondary": "#00A6C0",
            "accent": "#F2A900",
            "body": "#1A1A1A",
            "muted": "#55677D",
            "background": "#FFFFFF",
            "surface": "#EEF3FA",
            "rule": "#D8E0EC",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DECK_FLOOR_PT),
        "source": "主色取自 styles/t-blue-academic 实测 #0351D5 与 #0066FF；"
                  "青色取自 styles/t-teal-tech 实测 #007D8B；"
                  "中性层与 surface 沿用 M1n-n9/academic-ppt-master 的 academic-navy",
    },
    "career-growth-warm": {
        "name": "职规成长暖橙",
        "venue": "全国大学生职业规划大赛成长赛道",
        "colors": {
            "primary": "#B34A0A",
            "secondary": "#1B5570",
            "accent": "#F0A93C",
            "body": "#1E1A17",
            "muted": "#6B5B4E",
            "background": "#FFFFFF",
            "surface": "#FBF4EC",
            "rule": "#E8DCCB",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DECK_FLOOR_PT),
        "source": "暖橙取自 styles/t-warm-orange 实测 accent1 #F5794D；"
                  "青色辅助取自同包实测 accent2 #269DD8；"
                  "大赛徽标用「蓝绿玫瑰红」，见新京报 2024-04-19 教育部发布稿",
    },
    "career-employment-teal": {
        "name": "职规就业青蓝",
        "venue": "全国大学生职业规划大赛就业赛道",
        "colors": {
            "primary": "#0B6B70",
            "secondary": "#2F86C8",
            "accent": "#E39B32",
            "body": "#12201F",
            "muted": "#5C6B6A",
            "background": "#FFFFFF",
            "surface": "#EFF6F6",
            "rule": "#D5E3E3",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DECK_FLOOR_PT),
        "source": "青蓝取自 styles/t-teal-tech 实测 accent1 #007D8B 与 accent5 #5B9BD5；"
                  "暖金强调色取自同包 #F5D274；徽标「蓝绿」口径同上",
    },
    "academic-defense-navy": {
        "name": "答辩藏青",
        "venue": "学位论文答辩、开题与中期报告",
        "colors": {
            "primary": "#16365C",
            "secondary": "#B3261E",
            "accent": "#D4A72C",
            "body": "#16202C",
            "muted": "#55606E",
            "background": "#FFFFFF",
            "surface": "#EEF3FA",
            "rule": "#D8E0EC",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DEFENSE_FLOOR_PT),
        "source": "M1n-n9/academic-ppt-master templates/brands/academic-navy/design_spec.md："
                  "primary #16365C、accent #C0392B、panel-tint #EEF3FA、border #D8E0EC",
    },
    "academic-blue-clean": {
        "name": "学术蓝白",
        "venue": "文献汇报、组会与学术讲座",
        "colors": {
            "primary": "#1F4E79",
            "secondary": "#2E75B6",
            "accent": "#C9A227",
            "body": "#2D2D2D",
            "muted": "#5A5A5A",
            "background": "#FFFFFF",
            "surface": "#F2F6FA",
            "rule": "#CCCCCC",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DEFENSE_FLOOR_PT),
        "source": "Gabberflast/academic-pptx-skill slide_patterns.md 的 COLORS："
                  "primary #1F4E79、accent #2E75B6、body #2D2D2D、muted #777777、rule #CCCCCC",
    },
    "academic-graphite": {
        "name": "学术石墨",
        "venue": "文献汇报与研究报告的无彩色版",
        "colors": {
            "primary": "#2B3138",
            "secondary": "#B3442C",
            "accent": "#D4A72C",
            "body": "#1C2024",
            "muted": "#5E646C",
            "background": "#FFFFFF",
            "surface": "#F4F5F6",
            "rule": "#E3E5E8",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DEFENSE_FLOOR_PT),
        "source": "M1n-n9/academic-ppt-master templates/brands/academic-graphite/design_spec.md："
                  "primary #2B3138、body #1C2024、muted #5E646C、border #E3E5E8、alert #B3261E",
    },
    "tech-deck-deep": {
        "name": "深景科技",
        "venue": "硬件项目、竞赛成果与技术路演",
        "colors": {
            "primary": "#0B8CE6",
            "secondary": "#F98E45",
            "accent": "#3FD3E3",
            "body": "#E8EEF7",
            "muted": "#9AAAC0",
            "background": "#0B1220",
            "surface": "#16223A",
            "rule": "#2A3A52",
            "on_primary": "#04121F",
        },
        "font_floor_pt": dict(DECK_FLOOR_PT),
        "source": "深底与亮蓝取自 styles/t-tech-deck 实测 #0B8CE6 与 #0B9AF5；"
                  "橙取自同包 #F98E45；暗色中性层沿用 adithya-s-k/research-presentation-template "
                  "src/themes/index.ts 的 carbon dark（bg #0B0F12、bgRaised #141A1F、border #26313A）",
    },
    "eco-enterprise-green": {
        "name": "实业墨绿",
        "venue": "新能源、制造与工程实施类项目",
        "colors": {
            "primary": "#0F5B3E",
            "secondary": "#4E9A3F",
            "accent": "#D9B37A",
            "body": "#14231B",
            "muted": "#5E6E62",
            "background": "#FBFDF9",
            "surface": "#EEF4EA",
            "rule": "#D8E3D2",
            "on_primary": "#FFFFFF",
        },
        "font_floor_pt": dict(DECK_FLOOR_PT),
        "source": "墨绿取自 styles/t-green-eco 实测 accent1 #017C46 与 #52A23A；"
                  "米金强调色取自 styles/t-red-formal 的金色分隔线 #F2BA02 调低饱和",
    },
}


def names():
    return sorted(PRESETS)


def get(name):
    if name not in PRESETS:
        raise SystemExit("未知令牌：%s（可选 %s）" % (name, "、".join(names())))
    return PRESETS[name]


def colors_of(name):
    return dict(get(name)["colors"])


def floor_pt(name, role):
    floors = get(name)["font_floor_pt"]
    if role not in floors:
        raise SystemExit("未知角色：%s（可选 %s）" % (role, "、".join(sorted(floors))))
    return floors[role]


def categorical(name):
    preset = get(name)
    return [preset["colors"][role] for role in CATEGORICAL_ROLES]


def confusable(name):
    """返回分类色在色觉缺陷模拟与灰度口径下的可混淆对。"""
    import gate_palette
    findings = gate_palette.check_palette(categorical(name))
    return [item for item in findings if item["level"] == "FAIL"]


def _selfcheck():
    import gate_palette
    import rules

    failed = 0
    print("令牌 %d 套，分类色角色：%s" % (len(PRESETS), "、".join(CATEGORICAL_ROLES)))
    print("判据：Machado 2009 三型模拟后 CIE76 色差 < %.1f 判可混淆；"
          "Rec.709 亮度差 < %.2f 判灰度可混淆"
          % (gate_palette.CONFUSABLE_DELTA_E, gate_palette.GRAYSCALE_MIN_DELTA))
    print()
    for name in names():
        preset = PRESETS[name]
        colors = preset["colors"]
        pairs = confusable(name)
        body_contrast = rules.contrast_ratio(colors["body"], colors["background"])
        muted_contrast = rules.contrast_ratio(colors["muted"], colors["background"])
        muted_surface = rules.contrast_ratio(colors["muted"], colors["surface"])
        reverse = rules.contrast_ratio(colors["on_primary"], colors["primary"])
        print("%-24s %-22s 色数=%d 可混淆对=%d" % (name, preset["name"], len(colors), len(pairs)))
        print("    正文/背景=%.2f 弱化/背景=%.2f 弱化/面板=%.2f 反白/主色=%.2f"
              % (body_contrast, muted_contrast, muted_surface, reverse))
        for pair in pairs:
            print("    FAIL %s  %s" % (pair["rule"], pair["detail"]))
        failed += len(pairs)
    print()
    print("palette_presets: 可混淆对合计=%d" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selfcheck())
