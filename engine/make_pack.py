"""把参考演示文稿的“血肉”抽掉、只留下骨架与皮肤，做成可复用的风格包。

用法：
    python make_pack.py --src 参考.pptx --outdir styles/pack-xxx --name 橙暖生活

产物：
    pack.pptx   文字已清空的整套页面（背景、装饰、图形、图表、照片位置全部保留）
    slots.json  每页每个文字槽的几何、段落数、字符数、字距参数与角色

清空文字的做法是：每个段落只留一个 run，把 run 的文本设为空字符串。这样字体、
字号、颜色、字距（spc）、行距全部保留，合成时只需要往这个 run 里写新内容。
"""
import argparse
import io
import json
import math
import os
import zipfile
from collections import OrderedDict

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt


def cm(value):
    if value is None:
        return None
    return round(Emu(int(value)).cm, 2)


def color_of(font):
    try:
        color = font.color
        if color is None or color.type is None:
            return None
        kind = str(color.type)
        if "RGB" in kind:
            return "#" + str(color.rgb)
        if "THEME" in kind:
            return "theme:" + str(color.theme_color)
    except Exception:
        return None
    return None


def iter_shapes(shapes, depth=0):
    for shape in shapes:
        yield shape, depth
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            for sub, sub_depth in iter_shapes(shape.shapes, depth + 1):
                yield sub, sub_depth


def first_run(text_frame):
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            if run.text.strip():
                return run
    return None


def slot_role(text, width, height, slide_w, slide_h, font_size, char_count):
    """由几何与字体推断槽位角色，合成时按角色挑选内容。"""
    if char_count <= 1:
        return "glyph"
    if width and height and width >= slide_w * 0.88 and height >= slide_h * 0.55:
        return "backdrop_note"
    if font_size and font_size >= 44:
        return "display"
    if font_size and font_size >= 30:
        return "headline"
    if font_size and font_size >= 22:
        return "title"
    if char_count <= 8 and (font_size or 0) >= 18:
        return "label"
    if char_count >= 55:
        return "body"
    return "text"


A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# 这些槽的字号本身就是设计语言的一部分，缩小就变味了，所以参考页的原文会被保留，
# 生成时用同样的字数去替换，视觉密度与参考页一致。
RESIZE_ROLES = ("display", "headline", "glyph")
RESIZE_MIN_CHARS = 12


def keeps_size(text, role):
    return role in RESIZE_ROLES and len(text) >= RESIZE_MIN_CHARS


def frame_metrics(text_frame):
    """读出文本框自身的内边距与首段行距，测量文字用。"""
    body = text_frame._txBody.find(A_NS + "bodyPr")
    metrics = {"l_ins": 0.254, "r_ins": 0.254, "t_ins": 0.127, "b_ins": 0.127}
    if body is not None:
        for key, attribute in (("l_ins", "lIns"), ("r_ins", "rIns"),
                               ("t_ins", "tIns"), ("b_ins", "bIns")):
            raw = body.get(attribute)
            if raw is not None:
                metrics[key] = round(Emu(int(raw)).cm, 3)
    line_spacing = None
    paragraph = text_frame.paragraphs[0] if text_frame.paragraphs else None
    if paragraph is not None:
        ppr = paragraph._p.find(A_NS + "pPr")
        if ppr is not None:
            spacing = ppr.find(A_NS + "lnSpc")
            if spacing is not None:
                for child in spacing:
                    tag = etree.QName(child).localname
                    if tag == "spcPct":
                        line_spacing = round(int(child.get("val")) / 100000.0, 3)
                    elif tag == "spcPts":
                        line_spacing = round(int(child.get("val")) / 100.0, 2)
    metrics["line_spacing"] = line_spacing
    return metrics


