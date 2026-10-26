"""量文字、算字号、自动折行：把内容塞进参考页原来的文字槽。

参考页的每个文字槽都有固定的宽高，装饰图形又常压在文字框上面，所以新内容一旦比
原文更宽或更长，就会钻到装饰底下。这里的做法是：

1. 按实际可用宽度做贪心折行，中文按字断行，英文单词不拆开；
2. 折行后算总高度，放不下就按半磅递减字号，直到高度也放得下；
3. 结果与诊断一起返回，放不下时明确报出来，不悄悄溢出。

CJK 字形在常用黑体里基本都是全角方块，用字体度量取近似值再加安全系数足够准。
"""
import os

# 拉丁字符相对 CJK 全角宽度的经验比例
LATIN_UPPER = 0.62
LATIN_LOWER = 0.52
DIGIT = 0.56
SPACE = 0.28
NARROW_PUNCT = 0.30

LINE_HEIGHT_RATIO = 1.22
# 字体度量与实际排版的偏差留一点余量
SAFETY = 1.04
# 中文标点不允许出现在行首
NO_LINE_START = set("，。、；：？！）》」』】…%,.;:?!)]}")
# 中文标点不允许出现在行尾
NO_LINE_END = set("（《「『【([{")

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

_metrics_cache = {}


def is_wide(char):
    code = ord(char)
    if code < 0x1100:
        return False
    if 0x1100 <= code <= 0x115F:
        return True
    if 0x2E80 <= code <= 0xA4CF:
        return True
    if 0xAC00 <= code <= 0xD7A3:
        return True
    if 0xF900 <= code <= 0xFAFF:
        return True
    if 0xFE30 <= code <= 0xFE6F:
        return True
    if 0xFF00 <= code <= 0xFF60:
        return True
    if 0xFFE0 <= code <= 0xFFE6:
        return True
    return False


def char_em(char):
    if is_wide(char):
        return 1.0
    if char == " ":
        return SPACE
    if char.isupper():
        return LATIN_UPPER
    if char.isdigit():
        return DIGIT
    if char in "'\".,;:!|[]()":
        return NARROW_PUNCT
    return LATIN_LOWER


def text_em(text):
    return sum(char_em(char) for char in text)


def text_width_cm(text, font_size_pt):
    """字宽估算：全角字宽等于字号，em 数乘以字号再换算成厘米。"""
    return text_em(text) * font_size_pt * 0.03528 * SAFETY


def line_height_cm(font_size_pt, line_spacing=None):
    ratio = float(line_spacing) if line_spacing else LINE_HEIGHT_RATIO
    return font_size_pt * 0.03528 * ratio


def usable_area(slot):
    """文本框去掉自身内边距后的可用宽高，单位厘米。"""
    insets = slot.get("insets") or [0.254, 0.254, 0.127, 0.127]
    left, right, top, bottom = insets
    width = max(0.4, (slot.get("width") or 0.0) - left - right)
    height = max(0.3, (slot.get("height") or 0.0) - top - bottom)
    return width, height


def _tokens(text):
    """切成可断行单元：中文单字，英文按单词，数字按整串。"""
    tokens = []
    buffer = ""
    for char in text:
        if is_wide(char):
            if buffer:
                tokens.append(buffer)
                buffer = ""
            tokens.append(char)
        elif char == " ":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            tokens.append(" ")
        else:
            buffer += char
    if buffer:
        tokens.append(buffer)
    return tokens


def wrap_line(text, width_limit_cm, font_size_pt):
    """按可用宽度把一行折成若干行。"""
    if not text:
        return [""]
    tokens = _tokens(text)
    lines = []
    current = ""
    for token in tokens:
        candidate = current + token
        if text_width_cm(candidate.rstrip(), font_size_pt) <= width_limit_cm or not current.strip():
            current = candidate
            continue
        # 当前行已满：处理标点禁则后换行
        if token and token[0] in NO_LINE_START and current:
            current = candidate
            lines.append(current.strip())
            current = ""
            continue
        if current and current[-1] in NO_LINE_END:
            carry = current[-1]
            current = current[:-1]
            lines.append(current.strip())
            current = carry + token
            continue
        lines.append(current.strip())
        current = token
    if current.strip() or not lines:
        lines.append(current.strip())
    return lines


def wrap_block(lines, width_limit_cm, font_size_pt):
    wrapped = []
    for line in lines:
        wrapped.extend(wrap_line(line, width_limit_cm, font_size_pt))
    return wrapped


def block_height_cm(lines, font_size_pt, line_spacing=None, space_after_pt=0.0):
    height = len(lines) * line_height_cm(font_size_pt, line_spacing)
    height += max(0, len(lines) - 1) * float(space_after_pt) * 0.03528
    return height


def fit_block(slot, lines, requested_pt, line_spacing=None, space_after_pt=0.0,
              min_pt=7.0, max_lines=None):
    """折行并按高度收字号，返回最终字号与折行结果。"""
    width_limit, height_limit = usable_area(slot)
    if line_spacing is None:
        line_spacing = slot.get("line_spacing")
    size = float(requested_pt or 18.0)
    last = None
    while size >= min_pt:
        wrapped = wrap_block(lines, width_limit, size)
        height = block_height_cm(wrapped, size, line_spacing, space_after_pt)
        last = (size, wrapped, height)
        if height <= height_limit and (max_lines is None or len(wrapped) <= max_lines):
            return size, wrapped, height, width_limit, height_limit
        size -= 0.5
    size, wrapped, height = last
    return min_pt, wrapped, height, width_limit, height_limit


def analyse(slot, lines, requested_pt, line_spacing=None, space_after_pt=0.0):
    """一次算完，返回字号、折行内容与诊断。"""
    requested = float(requested_pt or 18.0)
    size, wrapped, height, width_limit, height_limit = fit_block(
        slot, lines, requested, line_spacing, space_after_pt)
    widest = max((text_width_cm(line, size) for line in wrapped), default=0.0)
    return {
        "slot": slot.get("slot"),
        "role": slot.get("role"),
        "requested_pt": requested,
        "fitted_pt": size,
        "lines": wrapped,
        "line_count": len(wrapped),
        "reference_lines": slot.get("paragraphs"),
        "need_width_cm": round(widest, 2),
        "box_width_cm": round(width_limit, 2),
        "box_height_cm": round(height_limit, 2),
        "need_height_cm": round(height, 2),
        "width_ok": widest <= width_limit + 0.02,
        "height_ok": height <= height_limit + 0.02,
        "shrunk": size < requested - 0.01,
    }
