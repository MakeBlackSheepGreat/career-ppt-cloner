import argparse
import json
import os
import sys

import fit
import rules

# 角色与字数倍数的对应：超限时记的等级与允许的倍数。
ROLE_LENGTH_LIMIT = {
    "display": ("FAIL", 1.5),
    "headline": ("FAIL", 1.5),
    "glyph": ("FAIL", 1.5),
    "label": ("WARN", 2.0),
    "body": ("FAIL", 2.5),
    "text": ("FAIL", 2.5),
    "title": ("FAIL", 2.5),
    "backdrop_note": ("FAIL", 2.5),
}
# 单段字数超过参考每段字数的倍数，超过即告警。
PARAGRAPH_RATIO = 2.0
# 缩字幅度：超过 WARN 值记告警，超过 FAIL 值记失败。
SHRINK_WARN = 0.20
SHRINK_FAIL = 0.35
# 封面页与章节页必须填的标题角色。参考页把标题分别标成 display、headline、title 三种。
TITLE_ROLES = ("display", "headline", "title")
# 章节页不该填的正文角色。
BODY_ROLES = ("body", "text")
# 内容条目没有指定字号时沿用的默认字号，与 fit.analyse 的缺省值一致。
DEFAULT_PT = 18.0


def finding(level, page, slot, role, rule, actual, limit):
    return {
        "level": level,
        "page": page,
        "slot": slot,
        "role": role,
        "rule": rule,
        "actual": actual,
        "limit": limit,
    }


def slot_lines(entry):
    """把条目里的 text 统一成按段拆开的字符串列表，与 fill.py 的写法一致。"""
    text = entry.get("text")
    if isinstance(text, list):
        return [str(line) for line in text]
    return str(text).split(chr(10))


def char_count(lines):
    return sum(len(line) for line in lines)


def resolve_entries(page_entry, page_manifest):
    """把 map 与 slots 两种写法统一成条目列表，简写按 fill_order 定位槽位号。"""
    if "map" in page_entry:
        return list(page_entry["map"]), 0
    raw = page_entry.get("slots")
    if raw is None:
        return [], 0
    order = list(page_manifest.get("fill_order") or [])
    entries = []
    overflow = 0
    for offset, item in enumerate(raw):
        if item is None:
            continue
        if isinstance(item, dict) and "slot" in item:
            entries.append(dict(item))
            continue
        if offset >= len(order):
            overflow += 1
            continue
        if isinstance(item, dict):
            entry = dict(item)
            entry["slot"] = order[offset]
        else:
            entry = {"slot": order[offset], "text": item}
        entries.append(entry)
    return entries, overflow


def check_slot(page, entry, manifest_slot, limits, findings):
    """查一个槽位的字数、段长、字号下限与缩字幅度，返回通过项的实测值与阈值。"""
    number = manifest_slot["slot"]
    role = manifest_slot.get("role")
    if role not in ROLE_LENGTH_LIMIT:
        raise SystemExit("槽位 %s 的角色 %r 不在判据表内，先补 ROLE_LENGTH_LIMIT" % (number, role))
    lines = slot_lines(entry)
    total = char_count(lines)
    reference = manifest_slot.get("chars") or 0
    per_paragraph = manifest_slot.get("per_paragraph") or 0
    level, ratio = ROLE_LENGTH_LIMIT[role]
    measured = []
    thresholds = []

    if reference > 0:
        got = total / float(reference)
        measured.append("%.2f" % got)
        thresholds.append("%.1f倍" % ratio)
        if got > ratio:
            findings.append(finding(
                level, page, number, role, "字数超参考",
                "%d字/参考%d字=%.2f倍" % (total, reference, got),
                "不超过%.1f倍" % ratio))
    else:
        measured.append("无参考")
        thresholds.append("参考字数=0")

    if per_paragraph > 0 and lines:
        longest = max(len(line) for line in lines)
        got = longest / float(per_paragraph)
        measured.append("%.2f" % got)
        thresholds.append("%.1f倍" % PARAGRAPH_RATIO)
        if got > PARAGRAPH_RATIO:
            findings.append(finding(
                "WARN", page, number, role, "单段超参考",
                "最长%d字/参考%d字=%.2f倍" % (longest, per_paragraph, got),
                "不超过%.1f倍" % PARAGRAPH_RATIO))
    else:
        measured.append("无参考")
        thresholds.append("参考每段=0")

    requested = float(entry["font_size"]) if entry.get("font_size") else float(
        manifest_slot.get("font_size") or DEFAULT_PT)
    analysis = fit.analyse(manifest_slot, lines, requested,
                           entry.get("line_spacing"), entry.get("space_after") or 0.0)
    fitted = analysis["fitted_pt"]
    floor = limits[role]
    measured.append("%.1fpt" % fitted)
    thresholds.append("下限%.1fpt" % floor)
    if fitted + 0.01 < floor:
        findings.append(finding(
            "FAIL", page, number, role, "字号下限",
            "实用%.1fpt" % fitted, "不低于%.1fpt" % floor))

    shrink = (requested - fitted) / requested if requested > 0 else 0.0
    measured.append("%.0f%%" % (shrink * 100))
    thresholds.append("不超过%.0f%%" % (SHRINK_WARN * 100))
    if shrink > SHRINK_FAIL:
        findings.append(finding(
            "FAIL", page, number, role, "缩字幅度",
            "需求%.1fpt->实用%.1fpt=%.0f%%" % (requested, fitted, shrink * 100),
            "不超过%.0f%%" % (SHRINK_FAIL * 100)))
    elif shrink > SHRINK_WARN:
        findings.append(finding(
            "WARN", page, number, role, "缩字幅度",
            "需求%.1fpt->实用%.1fpt=%.0f%%" % (requested, fitted, shrink * 100),
            "不超过%.0f%%" % (SHRINK_WARN * 100)))
    return measured, thresholds


