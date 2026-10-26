"""从一个参考演示文稿做出一整套可复用的风格包。

一条命令走完：清空文字得到 pack.pptx → 量每个文字槽 → 渲染每页缩略图 →
生成 catalog.md（给写内容的人看的页面目录）。

用法：
    python engine/build_style.py --src 参考.pptx --outdir styles/xxx \
        --name "橙暖生活" --tier A --pages 1-19

产物：
    pack.pptx        文字已清空的整套页面
    slots.json       每个文字槽的几何、字体、行距与角色
    thumbs/pNN.png   每页缩略图，写内容前先看这些图
    catalog.md       页面目录：每页的缩略图、用途提示、可填槽位表
    meta.json        风格元信息
"""
import argparse
import json
import os
import subprocess
import sys

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_DIR)

import qc  # noqa: E402


def run_make_pack(src, outdir, pages, max_px):
    command = [sys.executable, os.path.join(ENGINE_DIR, "make_pack.py"),
               "--src", src, "--outdir", outdir, "--max-px", str(max_px)]
    if pages:
        command += ["--pages", pages]
    result = subprocess.run(command, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("make_pack 失败")
    if result.stderr.strip():
        sys.stderr.write(result.stderr)


def render_thumbnails(outdir, soffice, zoom):
    pack = os.path.join(outdir, "pack.pptx")
    try:
        pdf = qc.to_pdf(pack, os.path.join(outdir, "pdf"), soffice)
        pages = qc.to_png(pdf, os.path.join(outdir, "png"), zoom, 4000)
    except SystemExit as error:
        print("跳过缩略图：%s" % error)
        return []
    thumb_dir = os.path.join(outdir, "thumbs")
    os.makedirs(thumb_dir, exist_ok=True)
    from PIL import Image
    thumbs = []
    for index, page in enumerate(pages, 1):
        target = os.path.join(thumb_dir, "p%02d.png" % index)
        image = Image.open(page).convert("RGB")
        image.thumbnail((720, 720), Image.LANCZOS)
        image.save(target)
        thumbs.append(target)
    return thumbs

ROLE_TEXT = {
    "display": "大号装饰字（章节序号等）",
    "headline": "页面主标题，字最大",
    "title": "页标题",
    "label": "短标签，四到八字",
    "body": "正文段，多行",
    "text": "一般文字",
    "backdrop_note": "压在整幅背景上的说明段",
    "glyph": "装饰字，已保留原文",
}

KIND_TEXT = {
    "cover": "封面：整幅背景图 + 若干标题条",
    "section": "章节过渡：超大序号 + 章节名",
    "text": "图文页：标题 + 正文 + 装饰",
    "grid": "并列卡片页：多个短标签 + 少量正文",
    "photo": "图片页：整幅照片，文字极少",
}

def write_catalog(outdir, manifest, thumbs, name):
    lines = ["# %s 页面目录" % name, ""]
    lines.append("来源：%s，共 %d 页。" % (manifest["source"], len(manifest["pages"])))
    lines.append("")
    lines.append("写内容前先看 thumbs 目录里的缩略图，按版面挑页，再填槽位。")
    lines.append("")
    for index, page in enumerate(manifest["pages"]):
        thumb = "thumbs/p%02d.png" % (index + 1)
        exists = index < len(thumbs) and os.path.exists(thumbs[index])
        lines.append("## 第 %d 页（%s）" % (page["page"], page["kind"]))
        lines.append("")
        if exists:
            lines.append("![第 %d 页](%s)" % (page["page"], thumb))
            lines.append("")
        lines.append(KIND_TEXT.get(page["kind"], page["kind"]))
        lines.append("")
        decorative = [slot["slot"] for slot in page["slots"] if slot["role"] == "glyph"]
        if decorative:
            lines.append("装饰槽位 %s 已保留原文，不要填。" % "、".join(str(n) for n in decorative))
            lines.append("")
        if page.get("photos"):
            lines.append("照片槽：%s（用 {\"photo\": 图片路径, \"photo_slot\": 编号} 填入）"
                         % "、".join(str(item["photo_slot"]) for item in page["photos"]))
            lines.append("")
        order = page.get("fill_order") or []
        rank = {number: position + 1 for position, number in enumerate(order)}
        lines.append("短写顺序（slots 数组按这个顺序排）：%s"
                     % " -> ".join(str(n) for n in order))
        lines.append("")
        lines.append("| 短写位 | 槽位 | 角色 | 位置 cm | 尺寸 cm | 参考字号 | 参考字数 | 参考内容 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for slot in page["slots"]:
            if slot["role"] == "glyph":
                continue
            sample = (slot.get("sample") or "").replace(chr(10), " ").replace("|", "/")
            lines.append("| %s | %d | %s | (%s, %s) | %s × %s | %s | %s | %s |" % (
                rank.get(slot["slot"], "-"),
                slot["slot"],
                ROLE_TEXT.get(slot["role"], slot["role"]),
                slot["left"], slot["top"], slot["width"], slot["height"],
                slot["font_size"] or "继承", slot["chars"], sample[:28]))
        lines.append("")
    with open(os.path.join(outdir, "catalog.md"), "w", encoding="utf-8") as handle:
        handle.write(chr(10).join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--tier", default="A", help="A 整页复刻 / B 版式复刻 / C 设计语言复刻")
    parser.add_argument("--pages", default="")
    parser.add_argument("--max-px", type=int, default=1800)
    parser.add_argument("--soffice", default="")
    parser.add_argument("--zoom", type=float, default=1.3)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    args.src = os.path.abspath(args.src)
    args.outdir = os.path.abspath(args.outdir)
    os.makedirs(args.outdir, exist_ok=True)
    run_make_pack(args.src, args.outdir, args.pages, args.max_px)

    with open(os.path.join(args.outdir, "slots.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)

    soffice = qc.find_soffice(args.soffice)
    thumbs = render_thumbnails(args.outdir, soffice, args.zoom)
    write_catalog(args.outdir, manifest, thumbs, args.name)

    meta = {
        "name": args.name,
        "style_id": os.path.basename(os.path.abspath(args.outdir)),
        "tier": args.tier,
        "source": manifest["source"],
        "slide_cm": manifest["slide_cm"],
        "page_count": len(manifest["pages"]),
        "pages": [{"page": page["page"], "kind": page["kind"],
                   "slots": len([s for s in page["slots"] if s["role"] != "glyph"])}
                  for page in manifest["pages"]],
        "note": args.note,
    }
    with open(os.path.join(args.outdir, "meta.json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=1)

    print("风格包完成：%s（%d 页，%d 张缩略图）" % (args.outdir, len(manifest["pages"]), len(thumbs)))


if __name__ == "__main__":
    main()
