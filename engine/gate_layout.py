"""版面量化门：把「文字有没有压到装饰、有没有溢出、层级是否分明」变成可复核的数字。

用法：
    python gate_layout.py --pptx 成品.pptx --profile presentation [--json 报告.json]

判据全部可量化，阈值集中在 rules.py：
1. 越界：形状超出页面边界超过容差。
2. 页边：文字框距页面四边小于最小留白。
3. 溢出：按 fit 的折行估算，文字所需高度超过框内可用高度。
4. 遮挡：上层不透明形状覆盖文字框面积超过阈值。
5. 重叠：两个文字框互相覆盖面积超过较小框的阈值。
6. 字号下限：按角色与口径档位查最低字号，低于下限判失败。
7. 自动缩字：normAutofit 的 fontScale 把字号压到下限以下判失败。
8. 层级：页面主标题字号不足正文字号的倍数。
9. 居中：文字框中点与底衬框中点偏差超过容差。
10. 行数：正文行数超过投影页上限。
11. 变形：图片框长宽比与源图长宽比偏差超过阈值。
"""
import argparse
import json
import math
import os
import sys

import fit
import rules


RULES = ("越界", "页边", "溢出", "遮挡", "重叠", "字号下限", "自动缩字",
         "层级", "行数", "居中", "变形")

MAX_ASPECT_DEVIATION = 0.05
MAX_TEXT_OVERLAP_RATIO = 0.30
# 出血版式：装饰图故意超出页面边缘，这个幅度以内不算缺陷。
BLEED_ALLOWANCE_CM = 3.0
# fit 的折行高度是估算值，留 8% 余量再判溢出。
OVERFLOW_TOLERANCE = 0.08
# 居中复核只对「底衬与文字框尺寸相当」的槽位生效，大卡片里的小文字本来就该偏。
CENTRE_SIZE_RATIO = 1.8


def finding(level, page, rule, detail, actual, limit):
    return {
        "level": level,
        "page": page,
        "rule": rule,
        "detail": detail,
        "actual": actual,
        "limit": limit,
    }


def z_order(slide):
    """按 spTree 里的文档顺序给形状编号，编号越大越靠上层。

    组合里的子形状不在 spTree 顶层，层级由它所在的最外层组合决定。
    """
    tree = slide.shapes._spTree
    top_level = {}
    for index, element in enumerate(tree):
        top_level[element] = index
    order = {}

    def walk(shapes, inherited):
        for shape in shapes:
            element = shape._element
            rank = top_level.get(element, inherited)
            order[element] = rank
            if shape.shape_type == rules.MSO_SHAPE_TYPE.GROUP:
                walk(shape.shapes, rank)

    walk(slide.shapes, 0)
    return order


def is_opaque(shape, scheme):
    fill = rules.shape_fill(shape)
    if fill["kind"] == "picture":
        return True
    if fill["kind"] == "solid" and fill["color"]:
        return True
    if fill["kind"] == "gradient":
        return True
    return False


def shape_fill_color(shape, scheme):
    fill = rules.shape_fill(shape)
    return rules.resolve_color(fill["color"], scheme) if fill["color"] else None


def text_need_height_cm(slot):
    """用 fit 的折行估算这段文字实际需要的高度。"""
    width_limit, height_limit = rules.usable_area_cm(slot)
    size = slot.get("font_size") or 18.0
    lines = [paragraph for paragraph in slot["text"].split(chr(10))]
    wrapped = fit.wrap_block(lines, width_limit, size)
    height = fit.block_height_cm(wrapped, size, slot.get("line_spacing"))
    return height, height_limit, len(wrapped)


def check_boundary(slide_number, slots, pictures, slide_w, slide_h, findings):
    for slot in slots:
        box = (slot["left"], slot["top"], slot["width"], slot["height"])
        over_left = -box[0]
        over_top = -box[1]
        over_right = box[0] + box[2] - slide_w
        over_bottom = box[1] + box[3] - slide_h
        worst = max(over_left, over_top, over_right, over_bottom)
        if worst > rules.BOUNDARY_TOLERANCE_CM:
            findings.append(finding(
                "FAIL", slide_number, "越界", "槽位 %d「%s」超出页面 %.2fcm"
                % (slot["slot"], slot["text"][:12], worst), round(worst, 3), rules.BOUNDARY_TOLERANCE_CM))
    for item in pictures:
        box = (item["left"], item["top"], item["width"], item["height"])
        worst = max(-box[0], -box[1], box[0] + box[2] - slide_w, box[1] + box[3] - slide_h)
        if worst > BLEED_ALLOWANCE_CM:
            findings.append(finding(
                "WARN", slide_number, "越界", "图片 %s 超出页面 %.2fcm"
                % (item["name"], worst), round(worst, 3), BLEED_ALLOWANCE_CM))