def find_backplate(shape, slide_shapes, slide_area):
    """找出承载这段文字的可视底衬框。

    参考件里很多文字贴在色块、胶囊条、圆角矩形上，文字框与色块是分别摆的两个形状，
    位置常差一两毫米。复刻时文字必须重新对准色块中心，所以先把底衬找出来。

    判据：底衬是形状（非图片、非文本框），能完整包住文字框，尺寸不夸张地大。整页底图
    与满版色块不算——那些是背景，文字本来就该按参考位置摆。
    """
    subject = (shape.left, shape.top, shape.width, shape.height)
    if None in subject:
        return None
    # 统一换成厘米，与 slide_area 同量纲
    sx, sy, sw, sh = (cm(value) for value in subject)
    if sw <= 0 or sh <= 0:
        return None
    best = None
    best_score = -1e18
    for other in slide_shapes:
        if other is shape:
            continue
        if other.shape_type == MSO_SHAPE_TYPE.PICTURE:
            continue
        if other.has_text_frame and other.text_frame.text.strip():
            continue
        if None in (other.left, other.top, other.width, other.height):
            continue
        ox, oy, ow, oh = (cm(other.left), cm(other.top), cm(other.width), cm(other.height))
        if ow <= 0 or oh <= 0:
            continue
        # 满版背景不算底衬
        if ow * oh >= slide_area * 0.62:
            continue
        scx = sx + sw / 2.0
        scy = sy + sh / 2.0
        if not (ox <= scx <= ox + ow and oy <= scy <= oy + oh):
            continue
        # 文字框要被底衬覆盖住九成以上，否则是旁边的大色块
        overlap_w = max(0.0, min(ox + ow, sx + sw) - max(ox, sx))
        overlap_h = max(0.0, min(oy + oh, sy + sh) - max(oy, sy))
        coverage = min(1.0, (overlap_w * overlap_h) / float(sw * sh))
        if coverage < 0.90:
            continue
        # 底衬面积不应超过文字框的若干倍，否则是装饰大色块不是文字底衬
        size_ratio = (ow * oh) / float(sw * sh)
        if size_ratio > 9.0 or size_ratio < 0.95:
            continue
        # 越贴合文字框、中心越接近，越可能是专属底衬
        centre_offset = (abs((ox + ow / 2.0) - scx) / float(sw)
                         + abs((oy + oh / 2.0) - scy) / float(sh))
        score = coverage * 2.0 - abs(math.log(size_ratio)) - centre_offset
        if score > best_score:
            best_score = score
            best = other
    if best is None:
        return None
    return {
        "left": best.left,
        "top": best.top,
        "width": best.width,
        "height": best.height,
        "center_x": best.left + best.width / 2.0,
        "center_y": best.top + best.height / 2.0,
    }


def describe_slots(slide, slide_w, slide_h):
    slots = []
    all_shapes = list(slide.shapes)
    for shape, _depth in iter_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text.strip()
        if not text:
            continue
        donor = first_run(shape.text_frame)
        font_size = donor.font.size.pt if donor is not None and donor.font.size else None
        font_name = donor.font.name if donor is not None else None
        bold = bool(donor.font.bold) if donor is not None else None
        color = color_of(donor.font) if donor is not None else None
        width, height = cm(shape.width), cm(shape.height)
        paragraphs = shape.text_frame.paragraphs
        alignment = None
        if paragraphs and paragraphs[0].alignment is not None:
            alignment = str(paragraphs[0].alignment).split(".")[-1].split(" ")[0]
        anchor = None
        try:
            if shape.text_frame.vertical_anchor is not None:
                anchor = str(shape.text_frame.vertical_anchor).split(".")[-1].split(" ")[0]
        except Exception:
            anchor = None
        metrics = frame_metrics(shape.text_frame)
        role = slot_role(text, width, height, slide_w, slide_h, font_size, len(text))
        backplate = None
        centroid = None
        if role in ("label", "title", "headline", "text", "body", "display"):
            backplate = find_backplate(shape, all_shapes, slide_w * slide_h)
            if backplate is not None:
                centroid = [backplate["center_x"], backplate["center_y"]]
            else:
                if None not in (shape.left, shape.top, shape.width, shape.height):
                    centroid = [shape.left + shape.width / 2.0,
                                shape.top + shape.height / 2.0]
        slots.append(OrderedDict([
            ("slot", len(slots) + 1),
            ("shape_id", shape.shape_id),
            ("name", shape.name),
            ("role", role),
            ("insets", [metrics["l_ins"], metrics["r_ins"], metrics["t_ins"], metrics["b_ins"]]),
            ("line_spacing", metrics["line_spacing"]),
            ("left", cm(shape.left)),
            ("top", cm(shape.top)),
            ("width", width),
            ("height", height),
            ("paragraphs", len(paragraphs)),
            ("chars", len(text)),
            ("per_paragraph", max(1, round(len(text) / max(1, len(paragraphs))))),
            ("font_name", font_name),
            ("font_size", font_size),
            ("bold", bold),
            ("color", color),
            ("align", alignment),
            ("anchor", anchor),
            ("backplate", backplate),
            ("centroid", centroid),
            ("sample", text[:100]),
            ("resize", text if keeps_size(text, role) else None),
        ]))
    return slots


