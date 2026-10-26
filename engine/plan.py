"""赛事叙事骨架：先按评审逻辑排好每页讲什么，再落到具体风格包的版面上。

参考件只提供版面，不提供叙事。往届选手的版面是为他自己的故事排的，直接往里塞内容
会出现「章节页塞正文」「一页讲两件事」这类问题。这里把三个主要赛事的内容骨架固化
下来，先规划大纲，再按版面类型匹配页码。

用法：
    python engine/plan.py --style styles/t-warm-orange --event 职业规划成长 --out 大纲.json
    python engine/plan.py --list
"""
import argparse
import json
import os

# 一页能装多少段内容，按版面类型定上限。
# 参考页的槽位总数往往远大于这个数（姓名、专业、绩点、导航标签各占一个框），
# 那些是给人填空用的细粒度槽位，不适合按顺序一口气填完。大纲只取前几段。
SLOT_CAPACITY = {
    "cover": 4,      # 主标题、副标题、一句话主张、赛道标签
    "section": 2,    # 章节名、可选一句导语（大序号是装饰，不填）
    "text": 4,       # 页标题、正文段、压轴句、补充句
    "grid": 6,       # 页标题、若干并列短标签
    "photo": 2,      # 页标题、短说明
}


# 某种版面用完之后，退而求其次的替代顺序。
# 封面退到章节页再退到内容页；章节页只用章节页或封面，绝不退到内容页——那样会把
# 「三、职业匹配」这种标题塞进正文页，读者会以为漏了一页。
FALLBACK = {
    "cover": ("section", "text"),
    "section": ("cover",),
    "text": ("grid", "photo"),
    "grid": ("text", "photo"),
    "photo": ("text", "grid"),
}


def load_style(style_dir):
    with open(os.path.join(style_dir, "slots.json"), encoding="utf-8") as handle:
        return json.load(handle)


def index_pages(manifest):
    by_kind = {}
    for page in manifest["pages"]:
        by_kind.setdefault(page["kind"], []).append(page)
    return by_kind


SPECIFICITY_RANK = {"generic": 0, "mixed": 1, "specific": 2}


def pick(kind_index, kind, used):
    """按类型取一页没用过的，优先挑版面通用、不专属的页。"""
    candidates = [page for page in kind_index.get(kind, []) if page["page"] not in used]
    if not candidates:
        return None
    candidates.sort(key=lambda page: (SPECIFICITY_RANK.get(page.get("specificity"), 1),
                                      page["page"]))
    return candidates[0]


def usable_slots(page):
    """可填槽位：排除装饰字，也排除页眉带里的版式签名。

    fill_order 就是「简写时按什么顺序填」的权威列表，它已经排除了装饰字，
    并且把页眉带排在最后。以它为准，避免大纲报出的槽位数与 fill.py 实际接受的不一致。
    """
    order = page.get("fill_order")
    by_number = {slot["slot"]: slot for slot in page["slots"]}
    if not order:
        return [slot for slot in page["slots"] if slot["role"] != "glyph"]
    picked = []
    for number in order:
        slot = by_number.get(number)
        if slot is None:
            continue
        # 参考件里原本没有文字的形状（纯色块、装饰图形）不填内容
        if not slot.get("expect_text", True):
            continue
        picked.append(slot)

    # 同一页里的槽位分量不一样：正文区和标题条能装整句话，角落的短标签只能塞四五个字。
    # 按「醒目程度」排序后，大纲优先把内容分给大字号的框，避免正文被塞进小圆圈。
    def prominence(slot):
        area = (slot.get("width") or 0) * (slot.get("height") or 0)
        return (slot.get("font_size") or 0) * 2.0 + area

    picked.sort(key=prominence, reverse=True)
    return picked


# ---------------------------------------------------------------- 赛事骨架

