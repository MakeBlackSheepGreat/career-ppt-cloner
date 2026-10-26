"""文字与底衬框像素级居中。

参考件里文字框与色块是两个独立形状，位置常差一两毫米。复刻时如果沿用文字框原位置，
文字在色块里就是歪的。这里把文字框重新摆到底衬框正中心：

- 文字框的中点严格等于底衬框的中点（左右上下都居中）；
- 框内再设水平居中 + 垂直居中，让文字在框里也是正的。

底衬中心由 make_pack 写进 slots.json 的 centroid 字段。没有底衬的槽位，centroid 就是
文字框自己的中心，等同于保持原位。
"""
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN


def place_at_centroid(shape, centroid):
    """把 shape 的中点挪到 centroid，返回实际偏移量（EMU）。"""
    if not centroid:
        return None
    target_cx, target_cy = centroid
    current_cx = shape.left + shape.width / 2.0
    current_cy = shape.top + shape.height / 2.0
    dx = int(round(target_cx - current_cx))
    dy = int(round(target_cy - current_cy))
    if dx or dy:
        shape.left = int(shape.left + dx)
        shape.top = int(shape.top + dy)
    return dx, dy


def center_text_in_frame(shape, mode="both"):
    """让文字在框内水平居中、垂直居中。"""
    frame = shape.text_frame
    if mode in ("both", "vertical"):
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    if mode in ("both", "horizontal"):
        for paragraph in frame.paragraphs:
            paragraph.alignment = PP_ALIGN.CENTER


def align_slot(shape, slot_manifest, mode):
    """按 mode 处理一个槽位：both / vertical / horizontal / off。"""
    if mode == "off":
        return None
    moved = place_at_centroid(shape, slot_manifest.get("centroid"))
    center_text_in_frame(shape, mode)
    return moved


def check_centering(shape, centroid):
    """复核：文字框中点与目标中点的偏差，单位厘米。"""
    if not centroid:
        return None
    cx = (shape.left + shape.width / 2.0) / 360000.0
    cy = (shape.top + shape.height / 2.0) / 360000.0
    tx = centroid[0] / 360000.0
    ty = centroid[1] / 360000.0
    return {
        "dx_cm": round(cx - tx, 4),
        "dy_cm": round(cy - ty, 4),
        "centered": abs(cx - tx) < 0.002 and abs(cy - ty) < 0.002,
    }