def photo_target(entry):
    raw = entry.get("target", entry.get("photo_slot", ""))
    return str(raw)


def check_photos(page, page_manifest, page_entry, entries, findings, passes):
    """照片槽：文件是否存在、槽号是否存在、该页照片槽是否漏填。"""
    declared = page_manifest.get("photos") or []
    available = {str(item["photo_slot"]) for item in declared}
    declared_entries = list(page_entry.get("photos") or [])
    declared_entries += [entry for entry in entries if entry.get("photo")]
    used = set()
    seen_photo = set()
    for entry in declared_entries:
        key = (photo_target(entry), str(entry.get("photo") or ""))
        if key in seen_photo:
            continue
        seen_photo.add(key)
        target = photo_target(entry)
        if not target:
            findings.append(finding(
                "FAIL", page, "-", "-", "照片槽号缺失",
                "条目没有 photo_slot 或 target", "必填"))
            continue
        used.add(target)
        if target not in available:
            findings.append(finding(
                "FAIL", page, target, "-", "照片槽存在",
                "本页照片槽 %s" % ("、".join(sorted(available)) or "无"),
                "槽号在本页照片槽内"))
        path = entry.get("photo")
        if not path:
            findings.append(finding(
                "FAIL", page, target, "-", "照片路径缺失",
                "条目没有 photo 字段", "必填"))
        elif not os.path.exists(path):
            findings.append(finding(
                "FAIL", page, target, "-", "照片文件存在",
                "找不到 %s" % path, "文件必须存在"))
    missing = sorted(available - used)
    if missing:
        findings.append(finding(
            "WARN", page, "-", "-", "照片槽漏填",
            "缺 %s" % "、".join(missing), "填满本页 %d 个照片槽" % len(available)))
    elif available:
        passes.append(finding(
            "PASS", page, "-", "-", "照片槽填满",
            "%d 个" % len(available), "填满 %d 个" % len(available)))