# 这些词说明这页是为原作者某段特定内容画的，换个赛道就装不下别人的内容
SPECIFIC_MARKERS = (
    "目录", "测评", "霍兰德", "MBTI", "生涯", "职业规划", "求职",
    "大学", "学院", "专业", "绩点", "姓名", "团员", "党员",
    "干练", "特长", "爱好", "性格",
)

# 校名与校情介绍一旦出现，这页就是为原作者的学校画的，换学校必错
SCHOOL_MARKERS = (
    "西南科技大学", "科技大学", "科技城", "绵阳",
    "省部共建", "国家国防", "重点学科", "一级学科", "博士学位授权",
)


def describe_page_specificity(slots, pictures):
    """判断这页的版面有多「专属」。

    generic 版面（色块、分区、箭头、时间轴）能装任意内容；
    specific 版面的形状与文字位置是为原作者某段话画的（目录、测评图、校门合影），
    换个人用就会别扭。生成大纲时优先选 generic 页。
    """
    text = " ".join((slot.get("sample") or "") for slot in slots)
    # 提到校名与校情的页一律算专属，不给别人用
    if any(marker in text for marker in SCHOOL_MARKERS):
        return "specific"
    hits = sum(1 for marker in SPECIFIC_MARKERS if marker in text)
    # 整幅背景图通常是校门、校园、主题主视觉，也偏专属
    full_bleed = any(item["role"] == "background" for item in pictures)
    if hits >= 3 or (full_bleed and hits >= 2):
        return "specific"

    # 大面积图片配上极少文字槽，说明这页是围绕那张图设计的（校情介绍、荣誉墙、
    # 产品图墙）。图里往往已经把原作者的文案印在像素里，换人用一定别扭。
    big_pictures = [item for item in pictures
                    if item["role"] != "background"]
    large_area = 0.0
    for item in big_pictures:
        large_area += (item["width"] or 0) * (item["height"] or 0)
    if large_area and len([s for s in slots if s["chars"] > 0]) <= 3:
        return "specific"

    if hits >= 1 or full_bleed:
        return "mixed"
    return "generic"


def describe_page_kind(slots, pictures, slide_w, slide_h):
    """从槽位与图片来源推断这页承担什么职责，供生成器选页。"""
    roles = [slot["role"] for slot in slots]
    backgrounds = [item for item in pictures if item["role"] == "background"]
    if "display" in roles or "glyph" in roles:
        return "section"
    if backgrounds:
        return "cover" if len(slots) <= 6 else "photo"
    texts = [slot for slot in slots if slot["role"] in ("title", "headline", "label")]
    bodies = [slot for slot in slots if slot["role"] in ("body", "text", "backdrop_note")]
    if len(texts) >= 6 and len(bodies) <= 2:
        return "grid"
    if not slots:
        return "photo"
    return "text"


