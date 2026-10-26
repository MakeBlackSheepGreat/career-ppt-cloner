"""把风格包里的空壳页面填上我们的内容，输出成品 pptx。

风格包已经把每个文字槽清空，槽位靠 shape_id 定位——shape_id 写在 pptx 的 XML 里，
保存、复制、LibreOffice 往返都不会变。

内容文件形状见 references/CONTENT-SCHEMA.md。最小形式：

    {
      "style": "warm-orange-life",
      "pages": [
        {"page": 1, "map": [{"slot": 1, "text": "标题"}]},
        {"page": 2, "map": [{"slot": 1, "text": ["第一段", "第二段"]}]}
      ]
    }

槽位条目除 slot 与 text 外，还可覆盖字号、字体、颜色、粗细、段距：
    {"slot": 3, "text": ["第一行", "第二行"], "font_size": 22, "color": "#FF8810",
     "bold": true, "font_name": "思源宋体 CN Heavy", "line_spacing": 1.35,
     "space_after": 6, "align": "LEFT"}
"""
import argparse
import copy
import json
import os
import shutil

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Pt

import align
import fit

NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PHOTO_PREFIX = "PHOTO-SLOT"

# 命令行传入的对齐模式，避免层层传参
args_align_mode = ["both"]


def walk(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            for sub in walk(shape.shapes):
                yield sub


def is_group(shape):
    try:
        return shape.shape_type == MSO_SHAPE_TYPE.GROUP
    except Exception:
        return False


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def text_frames_by_shape_id(slide):
    table = {}
    for shape in walk(slide.shapes):
        if shape.has_text_frame:
            table[shape.shape_id] = shape
    return table


def text_frames_by_name(slide):
    table = {}
    for shape in walk(slide.shapes):
        if shape.has_text_frame:
            table[shape.name] = shape
    return table


def set_paragraph_properties(paragraph, style):
    if style.get("align"):
        mapping = {
            "LEFT": 1, "CENTER": 2, "RIGHT": 3, "JUSTIFY": 4,
        }
        name = style["align"].upper()
        if name in mapping:
            from pptx.enum.text import PP_ALIGN
            paragraph.alignment = getattr(PP_ALIGN, name)
    if style.get("line_spacing"):
        paragraph.line_spacing = float(style["line_spacing"])
    if style.get("space_after") is not None:
        paragraph.space_after = Pt(float(style["space_after"]))
    if style.get("space_before") is not None:
        paragraph.space_before = Pt(float(style["space_before"]))
    paragraph.level = int(style.get("level", paragraph.level))


def apply_run_style(run, style):
    font = run.font
    if style.get("font_name"):
        font.name = style["font_name"]
    if style.get("font_size"):
        font.size = Pt(float(style["font_size"]))
    if style.get("bold") is not None:
        font.bold = bool(style["bold"])
    if style.get("italic") is not None:
        font.italic = bool(style["italic"])
    if style.get("underline") is not None:
        font.underline = bool(style["underline"])
    color = style.get("color")
    if color:
        if color.startswith("#"):
            font.color.rgb = RGBColor.from_string(color[1:].upper())
        elif color.startswith("theme:"):
            font.color.theme_color = color[len("theme:"):]


def default_run_style(slide_manifest, slot_manifest):
    """没有显式覆盖时，沿用参考页原来的字体、字号、颜色。"""
    return {
        "font_name": slot_manifest.get("font_name"),
        "font_size": slot_manifest.get("font_size"),
        "bold": slot_manifest.get("bold"),
        "color": slot_manifest.get("color"),
    }


def write_lines(shape, lines, style):
    """按行写进文本框，每一行都完整继承参考页首段的段落属性与 run 属性。"""
    frame = shape.text_frame
    while len(frame.paragraphs) > 1:
        last = frame.paragraphs[-1]
        last._p.getparent().remove(last._p)

    first_paragraph = frame.paragraphs[0]
    template_runs = list(first_paragraph.runs)
    template_rPr = None
    if template_runs:
        rPr = template_runs[0]._r.find(NS_A + "rPr")
        if rPr is not None:
            template_rPr = copy.deepcopy(rPr)

    first_p = first_paragraph._p

    for position, line in enumerate(lines):
        if position == 0:
            paragraph = first_paragraph
        else:
            new_p = copy.deepcopy(first_p)
            first_p.addnext(new_p) if position == 1 else paragraph._p.addnext(new_p)
            paragraph = frame.paragraphs[position]
        set_paragraph_properties(paragraph, style)

        runs = list(paragraph.runs)
        if runs:
            run = runs[0]
            for extra in runs[1:]:
                extra._r.getparent().remove(extra._r)
        else:
            run = paragraph.add_run()
        # 先补回参考页的 run 属性（含主题色、字体、字距），再按覆盖项改写
        if template_rPr is not None:
            existing = run._r.find(NS_A + "rPr")
            if existing is not None:
                run._r.remove(existing)
            run._r.insert(0, copy.deepcopy(template_rPr))
        run.text = line
        apply_run_style(run, style)

    return shape


def photo_frames_by_name(slide):
    table = {}
    for shape in walk(slide.shapes):
        if shape.name.startswith(PHOTO_PREFIX):
            table[shape.name[len(PHOTO_PREFIX):].strip()] = shape
        else:
            table[shape.name] = shape
    return table


def replace_with_picture(slide, frame, image_path):
    """把占位框换成真实照片，位置尺寸角度全部沿用占位框。"""
    if not os.path.exists(image_path):
        raise SystemExit("照片不存在：%s" % image_path)
    parent = frame._element.getparent()
    order = parent.index(frame._element)
    left, top, width, height = frame.left, frame.top, frame.width, frame.height
    rotation = frame.rotation
    picture = slide.shapes.add_picture(image_path, left, top, width, height)
    picture.rotation = rotation
    picture.name = frame.name
    parent.remove(frame._element)
    parent.insert(order, picture._element)
    return picture


def crop_picture_to_frame(picture, frame_width, frame_height):
    """按占位框比例裁切，避免照片被拉伸变形。"""
    try:
        image_w, image_h = picture.image.size
    except Exception:
        return
    if not image_w or not image_h:
        return
    frame_ratio = frame_width / float(frame_height)
    image_ratio = image_w / float(image_h)
    if image_ratio > frame_ratio:
        excess = 1.0 - frame_ratio / image_ratio
        picture.crop_left = excess / 2.0
        picture.crop_right = excess / 2.0
    elif image_ratio < frame_ratio:
        excess = 1.0 - image_ratio / frame_ratio
        picture.crop_top = excess / 2.0
        picture.crop_bottom = excess / 2.0


def fill_photo(slide, entry, photos):
    target = str(entry.get("target", entry.get("photo_slot", "")))
    if not target:
        raise SystemExit("照片条目的 target 或 photo_slot 不能为空")
    frame = photos.get(target)
    if frame is None:
        raise SystemExit("本页没有编号为 %r 的照片槽，可选：%s"
                         % (target, "、".join(sorted(photos)) or "无"))
    picture = replace_with_picture(slide, frame, entry["photo"])
    if entry.get("crop", True):
        crop_picture_to_frame(picture, frame.width, frame.height)
    return picture


def fill_slide(slide, entries, page_manifest, slide_manifest_lookup, reports, alignment_reports):
    frames = text_frames_by_shape_id(slide)
    by_name = text_frames_by_name(slide)
    photos = photo_frames_by_name(slide)
    filled = 0
    for entry in entries:
        if entry.get("photo"):
            fill_photo(slide, entry, photos)
            filled += 1
            continue
        number = entry.get("slot")
        if number is None:
            continue
        slot_manifest = slide_manifest_lookup.get(number)
        if slot_manifest is None:
            raise SystemExit("槽位 %d 在 slots.json 里不存在" % number)
        if slot_manifest.get("lookup_by_name"):
            shape = by_name.get(slot_manifest.get("name"))
        else:
            shape = frames.get(slot_manifest["shape_id"])
        if shape is None:
            raise SystemExit("槽位 %d 在页面里找不到（slots.json 与 pack.pptx 不一致，名字 %r）"
                             % (number, slot_manifest.get("name")))
        text = entry.get("text")
        if text is None:
            text = slot_manifest.get("resize")
        if text is None:
            continue
        if isinstance(text, list):
            lines = [str(line) for line in text]
        else:
            lines = str(text).split(chr(10))
        style = default_run_style(page_manifest, slot_manifest)
        for key in ("font_name", "font_size", "bold", "italic", "underline", "color",
                    "align", "line_spacing", "space_after", "space_before", "level",
                    "autofit"):
            if key in entry:
                style[key] = entry[key]

        align_mode = entry.get("align_center", args_align_mode[0])
        align.align_slot(shape, slot_manifest, align_mode)
        if slot_manifest.get("centroid"):
            check = align.check_centering(shape, slot_manifest["centroid"])
            if check is not None:
                alignment_reports.append({
                    "page": None, "slot": number,
                    "dx_cm": check["dx_cm"], "dy_cm": check["dy_cm"],
                    "centered": check["centered"],
                })

        autofit = style.pop("autofit", True)
        requested = style.get("font_size") or 18.0
        line_spacing = style.get("line_spacing")
        pending_space = style.get("space_after") or 0.0
        diagnosis = fit.analyse(slot_manifest, lines, requested, line_spacing, pending_space)
        reports.append(diagnosis)
        final_lines = diagnosis["lines"]
        if autofit:
            style["font_size"] = diagnosis["fitted_pt"]
        write_lines(shape, final_lines, style)
        filled += 1
    return filled


def expand_entries(page_entry, lookup, fill_order):
    """支持简短写法 {"slots": [...]}：按 catalog 给出的填写顺序依次填。

    参考件的槽位编号是绘制顺序，跟写内容的顺序对不上，所以用 fill_order 重排。
    要精确指定某个槽位时用 {"map": [{"slot": 3, "text": "..."}]}。
    """
    if "map" in page_entry:
        return list(page_entry["map"])
    raw = page_entry.get("slots")
    if raw is None:
        return []
    order = list(fill_order or [])
    result = []
    for offset, item in enumerate(raw):
        if item is None:
            continue
        if isinstance(item, dict) and "slot" in item:
            result.append(dict(item))
            continue
        if offset >= len(order):
            raise SystemExit("内容给多了：本页只有 %d 个可填槽位，第 %d 项没有位置"
                             % (len(order), offset + 1))
        slot_number = order[offset]
        if isinstance(item, dict):
            entry = dict(item)
            entry["slot"] = slot_number
        else:
            entry = {"slot": slot_number, "text": item}
        result.append(entry)
    return result


def resolve_keep(spec, content, presentation):
    """决定成品保留哪些页。None 表示全部保留。"""
    if spec == "all":
        return None
    if spec == "auto":
        return {entry["page"] for entry in content.get("pages", [])}
    keep = set()
    total = len(presentation.slides)
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            low, high = token.split("-")
            keep.update(range(int(low), int(high) + 1))
        else:
            keep.add(int(token))
    return {page for page in keep if 1 <= page <= total}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True, help="风格包目录")
    parser.add_argument("--content", required=True, help="内容 JSON")
    parser.add_argument("--out", required=True, help="输出 pptx")
    parser.add_argument("--pages", default="auto",
                        help="auto 只保留填过内容的页；也可写 1,3,5；all 保留全部")
    parser.add_argument("--align-center", default="both",
                        choices=("both", "vertical", "horizontal", "off"),
                        help="文字与底衬框的对齐方式，默认上下左右都居中")
    args = parser.parse_args()

    slots_path = os.path.join(args.style, "slots.json")
    pack_path = os.path.join(args.style, "pack.pptx")
    for path in (slots_path, pack_path):
        if not os.path.exists(path):
            raise SystemExit("风格包缺少文件：%s" % path)

    manifest = load_json(slots_path)
    content = load_json(args.content)

    working = args.out + ".working.pptx"
    shutil.copyfile(pack_path, working)
    presentation = Presentation(working)

    manifest_by_page = {page["page"]: page for page in manifest["pages"]}
    defaults = content.get("defaults", {})

    total = 0
    reports = []
    alignment_reports = []
    args_align_mode[0] = args.align_center
    for page_entry in content.get("pages", []):
        number = page_entry["page"]
        if number not in manifest_by_page:
            raise SystemExit("内容里引用了风格包没有的页 %d" % number)
        page_manifest = manifest_by_page[number]
        lookup = {slot["slot"]: slot for slot in page_manifest["slots"]}
        slide = presentation.slides[number - 1]
        entries = list(defaults.get("all", []))
        entries += page_manifest.get("preset", [])
        entries += expand_entries(page_entry, lookup, page_manifest.get("fill_order"))
        before = len(reports)
        before_align = len(alignment_reports)
        total += fill_slide(slide, entries, page_manifest, lookup, reports, alignment_reports)
        for record in reports[before:]:
            record["page"] = number
        for record in alignment_reports[before_align:]:
            record["page"] = number

    keep = resolve_keep(args.pages, content, presentation)
    if keep is not None:
        slide_ids = presentation.slides._sldIdLst
        for index, slide_id in enumerate(list(slide_ids), 1):
            if index in keep:
                continue
            rel_id = slide_id.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            presentation.part.drop_rel(rel_id)
            slide_ids.remove(slide_id)

    kept = len(presentation.slides)
    presentation.save(args.out)
    os.remove(working)

    report_path = os.path.splitext(args.out)[0] + ".fitreport.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=1)

    align_report_path = os.path.splitext(args.out)[0] + ".alignreport.json"
    with open(align_report_path, "w", encoding="utf-8") as handle:
        json.dump(alignment_reports, handle, ensure_ascii=False, indent=1)

    off_centre = [item for item in alignment_reports if not item["centered"]]
    print("与底衬框对齐的槽位 %d 个，偏差超限 %d 个，明细见 %s"
          % (len(alignment_reports), len(off_centre), os.path.basename(align_report_path)))
    for item in off_centre:
        print("  页 %-3s 槽 %-3s 偏差 dx=%.3fcm dy=%.3fcm"
              % (item["page"], item["slot"], item["dx_cm"], item["dy_cm"]))

    cramped = [item for item in reports if item["shrunk"]]
    overwide = [item for item in reports if not item["width_ok"]]
    print("saved %s (%d slots filled, %d pages)" % (args.out, total, kept))
    print("字号被压缩的槽位 %d 个，宽度仍超出的槽位 %d 个，明细见 %s"
          % (len(cramped), len(overwide), os.path.basename(report_path)))
    for item in cramped:
        print("  页 %-3s 槽 %-3s 需求 %.1fpt -> 实用 %.1fpt（框宽 %.2fcm，需要 %.2fcm）"
              % (item["page"], item["slot"], item["requested_pt"], item["fitted_pt"],
                 item["box_width_cm"], item["need_width_cm"]))


if __name__ == "__main__":
    main()