def check_margin(slide_number, slots, slide_w, slide_h, findings):
    for slot in slots:
        if slot["chrome"]:
            continue
        left = slot["left"]
        top = slot["top"]
        right = slide_w - (slot["left"] + slot["width"])
        bottom = slide_h - (slot["top"] + slot["height"])
        worst = min(left, top, right, bottom)
        if worst < rules.MIN_MARGIN_CM:
            findings.append(finding(
                "WARN", slide_number, "页边", "槽位 %d「%s」距页边 %.2fcm"
                % (slot["slot"], slot["text"][:12], worst), round(worst, 3), rules.MIN_MARGIN_CM))


def check_overflow(slide_number, slots, findings):
    for slot in slots:
        if slot["role"] == "glyph":
            continue
        # 文本框开了 normAutofit 时 PowerPoint 自己会缩字，这不是溢出缺陷。
        if slot.get("autofit") == "normAutofit":
            continue
        height, limit, line_count = text_need_height_cm(slot)
        if height > limit * (1.0 + OVERFLOW_TOLERANCE):
            findings.append(finding(
                "FAIL", slide_number, "溢出", "槽位 %d「%s」需要 %.2fcm 高，框内只有 %.2fcm（%d 行）"
                % (slot["slot"], slot["text"][:12], height, limit, line_count),
                round(height, 2), round(limit, 2)))


def check_occlusion(slide_number, slide, slots, scheme, findings, slide_width, slide_height):
    order = z_order(slide)
    others = []
    for shape in rules.iter_shapes(slide.shapes):
        if not shape.has_text_frame or not shape.text_frame.text.strip():
            if rules.bbox_cm(shape) is not None and is_opaque(shape, scheme):
                others.append((order.get(shape._element, 0), shape, rules.bbox_cm(shape)))
    for slot in slots:
        if slot["role"] == "glyph":
            continue
        subject = (slot["left"], slot["top"], slot["width"], slot["height"])
        area = subject[2] * subject[3]
        if area <= 0:
            continue
        subject_order = order.get(None, 0)
        for shape in rules.iter_shapes(slide.shapes):
            if shape.shape_id == slot["shape_id"]:
                subject_order = order.get(shape._element, 0)
                break
        for shape_order, shape, box in others:
            if shape_order <= subject_order:
                continue
            # 满版背景图不算遮挡，文字本来就压在背景上。
            if box[2] >= slide_width * 0.88 and box[3] >= slide_height * 0.8:
                continue
            covered = rules.overlap_area_cm(subject, box) / area
            if covered > rules.OCCLUSION_RATIO:
                # 组合版式里上层色块可能是文字的高亮底衬，几何判断分不清，
                # 所以记告警，由看图确认。
                findings.append(finding(
                    "WARN", slide_number, "遮挡", "槽位 %d「%s」被上层形状 %s 覆盖 %.0f%%"
                    % (slot["slot"], slot["text"][:12], shape.name, covered * 100),
                    round(covered, 3), rules.OCCLUSION_RATIO))


def check_text_overlap(slide_number, slots, findings):
    for index, first in enumerate(slots):
        if first["role"] == "glyph":
            continue
        for second in slots[index + 1:]:
            if second["role"] == "glyph":
                continue
            a = (first["left"], first["top"], first["width"], first["height"])
            b = (second["left"], second["top"], second["width"], second["height"])
            overlap = rules.overlap_area_cm(a, b)
            smaller = min(a[2] * a[3], b[2] * b[3])
            if smaller <= 0:
                continue
            ratio = overlap / smaller
            if ratio > MAX_TEXT_OVERLAP_RATIO:
                findings.append(finding(
                    "FAIL", slide_number, "重叠", "槽位 %d 与槽位 %d 互相覆盖 %.0f%%"
                    % (first["slot"], second["slot"], ratio * 100),
                    round(ratio, 3), MAX_TEXT_OVERLAP_RATIO))