# 简写填写时的推荐顺序：先页面标题，再页眉导航，再正文，最后短标签。
# 参考件的槽位编号是绘制顺序，跟人写内容的顺序对不上，所以单独给一份顺序。
FILL_ORDER = {
    "headline": 0,
    "title": 1,
    "display": 2,
    "body": 3,
    "backdrop_note": 3,
    "text": 4,
    "label": 5,
    "glyph": 9,
}


def compute_fill_order(slots, chrome):
    """算出这页按什么顺序填内容，返回槽位号列表。"""
    candidates = [slot for slot in slots if slot["role"] != "glyph"]
    header = set(chrome)

    def band(slot):
        # 页眉带是版式签名，永远排最后，避免误填内容
        return 1 if slot["slot"] in header else 0

    def sort_key(slot):
        # 先按位置从上到下、从左到右，再看角色权重：
        # 读者看一页的顺序就是标题在上、正文在中、落款在下。
        role_weight = FILL_ORDER.get(slot["role"], 6)
        heading = role_weight <= 1
        return (band(slot), 0 if heading else 1,
                slot["top"] or 0, role_weight, slot["left"] or 0)

    return [slot["slot"] for slot in sorted(candidates, key=sort_key)]


def describe_chrome(slots):
    """页眉带上那些反复出现的小标签，是版式的签名，不是内容。"""
    chrome = []
    for slot in slots:
        # 页眉带里的字都不会是页面主标题
        if slot["role"] not in ("text", "label"):
            continue
        top = slot["top"] or 0
        if top >= 3.2:
            continue
        if slot["chars"] > 14:
            continue
        chrome.append(slot["slot"])
    return chrome


def classify_picture(shape, width, height, slide_w, slide_h):
    """把图片分成四类：整幅背景、装饰、照片槽、正片内容。

    区分照片槽与正片内容靠看图片本身：照片通常满幅、色彩丰富；截图与证书大面积是
    白底或纯色底。判错代价不对称——把别人的证书当成装饰留在成品里，等于抄进了别人
    的材料，所以宁可多判成正片内容。
    """
    if not width or not height:
        return "decoration"
    if width >= slide_w * 0.88 and height >= slide_h * 0.8:
        return "background"

    area_ratio = (width * height) / (slide_w * slide_h)
    if area_ratio < 0.02:
        return "decoration"

    blob = picture_blob(shape)
    if blob is None:
        # 矢量图标与读不出像素的图，尺寸够大就按正片内容处理，宁可多删
        return "content"
    stats = image_stats(blob)
    if stats is None:
        return "content"
    mean, white_ratio, saturation, alpha_ratio = stats
    # 带大量透明像素的是贴上去的图形素材（问号、箭头、书法字），不是照片
    if alpha_ratio is not None and alpha_ratio > 0.05:
        return "decoration"

    # 大面积白底或纯色底，基本是截图、证书、表格
    if white_ratio >= 0.35 or saturation < 0.10:
        return "content"
    if mean > 235:
        return "content"

    aspect = width / height
    if 0.35 <= aspect <= 2.6:
        return "photo"
    return "decoration"


def is_title_lettering(item, slide_w, slide_h):
    """封面那行书法大字常是导出的透明 PNG，不是照片也不是普通装饰。

    判据：位置在上半版、横向铺得够宽、高度像一行字。这类图换成同位置的可填标题文字，
    保留参考页的字号气势，使用者填自己的主标题。
    """
    if item["role"] == "background":
        return False
    height = item["height"] or 0
    top = item["top"] or 0
    width = item["width"] or 0
    if top > slide_h * 0.55:
        return False
    if width < slide_w * 0.35:
        return False
    # 一行到三行字的高度范围
    if height < slide_h * 0.05 or height > slide_h * 0.60:
        return False
    return True


