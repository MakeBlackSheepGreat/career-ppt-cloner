import argparse
import io
import json
import math
import os
import sys

from PIL import Image

import rules


# Machado 2009 线性 RGB 色觉缺陷矩阵。
CVD_MATRICES = {
    "protanopia": [
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ],
    "deuteranopia": [
        [0.367322, 0.860646, -0.227968],
        [0.280085, 0.672501, 0.047413],
        [-0.011820, 0.042940, 0.968881],
    ],
    "tritanopia": [
        [1.255528, -0.076749, -0.178779],
        [-0.078411, 0.930809, 0.147602],
        [0.004733, 0.691367, 0.303900],
    ],
}

# 色觉缺陷模拟后 CIE76 色差下限，低于此值判为可混淆。
CONFUSABLE_DELTA_E = 12.0
# Rec.709 亮度差下限，低于此值判为灰度可混淆。
GRAYSCALE_MIN_DELTA = 0.03
# 正文与背景的 WCAG 对比度下限与舒适值，与 rules.py 共用一套口径。
CONTRAST_MIN = rules.CONTRAST_MIN
CONTRAST_COMFORT = rules.CONTRAST_COMFORT
# 单页配色数量上限，沿用 Paul Tol 亮色板的 6 色口径。
MAX_PAGE_COLORS = rules.MAX_PAGE_COLORS
# 页眉页脚与页码属于辅助信息，投影口径放宽到 3.0，自读与论文口径按正文标准。
CHROME_CONTRAST = {"presentation": 3.0, "reading": 4.5, "paper": 4.5}
# 黑白不是配色，统计单页色数时剔除。
NEUTRAL_COLORS = ("#FFFFFF", "#000000")
# 文字压在图片上时对比度不可测，图片覆盖文字框超过这个比例才按整块压在图上处理。
PICTURE_COVER_RATIO = 0.90
# 图片底衬按网格降采样取色，10 分位对比度作为判定值，避免单个抗锯齿像素把结论拉偏。
PICTURE_GRID = 24
PICTURE_PERCENTILE = 10


def finding(level, rule, detail, actual, limit, page=None):
    return {"level": level, "page": page, "rule": rule, "detail": detail,
            "actual": actual, "limit": limit}


def linear_rgb(hex_color):
    """把 #RRGGBB 转成线性 RGB，供色觉缺陷矩阵使用。"""
    red, green, blue = rules.hex_to_rgb(hex_color)
    return tuple(channel / 12.92 if channel <= 0.04045
                 else ((channel + 0.055) / 1.055) ** 2.4
                 for channel in (red, green, blue))


def apply_matrix(rgb, matrix):
    return tuple(sum(matrix[row][column] * rgb[column] for column in range(3))
                 for row in range(3))