EVENTS = {
    "职业规划成长": {
        "name": "全国大学生职业规划大赛 · 成长赛道",
        "basis": "教育部通知附件1《成长赛道方案》：考察生涯发展理念、职业目标设置、"
                 "围绕目标的持续行动与调整、综合素质与专业能力提升",
        "outline": [
            ("cover", "封面", "职业目标一句话、姓名、赛道"),
            ("section", "一、自我认知", "性格与兴趣测评结论、能力现状"),
            ("text", "兴趣的起点", "一件具体的小事，说明兴趣从哪来"),
            ("text", "做过哪些尝试", "列出试过的方向，哪些留下了、哪些放弃了"),
            ("text", "测评结果怎么看", "霍兰德或 MBTI 结论如何对应到具体岗位"),
            ("section", "二、职业定位", "目标职业、行业、岗位"),
            ("text", "为什么是这个岗位", "岗位每天都在做什么，自己哪一点被它吸引"),
            ("grid", "岗位能力要求", "拆成 3 到 5 条并列的能力项"),
            ("text", "行业与政策依据", "行业规模、政策文件、招聘需求"),
            ("section", "三、职业匹配", "能力与岗位的对应关系"),
            ("text", "能力对照", "逐条说明自己的经历怎么对上岗位要求"),
            ("photo", "实践与成果", "竞赛、项目、实习的照片与证书"),
            ("grid", "已具备的能力", "并列列出可验证的能力证据"),
            ("section", "四、未来规划", "短期、中期、长期的行动"),
            ("text", "接下来一年", "具体到课程、项目、实习"),
            ("text", "三到五年", "岗位晋升路径与要补的短板"),
            ("text", "兜底方案", "如果目标没实现，备选路径是什么"),
            ("text", "结语", "一句话收束"),
        ],
    },
    "职业规划就业": {
        "name": "全国大学生职业规划大赛 · 就业赛道",
        "basis": "教育部通知附件2《就业赛道方案》：考察求职实战能力、综合素质与专业能力"
                 "同目标职业的契合度、个人发展路径与就业市场需求的适应度",
        "outline": [
            ("cover", "封面", "求职意向岗位、姓名、赛道"),
            ("section", "一、个人情况与求职意向", "基本信息、求职目标"),
            ("text", "基本情况", "学校、专业、年级、成绩排名"),
            ("text", "求职意向", "目标岗位、目标行业、目标城市"),
            ("text", "为什么选这个行业", "行业判断依据与信息来源"),
            ("section", "二、岗位认知", "岗位职责、能力要求、市场供需"),
            ("text", "岗位每天都在做什么", "职责拆解，说明自己确实了解这个岗位"),
            ("grid", "岗位核心要求", "拆成并列的能力项"),
            ("text", "招聘信息分析", "主流企业同类岗位的要求归纳"),
            ("section", "三、能力匹配", "逐条对上岗位要求"),
            ("text", "专业能力", "课程、项目、技术栈怎么对上要求"),
            ("photo", "项目与实践", "项目照片、代码截图、实物照片"),
            ("grid", "成果与证书", "奖项、专利、论文、证书并列"),
            ("text", "实习经历", "做过什么、负责哪部分、产出是什么"),
            ("section", "四、职业规划", "入职后一到三年的打算"),
            ("text", "短期（0 到 1 年）", "上手期要补齐什么"),
            ("text", "中期（1 到 3 年）", "独立负责什么"),
            ("text", "长期", "往哪个方向发展"),
            ("text", "结语", "一句话收束"),
        ],
    },
    "挑战杯创业": {
        "name": "挑战杯 / 中国国际大学生创新大赛 · 创业计划",
        "basis": "两赛评审均围绕项目背景、产品与创新、市场与竞争、商业模式与财务、"
                 "团队与执行五条主线展开，路演通常 5 到 8 分钟",
        "outline": [
            ("cover", "封面", "项目名、一句话定位、团队与学校"),
            ("section", "一、项目背景", "痛点与机会"),
            ("text", "痛点", "用数据或真实案例说明问题有多严重"),
            ("text", "现有方案哪里不够", "竞品或传统做法的具体缺陷"),
            ("text", "政策与市场机会", "政策文件、市场规模、增长趋势"),
            ("section", "二、产品与创新", "做的是什么，创新点在哪"),
            ("text", "产品是什么", "一句话说清产品形态与使用方式"),
            ("photo", "产品实拍", "实物、界面、现场照片"),
            ("grid", "技术或模式创新点", "三到五条并列"),
            ("text", "技术壁垒", "专利、算法、工艺，凭什么别人做不出来"),
            ("section", "三、市场与竞争", "卖给谁，凭什么赢"),
            ("grid", "目标客户", "客户画像并列拆解"),
            ("text", "竞争分析", "与主要竞品的对比，优势与劣势都写"),
            ("text", "市场验证", "已经拿到的订单、试用、合作意向"),
            ("section", "四、商业模式", "怎么赚钱"),
            ("text", "收入来源", "谁付钱，付多少，付几次"),
            ("text", "成本结构", "主要成本项与毛利率"),
            ("text", "推广路径", "先打哪个场景，再复制到哪"),
            ("section", "五、团队与进展", "谁在做，做到哪一步"),
            ("photo", "团队成员", "核心成员与分工"),
            ("text", "项目进展", "里程碑、已有成果、下一步计划"),
            ("text", "融资与规划", "需要多少钱，用在什么地方"),
            ("text", "结语", "一句话收束"),
        ],
    },
}