def picture_blob(shape):
    """取图片原始字节。SVG 之类的图片读不到 .image，直接从包里按关系号取。"""
    try:
        return shape.image.blob
    except Exception:
        pass
    try:
        blip = shape._element.find(".//" + A_NS + "blip")
        if blip is None:
            return None
        rel_id = blip.get(R_NS + "embed")
        if not rel_id:
            return None
        part = shape.part.related_part(rel_id)
        return part.blob
    except Exception:
        return None


def picture_pixels(shape):
    """返回 宽x高 描述；取不到时返回 None。"""
    blob = picture_blob(shape)
    if blob is None:
        return None
    try:
        image = Image.open(io.BytesIO(blob))
        return image.size
    except Exception:
        return None


def _pixels(image):
    """把缩略图取成一个 RGB 三元组列表，避开已废弃的 getdata。"""
    raw = image.tobytes()
    return [tuple(raw[index:index + 3]) for index in range(0, len(raw), 3)]


def image_stats(blob):
    """缩略取样，返回平均亮度、近白像素占比、平均饱和度（0 到 1）。"""
    alpha_ratio = None
    try:
        image = Image.open(io.BytesIO(blob))
        image.load()
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            alpha = image.convert("RGBA")
            alpha.thumbnail((96, 96))
            raw_alpha = alpha.tobytes()
            transparent = sum(
                1 for index in range(3, len(raw_alpha), 4) if raw_alpha[index] < 32)
            alpha_ratio = transparent / float(len(raw_alpha) / 4.0)
        image = image.convert("RGB")
        image.thumbnail((96, 96))
        pixels = _pixels(image)
    except Exception:
        return None
    count = float(len(pixels))
    total = 0
    white = 0
    saturation_total = 0.0
    for red, green, blue in pixels:
        total += (red + green + blue) / 3.0
        if red > 238 and green > 238 and blue > 238:
            white += 1
        high = max(red, green, blue)
        low = min(red, green, blue)
        saturation_total += 0.0 if high == 0 else (high - low) / float(high)
    return total / count, white / count, saturation_total / count, alpha_ratio


def describe_pictures(slide, slide_w, slide_h):
    pictures = []
    for shape, _depth in iter_shapes(slide.shapes):
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            continue
        width, height = cm(shape.width), cm(shape.height)
        pictures.append(OrderedDict([
            ("name", shape.name),
            ("shape_id", shape.shape_id),
            ("left", cm(shape.left)),
            ("top", cm(shape.top)),
            ("width", width),
            ("height", height),
            ("role", classify_picture(shape, width, height, slide_w, slide_h)),
            ("px", picture_pixels(shape)),
        ]))
    return pictures


def clear_text(presentation, preserve_ids=()):
    """每个段落只保留一个 run，并把它的文本设为空。

    preserve_ids 里的形状原样保留——装饰性的大数字、编号、书法字是版式的一部分，
    清掉就少一块视觉重量。
    """
    for slide in presentation.slides:
        for shape, _depth in iter_shapes(slide.shapes):
            if not shape.has_text_frame:
                continue
            if shape.shape_id in preserve_ids:
                continue
            frame = shape.text_frame
            if not frame.text.strip():
                continue
            for index, paragraph in enumerate(list(frame.paragraphs)):
                if index > 0:
                    paragraph._p.getparent().remove(paragraph._p)
                    continue
                runs = list(paragraph.runs)
                for run in runs[1:]:
                    run._r.getparent().remove(run._r)
                if runs:
                    runs[0].text = ""
                else:
                    paragraph.add_run().text = ""


def strip_content_pictures(presentation, content_ids):
    """删掉正片图片：证书、别人的图表，一律不带走。"""
    removed = 0
    for index, slide in enumerate(presentation.slides, 1):
        for shape, _depth in list(iter_shapes(slide.shapes)):
            if (index, shape.shape_id) not in content_ids:
                continue
            if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
                continue
            shape._element.getparent().remove(shape._element)
            removed += 1
    print("移除正片图片 %d 张" % removed)