def effective_size(slot):
    size = slot.get("font_size") or 0.0
    return round(size * (slot.get("font_scale") or 1.0), 2)


def check_font_floor(slide_number, slots, limits, findings):
    for slot in slots:
        role = "chrome" if slot["chrome"] else slot["role"]
        floor = limits.get(role, limits["text"])
        size = effective_size(slot)
        if size <= 0:
            continue
        if size + 0.01 < floor:
            findings.append(finding(
                "FAIL", slide_number, "字号下限",
                "槽位 %d「%s」角色 %s 实际 %.1fpt" % (slot["slot"], slot["text"][:12], role, size),
                size, floor))
        elif slot.get("font_scale") and slot["font_scale"] < 0.9:
            findings.append(finding(
                "WARN", slide_number, "自动缩字",
                "槽位 %d「%s」被 normAutofit 压到 %.0f%%（%.1fpt -> %.1fpt）"
                % (slot["slot"], slot["text"][:12], slot["font_scale"] * 100,
                   slot["font_size"], size),
                round(slot["font_scale"], 3), 0.9))


def check_hierarchy(slide_number, slots, findings):
    headlines = [s for s in slots if s["role"] in ("display", "headline", "title") and not s["chrome"]]
    bodies = [s for s in slots if s["role"] in ("body", "text") and not s["chrome"]]
    if not headlines or not bodies:
        return
    title_size = max(effective_size(s) for s in headlines)
    body_size = max(effective_size(s) for s in bodies)
    if body_size <= 0:
        return
    ratio = title_size / body_size
    if ratio + 0.01 < rules.HIERARCHY_RATIO:
        findings.append(finding(
            "WARN", slide_number, "层级", "标题 %.1fpt 与正文 %.1fpt 相差 %.2f 倍"
            % (title_size, body_size, ratio), round(ratio, 2), rules.HIERARCHY_RATIO))


def check_body_lines(slide_number, slots, findings):
    for slot in slots:
        if slot["chrome"] or slot["role"] not in ("body", "text", "backdrop_note"):
            continue
        _height, _limit, line_count = text_need_height_cm(slot)
        if line_count > rules.MAX_BODY_LINES:
            findings.append(finding(
                "WARN", slide_number, "行数", "槽位 %d「%s」折行后 %d 行"
                % (slot["slot"], slot["text"][:12], line_count),
                line_count, rules.MAX_BODY_LINES))


def check_centering(slide_number, slide, slots, findings):
    """只对一个底衬框里只装一个文字框的槽位复核居中。

    一个卡片里同时放标题与正文是常见版式，正文本来就该排在标题下方，
    拿卡片中点去要求它也居中会误判。
    """
    shapes = list(rules.iter_shapes(slide.shapes))
    slide_area = 0.0
    for shape in shapes:
        box = rules.bbox_cm(shape)
        if box:
            slide_area = max(slide_area, box[2] * box[3])
    backplate_owner = {}
    subject_of = {}
    for slot in slots:
        if slot["role"] in ("glyph", "backdrop_note"):
            continue
        for shape in shapes:
            if shape.shape_id == slot["shape_id"]:
                subject_of[slot["slot"]] = shape
                break
        subject_shape = subject_of.get(slot["slot"])
        if subject_shape is None:
            continue
        backplate = rules.find_backplate(slot, shapes, slide_area * 2.6)
        if backplate is None:
            continue
        backplate_owner.setdefault(backplate.shape_id, []).append(slot["slot"])
        slot["_backplate"] = backplate
    for slot in slots:
        if slot["role"] in ("glyph", "backdrop_note"):
            continue
        backplate = slot.get("_backplate")
        if backplate is None:
            continue
        if len(backplate_owner.get(backplate.shape_id, [])) > 1:
            continue
        box = rules.bbox_cm(backplate)
        if box is None:
            continue
        size_ratio = (box[2] * box[3]) / float(slot["width"] * slot["height"])
        if size_ratio > CENTRE_SIZE_RATIO:
            continue
        text_centre = rules.centre_cm((slot["left"], slot["top"], slot["width"], slot["height"]))
        plate_centre = rules.centre_cm(box)
        dx = text_centre[0] - plate_centre[0]
        dy = text_centre[1] - plate_centre[1]
        worst = max(abs(dx), abs(dy))
        if worst > rules.CENTRE_TOLERANCE_CM:
            findings.append(finding(
                "WARN", slide_number, "居中", "槽位 %d「%s」与底衬 %s 偏差 dx=%.2f dy=%.2f"
                % (slot["slot"], slot["text"][:12], backplate.name, dx, dy),
                round(worst, 3), rules.CENTRE_TOLERANCE_CM))