def plan(style_dir, event_key):
    manifest = load_style(style_dir)
    kind_index = index_pages(manifest)
    outline = EVENTS[event_key]["outline"]
    used = set()
    # 封面的第二页（尾页）要留给收束，不能拿去当章节页
    reserved_covers = 1 if len(kind_index.get("cover", [])) > 1 else 0
    plan_pages = []
    missing = []
    for kind, title, hint in outline:
        page = pick(kind_index, kind, used)
        if page is not None and kind == "cover" and reserved_covers:
            # 章节页借用封面时，只借最后一页之外的
            reserved = set(p["page"] for p in kind_index.get("cover", [])[-reserved_covers:])
            if page["page"] in reserved:
                page = None
        if page is None:
            # 退而求其次：先找同类型的近亲，再退到通用内容页
            for fallback in FALLBACK.get(kind, ()):
                page = pick(kind_index, fallback, used)
                if page is not None:
                    missing.append("%s 没有 %s 版面，改用第 %d 页（%s）"
                                   % (title, kind, page["page"], fallback))
                    break
        if page is None:
            missing.append("%s 没有可用版面，已跳过" % title)
            continue
        used.add(page["page"])
        if page.get("specificity") == "specific" and kind not in ("cover", "photo"):
            missing.append("%s 用的是偏专属的版面（第 %d 页），原版是给别的主题画的，"
                           "填完务必看缩略图确认不别扭" % (title, page["page"]))
        slots = usable_slots(page)
        capacity = SLOT_CAPACITY.get(page["kind"], 4)
        picked_slots = slots[:capacity]
        plan_pages.append({
            "kind": page["kind"],
            "page": page["page"],
            "specificity": page.get("specificity", "unknown"),
            "section": title,
            "hint": hint,
            "capacity": capacity,
            "total_slots": len(slots),
            "fill_order": [s["slot"] for s in picked_slots],
            "slots": [{"slot": s["slot"], "role": s["role"],
                       "chars": s["chars"], "font_size": s["font_size"],
                       "sample": (s.get("sample") or "")[:40]}
                      for s in picked_slots],
        })
    available = {kind: len(pages) for kind, pages in kind_index.items()}
    return {
        "style": os.path.basename(os.path.abspath(style_dir)),
        "event": event_key,
        "event_name": EVENTS[event_key]["name"],
        "basis": EVENTS[event_key]["basis"],
        "capacity": available,
        "pages": plan_pages,
        "warnings": missing,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", help="风格包目录")
    parser.add_argument("--event", help="赛事骨架：职业规划成长 / 职业规划就业 / 挑战杯创业")
    parser.add_argument("--out", help="输出大纲 JSON")
    parser.add_argument("--list", action="store_true", help="列出可用赛事骨架")
    args = parser.parse_args()

    if args.list:
        for key, value in EVENTS.items():
            print("%-12s %s（%d 页）" % (key, value["name"], len(value["outline"])))
            print("             依据：%s" % value["basis"])
        return

    if not (args.style and args.event):
        raise SystemExit("需要 --style 与 --event，或使用 --list 查看骨架")
    if args.event not in EVENTS:
        raise SystemExit("未知赛事骨架 %r，可选：%s" % (args.event, "、".join(EVENTS)))

    result = plan(args.style, args.event)
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print("大纲已写到 %s（%d 页）" % (args.out, len(result["pages"])))
        for warning in result["warnings"]:
            print("  注意：", warning)
    else:
        print(text)


if __name__ == "__main__":
    main()