def linear_to_lab(rgb):
    """线性 RGB(D65) 经 XYZ 转 CIELAB。"""
    red, green, blue = rgb
    x = 0.4124564 * red + 0.3575761 * green + 0.1804375 * blue
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = 0.0193339 * red + 0.1191920 * green + 0.9503041 * blue

    def f(value):
        delta = 6.0 / 29.0
        return value ** (1.0 / 3.0) if value > delta ** 3 else value / (3 * delta ** 2) + 4.0 / 29.0

    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e76(first, second):
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def grayscale_luma(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def parse_colors(text):
    colors = []
    for item in text.split(","):
        value = item.strip()
        if not value:
            continue
        if not value.startswith("#") or len(value) != 7:
            raise SystemExit("颜色格式错误（应为 #RRGGBB）：%s" % value)
        int(value[1:], 16)
        colors.append(value.upper())
    if len(colors) < 2:
        raise SystemExit("至少需要 2 个颜色才能查可混淆对")
    return colors


def check_palette(colors):
    findings = []
    rgbs = [linear_rgb(color) for color in colors]
    for simulation, matrix in CVD_MATRICES.items():
        labs = [linear_to_lab(apply_matrix(rgb, matrix)) for rgb in rgbs]
        pairs = []
        for first in range(len(labs)):
            for second in range(first + 1, len(labs)):
                value = delta_e76(labs[first], labs[second])
                if value < CONFUSABLE_DELTA_E:
                    pairs.append((colors[first], colors[second], round(value, 2)))
        if not pairs:
            findings.append(finding("PASS", simulation, "可混淆对=0", "0", CONFUSABLE_DELTA_E))
        for left, right, value in pairs:
            findings.append(finding("FAIL", simulation,
                                    "%s 与 %s 色差 %.2f" % (left, right, value),
                                    "%.2f" % value, CONFUSABLE_DELTA_E))
    lumas = [grayscale_luma(rgb) for rgb in rgbs]
    grey_pairs = []
    for first in range(len(lumas)):
        for second in range(first + 1, len(lumas)):
            value = abs(lumas[first] - lumas[second])
            if value < GRAYSCALE_MIN_DELTA:
                grey_pairs.append((colors[first], colors[second], round(value, 4)))
    if not grey_pairs:
        findings.append(finding("PASS", "grayscale", "可混淆对=0", "0", GRAYSCALE_MIN_DELTA))
    for left, right, value in grey_pairs:
        findings.append(finding("FAIL", "grayscale",
                                "%s 与 %s 亮度差 %.4f" % (left, right, value),
                                "%.4f" % value, GRAYSCALE_MIN_DELTA))
    return findings


class PictureSampler:
    """按形状缓存图片像素，取文字框下方区域的对比度分布。"""

    def __init__(self):
        self.cache = {}

    def image(self, shape):
        key = shape.shape_id
        if key not in self.cache:
            self.cache[key] = Image.open(io.BytesIO(shape.image.blob)).convert("RGB")
        return self.cache[key]

    def contrasts(self, shape, box, foreground):
        image = self.image(shape)
        frame_left = rules.cm_of(shape.left)
        frame_top = rules.cm_of(shape.top)
        frame_width = rules.cm_of(shape.width)
        frame_height = rules.cm_of(shape.height)
        if frame_width <= 0 or frame_height <= 0:
            return []
        left = (box[0] - frame_left) / frame_width
        top = (box[1] - frame_top) / frame_height
        width = box[2] / frame_width
        height = box[3] / frame_height
        px0 = max(0, int(left * image.width))
        py0 = max(0, int(top * image.height))
        px1 = min(image.width, int((left + width) * image.width))
        py1 = min(image.height, int((top + height) * image.height))
        if px1 <= px0 or py1 <= py0:
            return []
        crop = image.crop((px0, py0, px1, py1)).resize((PICTURE_GRID, PICTURE_GRID), Image.LANCZOS)
        raw = crop.tobytes()
        values = []
        for offset in range(0, len(raw), 3):
            hexed = "#%02X%02X%02X" % (raw[offset], raw[offset + 1], raw[offset + 2])
            value = rules.contrast_ratio(foreground, hexed)
            if value is not None:
                values.append((value, hexed))
        values.sort()
        return values


def picture_underlay(slot, shapes):
    """文字框中心落在整张图片上时返回那张图片。"""
    subject = (slot["left"], slot["top"], slot["width"], slot["height"])
    area = subject[2] * subject[3]
    if area <= 0:
        return None
    centre_x, centre_y = rules.centre_cm(subject)
    for shape in shapes:
        if shape.shape_type != rules.MSO_SHAPE_TYPE.PICTURE:
            continue
        box = rules.bbox_cm(shape)
        if box is None or box[2] <= 0 or box[3] <= 0:
            continue
        if not (box[0] <= centre_x <= box[0] + box[2] and box[1] <= centre_y <= box[1] + box[3]):
            continue
        if rules.overlap_area_cm(box, subject) / area >= PICTURE_COVER_RATIO:
            return shape
    return None


def slot_underlay(slot, shapes, slide_area, background, scheme, sampler):
    """返回 (对比度判定值, 前景, 背景描述, 最低对比度, 最低处的背景色)。"""
    foreground = rules.resolve_color(slot["color"], scheme)
    if foreground is None:
        return None
    box = (slot["left"], slot["top"], slot["width"], slot["height"])
    plate = rules.find_backplate(slot, shapes, slide_area)
    if plate is not None:
        fill = rules.shape_fill(plate)
        if fill["kind"] == "solid":
            backdrop = rules.resolve_color(fill["color"], scheme)
            if backdrop is not None:
                value = rules.contrast_ratio(foreground, backdrop)
                return (value, foreground, backdrop, value, backdrop)
        if fill["kind"] == "picture":
            values = sampler.contrasts(plate, box, foreground)
            if values:
                index = max(0, int(len(values) * PICTURE_PERCENTILE / 100.0) - 1)
                return (values[index][0], foreground, values[index][1],
                        values[0][0], values[0][1])
    if isinstance(background, str) and background.startswith("#"):
        value = rules.contrast_ratio(foreground, background)
        if value is not None:
            return (value, foreground, background, value, background)
    underlay = picture_underlay(slot, shapes)
    if underlay is not None:
        values = sampler.contrasts(underlay, box, foreground)
        if values:
            index = max(0, int(len(values) * PICTURE_PERCENTILE / 100.0) - 1)
            return (values[index][0], foreground, values[index][1],
                    values[0][0], values[0][1])
    return None


def audit_page(number, slide, presentation, scheme, slide_w, slide_h, slide_area, profile):
    background = rules.slide_background(slide, presentation, scheme)
    shapes = list(rules.iter_shapes(slide.shapes))
    slots = rules.describe_slots(slide, slide_w, slide_h, scheme)
    sampler = PictureSampler()
    palette = set()
    if isinstance(background, str) and background.startswith("#"):
        palette.add(background.upper())
    for slot in slots:
        foreground = rules.resolve_color(slot["color"], scheme)
        if foreground:
            palette.add(foreground)
        plate = rules.find_backplate(slot, shapes, slide_area)
        if plate is not None:
            fill = rules.shape_fill(plate)
            if fill["kind"] == "solid":
                color = rules.resolve_color(fill["color"], scheme)
                if color:
                    palette.add(color)
    body = []
    chrome = []
    unmeasured = []
    for slot in slots:
        result = slot_underlay(slot, shapes, slide_area, background, scheme, sampler)
        if result is None:
            unmeasured.append((slot["slot"], "文字色或背景不可解析"))
            continue
        value, foreground, backdrop, lowest, lowest_color = result
        entry = (value, slot["slot"], foreground, backdrop, lowest, lowest_color)
        if slot["chrome"]:
            chrome.append(entry)
        else:
            body.append(entry)
    body.sort(key=lambda item: item[0])
    chrome.sort(key=lambda item: item[0])
    colors = sorted(color for color in palette if color not in NEUTRAL_COLORS)
    details = []
    if body:
        worst = body[0]
        soft = [item for item in body if item[0] < CONTRAST_COMFORT]
        if worst[0] < CONTRAST_MIN:
            details.append(finding(
                "FAIL", "对比度",
                "槽位 %d %s 对 %s 低于正文下限（%d 个正文槽位未达舒适值）"
                % (worst[1], worst[2], worst[3], len(soft)),
                worst[0], CONTRAST_MIN, number))
        elif worst[0] < CONTRAST_COMFORT:
            details.append(finding(
                "WARN", "对比度",
                "槽位 %d %s 对 %s 未达舒适值（%d 个正文槽位未达舒适值）"
                % (worst[1], worst[2], worst[3], len(soft)),
                worst[0], CONTRAST_COMFORT, number))
        else:
            details.append(finding("PASS", "对比度",
                                   "正文槽位 %d 个，最低为槽位 %d" % (len(body), worst[1]),
                                   worst[0], CONTRAST_MIN, number))
    if chrome:
        worst = chrome[0]
        if worst[0] < CHROME_CONTRAST[profile]:
            details.append(finding("WARN", "页眉页脚",
                                   "槽位 %d %s 对 %s 低于辅助信息下限"
                                   % (worst[1], worst[2], worst[3]),
                                   worst[0], CHROME_CONTRAST[profile], number))
        else:
            details.append(finding("PASS", "页眉页脚",
                                   "辅助槽位 %d 个，最低为槽位 %d" % (len(chrome), worst[1]),
                                   worst[0], CHROME_CONTRAST[profile], number))
    if len(colors) > MAX_PAGE_COLORS:
        details.append(finding("WARN", "配色数",
                               "单页 %d 个非黑白颜色：%s" % (len(colors), " ".join(colors)),
                               len(colors), MAX_PAGE_COLORS, number))
    else:
        details.append(finding("PASS", "配色数", "单页 %d 个非黑白颜色" % len(colors),
                               len(colors), MAX_PAGE_COLORS, number))
    if unmeasured:
        reasons = {}
        for slot_number, reason in unmeasured:
            reasons.setdefault(reason, []).append(slot_number)
        parts = []
        for reason, numbers in sorted(reasons.items()):
            parts.append("槽位 %s %s" % ("、".join(str(item) for item in numbers), reason))
        details.append(finding("WARN", "不可测",
                               "%d 个槽位跳过对比度：%s" % (len(unmeasured), "；".join(parts)),
                               len(unmeasured), 0, number))
    levels = [item["level"] for item in details]
    level = "FAIL" if "FAIL" in levels else ("WARN" if "WARN" in levels else "PASS")
    shown = body[0] if body else (chrome[0] if chrome else None)
    if shown is not None and shown[4] + 0.5 < shown[0]:
        details.append(finding("WARN", "最低值",
                               "槽位 %d 的底衬局部像素最低 %.2f（判定值取 10 分位 %.2f）"
                               % (shown[1], shown[4], shown[0]),
                               shown[4], CONTRAST_MIN, number))
    if shown is None:
        summary = (level, number, len(colors), "n/a", "n/a")
    else:
        summary = (level, number, len(colors), "%.2f" % shown[0],
                   "%s/%s" % (shown[2], shown[3]))
    return summary, details


def audit_pptx(path, profile):
    presentation, slide_w, slide_h, scheme = rules.open_presentation(path)
    slide_area = slide_w * slide_h
    summaries = []
    findings = []
    for number, slide in enumerate(presentation.slides, 1):
        summary, details = audit_page(number, slide, presentation, scheme,
                                      slide_w, slide_h, slide_area, profile)
        summaries.append(summary)
        findings.extend(details)
    return len(presentation.slides), summaries, findings


def print_pptx(summaries, findings):
    by_page = {}
    for item in findings:
        by_page.setdefault(item["page"], []).append(item)
    for level, number, count, min_contrast, worst in summaries:
        print("%-4s  page %-3d  colors=%d  min_contrast=%s  worst=%s"
              % (level, number, count, min_contrast, worst))
        for item in by_page.get(number, []):
            print("%-4s  page %-3d  %-6s  %s  实测=%s  阈值=%s"
                  % (item["level"], number, item["rule"], item["detail"],
                     item["actual"], item["limit"]))


def print_colors(findings):
    for item in findings:
        print("%-4s  %-12s  %s  实测=%s  阈值=%s"
              % (item["level"], item["rule"], item["detail"],
                 item["actual"], item["limit"]))


def main():
    parser = argparse.ArgumentParser(description="配色与对比度量化门")
    parser.add_argument("--colors", default="", help="逗号分隔的 #RRGGBB 色板")
    parser.add_argument("--pptx", default="", help="待查的成品 pptx")
    parser.add_argument("--profile", default="presentation", choices=rules.PROFILES)
    parser.add_argument("--json", default="")
    args = parser.parse_args()
    if bool(args.colors) == bool(args.pptx):
        raise SystemExit("--colors 与 --pptx 必须且只能给一个")
    if args.colors:
        colors = parse_colors(args.colors)
        findings = check_palette(colors)
        print("色板 %d 色：%s" % (len(colors), " ".join(colors)))
        print_colors(findings)
        report = {"mode": "colors", "colors": colors, "findings": findings}
    else:
        if not os.path.exists(args.pptx):
            raise SystemExit("文件不存在：%s" % args.pptx)
        pages, summaries, findings = audit_pptx(args.pptx, args.profile)
        print_pptx(summaries, findings)
        report = {"mode": "pptx", "pptx": args.pptx, "profile": args.profile,
                  "pages": pages, "findings": findings}
    fails = [item for item in findings if item["level"] == "FAIL"]
    warns = [item for item in findings if item["level"] == "WARN"]
    passes = [item for item in findings if item["level"] == "PASS"]
    print("gate_palette: FAIL=%d WARN=%d PASS=%d" % (len(fails), len(warns), len(passes)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1)
        print("报告 %s" % args.json)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