def register_title_slots(pages):
    """把书法标题框登记成可填的文字槽，填内容时按普通槽位写。"""
    added = 0
    for page in pages:
        for item in page["title_slots"]:
            # 标题框与文字槽一样按顺序编号，接在已有槽位之后
            number = len(page["slots"]) + 1
            page["slots"].append(OrderedDict([
                ("slot", number),
                ("shape_id", item["title_slot"]),
                ("name", "TITLE-SLOT p%d-%d" % (page["page"], item["title_slot"])),
                ("lookup_by_name", True),
                ("role", "headline"),
                ("insets", [0.254, 0.254, 0.127, 0.127]),
                ("line_spacing", None),
                ("left", item["left"]),
                ("top", item["top"]),
                ("width", item["width"]),
                ("height", item["height"]),
                ("paragraphs", 1),
                ("chars", 0),
                ("per_paragraph", 0),
                ("font_name", None),
                ("font_size", 44.0),
                ("bold", True),
                ("color", "#FFFFFF"),
                ("align", "CENTER"),
                ("anchor", "MIDDLE"),
                ("backplate", None),
                ("centroid", None),
                ("sample", "封面书法大标题"),
                ("resize", None),
                ("expect_text", True),
            ]))
            added += 1
    if added:
        print("登记可填封面标题槽 %d 个" % added)


def replace_with_title_text(presentation, targets):
    """把书法标题图换成同位置同尺寸的文本框，字号按高度反推，供使用者填主标题。"""
    replaced = 0
    for index, slide in enumerate(presentation.slides, 1):
        collected = []
        for shape, _depth in iter_shapes(slide.shapes):
            if (index, shape.shape_id) not in targets:
                continue
            if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
                continue
            collected.append(shape)
        for shape in collected:
            parent = shape._element.getparent()
            order = parent.index(shape._element)
            height_cm = Emu(int(shape.height)).cm
            left, top = shape.left, shape.top
            width, height = shape.width, shape.height
            # 一行字的高度约为字号的 1.25 倍
            font_pt = max(12.0, round(min(height_cm / 1.25 * 28.35, 96.0), 1))
            box = slide.shapes.add_textbox(left, top, width, height)
            box.name = "TITLE-SLOT p%d-%d" % (index, shape.shape_id)
            box_element = box._element
            # 新建的文本框挂在 slide 的 spTree 下，先摘下来再插到原图的位置
            box_element.getparent().remove(box_element)
            box.text_frame.word_wrap = True
            frame = box.text_frame
            frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            paragraph = frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.CENTER
            run = paragraph.add_run()
            run.text = ""
            run.font.size = Pt(font_pt)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            parent.remove(shape._element)
            parent.insert(order, box_element)
            replaced += 1
    print("封面书法标题换成可填标题框 %d 个" % replaced)


def replace_with_placeholder(presentation, targets):
    """把指定图片换成同位置同尺寸的相框占位块。

    相框保留原来的位置、尺寸、旋转角度与圆角裁剪，使用者把自己的照片按编号填进去，
    照片页的版面重量与参考页完全一致。
    """
    replaced = 0
    for index, slide in enumerate(presentation.slides, 1):
        collected = []
        for shape, _depth in list(iter_shapes(slide.shapes)):
            if (index, shape.shape_id) not in targets:
                continue
            if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
                continue
            collected.append(shape)
        for shape in collected:
            parent = shape._element.getparent()
            order = parent.index(shape._element)
            rotation = shape.rotation
            placeholder = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, shape.left, shape.top, shape.width, shape.height)
            placeholder.name = "PHOTO-SLOT %d" % shape.shape_id
            placeholder.rotation = rotation
            placeholder.fill.solid()
            placeholder.fill.fore_color.rgb = RGBColor(0xEC, 0xEC, 0xEC)
            placeholder.line.color.rgb = RGBColor(0xBF, 0xBF, 0xBF)
            placeholder.line.width = Emu(9525)
            parent.remove(shape._element)
            parent.insert(order, placeholder._element)
            replaced += 1
    print("照片换成可填占位框 %d 张" % replaced)