def check_pictures(slide_number, slide, pictures, findings):
    for item in pictures:
        shape = None
        for candidate in rules.iter_shapes(slide.shapes):
            if candidate.shape_id == item["shape_id"]:
                shape = candidate
                break
        if shape is None or item["width"] <= 0 or item["height"] <= 0:
            continue
        try:
            image_w, image_h = shape.image.size
        except Exception:
            continue
        if not image_w or not image_h:
            continue
        frame_ratio = item["width"] / float(item["height"])
        image_ratio = image_w / float(image_h)
        if image_ratio <= 0:
            continue
        deviation = abs(frame_ratio - image_ratio) / image_ratio
        cropped = bool(shape.crop_left or shape.crop_right or shape.crop_top or shape.crop_bottom)
        if deviation > MAX_ASPECT_DEVIATION and not cropped:
            findings.append(finding(
                "WARN", slide_number, "变形", "图片 %s 框比例 %.2f 与源图比例 %.2f 偏差 %.0f%%"
                % (item["name"], frame_ratio, image_ratio, deviation * 100),
                round(deviation, 3), MAX_ASPECT_DEVIATION))


def describe_pictures(slide, slide_w, slide_h):
    pictures = []
    for shape in rules.iter_shapes(slide.shapes):
        if shape.shape_type != rules.MSO_SHAPE_TYPE.PICTURE:
            continue
        box = rules.bbox_cm(shape)
        if box is None:
            continue
        pictures.append({
            "name": shape.name,
            "shape_id": shape.shape_id,
            "left": box[0], "top": box[1], "width": box[2], "height": box[3],
        })
    return pictures


def audit(path, profile):
    limits = rules.profile_limits(profile)
    presentation, slide_w, slide_h, scheme = rules.open_presentation(path)
    findings = []
    for number, slide in enumerate(presentation.slides, 1):
        slots = rules.describe_slots(slide, slide_w, slide_h, scheme)
        pictures = describe_pictures(slide, slide_w, slide_h)
        check_boundary(number, slots, pictures, slide_w, slide_h, findings)
        check_margin(number, slots, slide_w, slide_h, findings)
        check_overflow(number, slots, findings)
        check_occlusion(number, slide, slots, scheme, findings, slide_w, slide_h)
        check_text_overlap(number, slots, findings)
        check_font_floor(number, slots, limits, findings)
        check_hierarchy(number, slots, findings)
        check_body_lines(number, slots, findings)
        check_centering(number, slide, slots, findings)
        check_pictures(number, slide, pictures, findings)
    return presentation, findings


def main():
    parser = argparse.ArgumentParser(description="版面量化门")
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--profile", default="presentation", choices=rules.PROFILES)
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    if not os.path.exists(args.pptx):
        raise SystemExit("文件不存在：%s" % args.pptx)
    presentation, findings = audit(args.pptx, args.profile)

    for item in findings:
        print("%-4s 页%-3d %-6s %s  实测=%s 阈值=%s"
              % (item["level"], item["page"], item["rule"], item["detail"],
                 item["actual"], item["limit"]))
    fails = [item for item in findings if item["level"] == "FAIL"]
    warns = [item for item in findings if item["level"] == "WARN"]
    print("gate_layout: 页数=%d 判据=%d FAIL=%d WARN=%d"
          % (len(presentation.slides), len(RULES), len(fails), len(warns)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"pptx": args.pptx, "profile": args.profile,
                       "pages": len(presentation.slides), "findings": findings},
                      handle, ensure_ascii=False, indent=1)
        print("报告 %s" % args.json)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