def audit(content, manifest, profile):
    limits = rules.profile_limits(profile)
    if not isinstance(content, dict) or not isinstance(content.get("pages"), list):
        raise SystemExit("内容 JSON 顶层缺少 pages 数组，实际顶层类型 %s"
                         % type(content).__name__)
    manifest_by_page = {page["page"]: page for page in manifest["pages"]}
    defaults = list(content.get("defaults", {}).get("all", []))
    per_page = []
    for page_entry in content.get("pages", []):
        findings = []
        passes = []
        number = page_entry.get("page")
        if number is None:
            findings.append(finding("FAIL", "-", "-", "-", "页码缺失",
                                    "内容页没有 page 字段", "必填"))
            per_page.append((number, findings, passes))
            continue
        if number not in manifest_by_page:
            findings.append(finding(
                "FAIL", number, "-", "-", "页码存在",
                "风格包共 %d 页" % len(manifest_by_page),
                "页码在 %d-%d 之内" % (min(manifest_by_page), max(manifest_by_page))))
            per_page.append((number, findings, passes))
            continue
        page_manifest = manifest_by_page[number]
        lookup = {slot["slot"]: slot for slot in page_manifest["slots"]}
        page_entries, overflow = resolve_entries(page_entry, page_manifest)
        entries = defaults + page_entries
        if overflow:
            findings.append(finding(
                "FAIL", number, "-", "-", "简写位超量",
                "多出 %d 项" % overflow,
                "本页简写最多 %d 项" % len(page_manifest.get("fill_order") or [])))

        seen = {}
        for entry in entries:
            if entry.get("photo"):
                continue
            slot_number = entry.get("slot")
            if slot_number is None:
                findings.append(finding("FAIL", number, "-", "-", "槽位号缺失",
                                        "条目没有 slot 字段", "必填"))
                continue
            seen[slot_number] = seen.get(slot_number, 0) + 1
        for slot_number, times in sorted(seen.items()):
            if times > 1:
                findings.append(finding(
                    "FAIL", number, slot_number, "-", "槽位重复",
                    "同一槽位填了 %d 次" % times, "每槽只填一次"))

        filled_roles = []
        checked = set()
        for entry in entries:
            if entry.get("photo"):
                continue
            slot_number = entry.get("slot")
            if slot_number is None or slot_number in checked:
                continue
            checked.add(slot_number)
            manifest_slot = lookup.get(slot_number)
            if manifest_slot is None:
                findings.append(finding(
                    "FAIL", number, slot_number, "-", "槽位存在",
                    "本页槽位 %s" % "、".join(str(key) for key in sorted(lookup)),
                    "槽位号在本页槽位清单内"))
                continue
            if entry.get("text") is None:
                continue
            role = manifest_slot.get("role")
            before = len(findings)
            measured, thresholds = check_slot(number, entry, manifest_slot, limits, findings)
            filled_roles.append(role)
            if len(findings) == before:
                passes.append(finding(
                    "PASS", number, slot_number, role, "字数/段长/字号/缩字",
                    "/".join(measured), "/".join(thresholds)))

        page_chars = 0
        for entry in entries:
            if entry.get("photo") or entry.get("text") is None:
                continue
            page_chars += char_count(slot_lines(entry))
        if profile == "presentation":
            if page_chars > rules.MAX_PAGE_CHARS:
                findings.append(finding(
                    "WARN", number, "-", "-", "单页总字数",
                    "%d字" % page_chars, "不超过%d字" % rules.MAX_PAGE_CHARS))
            else:
                passes.append(finding(
                    "PASS", number, "-", "-", "单页总字数",
                    "%d字" % page_chars, "不超过%d字" % rules.MAX_PAGE_CHARS))

        kind = page_manifest.get("kind")
        if kind in ("cover", "section"):
            if any(role in TITLE_ROLES for role in filled_roles):
                passes.append(finding(
                    "PASS", number, "-", "-", "页面标题",
                    "已填 %s" % "/".join(role for role in filled_roles if role in TITLE_ROLES),
                    "至少填 1 个 %s 角色槽位" % "/".join(TITLE_ROLES)))
            else:
                findings.append(finding(
                    "FAIL", number, "-", "-", "页面标题缺失",
                    "%s 页没填标题槽位" % kind,
                    "至少填 1 个 %s 角色槽位" % "/".join(TITLE_ROLES)))
        if kind == "section":
            for entry in entries:
                if entry.get("photo") or entry.get("text") is None:
                    continue
                manifest_slot = lookup.get(entry.get("slot"))
                if manifest_slot is None:
                    continue
                if manifest_slot.get("role") in BODY_ROLES:
                    findings.append(finding(
                        "WARN", number, manifest_slot["slot"], manifest_slot.get("role"),
                        "章节页填正文",
                        "填了 %d 字" % char_count(slot_lines(entry)),
                        "章节页不填 %s 角色槽位" % "/".join(BODY_ROLES)))

        check_photos(number, page_manifest, page_entry, entries, findings, passes)
        per_page.append((number, findings, passes))
    return per_page


def format_finding(item):
    return "%-4s 页%-3s 槽%-4s 角色%-12s %-12s 实测=%-22s 阈值=%s" % (
        item["level"],
        item["page"],
        "-" if item["slot"] is None else item["slot"],
        "-" if item["role"] is None else item["role"],
        item["rule"],
        item["actual"],
        item["limit"])


def main():
    parser = argparse.ArgumentParser(description="内容与版面匹配量化门")
    parser.add_argument("--style", required=True, help="风格包目录")
    parser.add_argument("--content", required=True, help="内容 JSON")
    parser.add_argument("--profile", default="presentation", choices=rules.PROFILES,
                        help="字号下限口径")
    parser.add_argument("--json", default="", help="把全部判据写成 JSON")
    args = parser.parse_args()

    slots_path = os.path.join(args.style, "slots.json")
    if not os.path.exists(slots_path):
        raise SystemExit("风格包缺少 slots.json：%s" % slots_path)
    if not os.path.exists(args.content):
        raise SystemExit("内容文件不存在：%s" % args.content)
    with open(slots_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        raise SystemExit("风格包的 slots.json 缺少 pages 数组：%s" % slots_path)
    with open(args.content, encoding="utf-8") as handle:
        content = json.load(handle)

    per_page = audit(content, manifest, args.profile)
    fails = []
    warns = []
    passed = []
    for _number, findings, passes in per_page:
        for item in findings + passes:
            print(format_finding(item))
            if item["level"] == "FAIL":
                fails.append(item)
            elif item["level"] == "WARN":
                warns.append(item)
            else:
                passed.append(item)
    print("gate_content: FAIL=%d WARN=%d PASS=%d" % (len(fails), len(warns), len(passed)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({
                "style": args.style,
                "content": args.content,
                "profile": args.profile,
                "findings": [item for _n, findings, passes in per_page
                             for item in findings + passes],
            }, handle, ensure_ascii=False, indent=1)
        print("报告 %s" % args.json)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())