def drop_unselected(presentation, keep):
    slide_ids = presentation.slides._sldIdLst
    for index, slide_id in enumerate(list(slide_ids), 1):
        if index in keep:
            continue
        rel_id = slide_id.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        presentation.part.drop_rel(rel_id)
        slide_ids.remove(slide_id)


def strip_embedded_fonts(path):
    """去掉内嵌字体。内嵌字体动辄几十兆，一个风格包塞不下；字体名仍写在 meta 里，
    机器上装了对应字体就照常显示，没装则回落到系统字体。"""
    temp = path + ".tmp"
    removed = 0
    total = 0
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as target:
        keep_names = [item.filename for item in source.infolist()]
        for item in source.infolist():
            if item.filename.startswith("ppt/fonts/") or item.filename == "docProps/thumbnail.jpeg":
                removed += 1
                total += item.file_size
                continue
            data = source.read(item.filename)
            if item.filename == "ppt/presentation.xml":
                data = strip_font_list(data)
            elif item.filename.endswith(".rels"):
                data = strip_font_rels(data)
            target.writestr(item, data)
    os.replace(temp, path)
    if removed:
        print("去掉内嵌字体与缩略图 %d 个（%.1f MB）" % (removed, total / 1e6))


def strip_font_list(xml_bytes):
    root = etree.fromstring(xml_bytes)
    for tag in ("embeddedFontLst",):
        node = root.find(qn(tag)) if False else root.find("{http://schemas.openxmlformats.org/presentationml/2006/main}" + tag)
        if node is not None:
            root.remove(node)
    for key in ("embedTrueTypeFonts", "saveSubsetFonts"):
        if key in root.attrib:
            del root.attrib[key]
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def strip_font_rels(xml_bytes):
    text = xml_bytes.decode("utf-8")
    if "/font" not in text:
        return xml_bytes
    root = etree.fromstring(xml_bytes)
    for rel in list(root):
        if rel.get("Type", "").endswith("/font"):
            root.remove(rel)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def shrink_media(path, max_side, jpeg_quality):
    """把媒体缩到 max_side 以内，逐字节比较，只在新文件更小时替换。"""
    temp = path + ".tmp"
    before = after = 0
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.startswith("ppt/media/") and item.filename.lower().endswith(
                    (".png", ".jpg", ".jpeg")):
                before += len(data)
                try:
                    image = Image.open(io.BytesIO(data))
                    image.load()
                    longest = max(image.size)
                    if longest > max_side:
                        scale = max_side / float(longest)
                        image = image.resize(
                            (max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale))),
                            Image.LANCZOS)
                    buffer = io.BytesIO()
                    if item.filename.lower().endswith(".png"):
                        image.save(buffer, format="PNG", optimize=True)
                    else:
                        if image.mode in ("RGBA", "P", "LA"):
                            image = image.convert("RGB")
                        image.save(buffer, format="JPEG", quality=jpeg_quality,
                                   optimize=True, progressive=True)
                    candidate = buffer.getvalue()
                    if len(candidate) < len(data):
                        data = candidate
                except Exception as error:
                    print("  skip media %s (%r)" % (item.filename, error))
                after += len(data)
            target.writestr(item, data)
    os.replace(temp, path)
    print("media %.1f MB -> %.1f MB" % (before / 1e6, after / 1e6))


def parse_pages(spec, total):
    if not spec:
        return set(range(1, total + 1))
    keep = set()
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
    parser.add_argument("--src", required=True, help="参考 pptx 路径")
    parser.add_argument("--outdir", required=True, help="风格包输出目录")
    parser.add_argument("--pages", default="", help="保留的页码，例如 1-10,12,15")
    parser.add_argument("--max-px", type=int, default=2000, help="媒体长边像素上限")
    parser.add_argument("--jpeg-quality", type=int, default=82)
    parser.add_argument("--keep-fonts", action="store_true",
                        help="保留内嵌字体（会让风格包涨到几十兆，默认去掉）")
    parser.add_argument("--content-policy", default="strip",
                        choices=("strip", "blank", "keep"),
                        help="strip 删掉别人的证书图表照片；blank 换成灰色占位块；keep 原样保留")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    presentation = Presentation(args.src)
    slide_w, slide_h = cm(presentation.slide_width), cm(presentation.slide_height)
    total = len(presentation.slides)
    keep = parse_pages(args.pages, total)
    # 形状编号只在单页内唯一，跨页比较必须带上页码
    content_ids = {}
    photo_ids = {}
    title_ids = {}
    for index, slide in enumerate(presentation.slides, 1):
        for item in describe_pictures(slide, slide_w, slide_h):
            key = (index, item["shape_id"])
            if is_title_lettering(item, slide_w, slide_h):
                title_ids[key] = item
            elif item["role"] == "content":
                content_ids[key] = item
            elif item["role"] == "photo":
                photo_ids[key] = item

    pages = []
    for index, slide in enumerate(presentation.slides, 1):
        if index not in keep:
            continue
        slots = describe_slots(slide, slide_w, slide_h)
        pictures = describe_pictures(slide, slide_w, slide_h)
        photo_items = [item for item in pictures if item["role"] == "photo"]
        title_items = [item for item in pictures
                       if is_title_lettering(item, slide_w, slide_h)]
        page_title_ids = {item["shape_id"] for item in title_items}
        photo_slots = [
            OrderedDict([
                ("photo_slot", item["shape_id"]),
                ("left", item["left"]),
                ("top", item["top"]),
                ("width", item["width"]),
                ("height", item["height"]),
            ])
            for item in photo_items if item["shape_id"] not in page_title_ids
        ]
        title_slots = [
            OrderedDict([
                ("title_slot", item["shape_id"]),
                ("left", item["left"]),
                ("top", item["top"]),
                ("width", item["width"]),
                ("height", item["height"]),
            ])
            for item in title_items
        ]
        chrome = describe_chrome(slots)
        for slot in slots:
            slot["expect_text"] = slot["chars"] > 0
        pages.append(OrderedDict([
            ("kind", describe_page_kind(slots, pictures, slide_w, slide_h)),
            ("specificity", describe_page_specificity(slots, pictures)),
            ("page", index),
            ("layout", slide.slide_layout.name),
            ("slots", slots),
            ("chrome", chrome),
            ("fill_order", compute_fill_order(slots, chrome)),
            ("photos", photo_slots),
            ("title_slots", title_slots),
            ("pictures", pictures),
        ]))

    preserve = set()
    for page in pages:
        for slot in page["slots"]:
            if slot["role"] == "glyph":
                preserve.add(slot["shape_id"])
    clear_text(presentation, preserve)
    register_title_slots(pages)
    # 标题槽是后加的，填序要重算
    for page in pages:
        page["fill_order"] = compute_fill_order(page["slots"], page["chrome"])
    if args.content_policy in ("strip", "blank"):
        strip_content_pictures(presentation, content_ids)
    replace_with_placeholder(presentation, photo_ids)
    replace_with_title_text(presentation, title_ids)
    drop_unselected(presentation, keep)

    pack_path = os.path.join(args.outdir, "pack.pptx")
    presentation.save(pack_path)
    shrink_media(pack_path, args.max_px, args.jpeg_quality)
    if not args.keep_fonts:
        strip_embedded_fonts(pack_path)

    manifest = OrderedDict([
        ("source", os.path.basename(args.src)),
        ("slide_cm", [slide_w, slide_h]),
        ("pages", pages),
    ])
    with open(os.path.join(args.outdir, "slots.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)

    print("pack: %s (%d pages, %.1f MB)" % (pack_path, len(pages), os.path.getsize(pack_path) / 1e6))


if __name__ == "__main__":
    main()
