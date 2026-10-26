import argparse
import io
import os
import zipfile

from PIL import Image


# 内嵌媒体的长边上限与 JPEG 质量。风格包只用于版面复刻，不需要印刷级精度。
MAX_SIDE_PX = 1400
JPEG_QUALITY = 76
# 已经是矢量或小文件的媒体不再处理。
SKIP_BELOW_BYTES = 120 * 1024
RASTER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
# 这些格式是矢量或动画，压了会丢清晰度或丢帧，原样保留。
KEEP_EXTENSIONS = (".emf", ".wmf", ".svg", ".gif", ".webp")


def shrink_image(data, extension):
    """把一张栅格图压到长边上限内，返回更小的字节串；压不小就返回原字节串。"""
    image = Image.open(io.BytesIO(data))
    image.load()
    width, height = image.size
    longest = max(width, height)
    if longest > MAX_SIDE_PX:
        ratio = MAX_SIDE_PX / float(longest)
        size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
        image = image.resize(size, Image.LANCZOS)
    output = io.BytesIO()
    has_alpha = image.mode in ("RGBA", "LA", "P") or "transparency" in image.info
    if has_alpha:
        image = image.convert("RGBA")
        image.save(output, "PNG", optimize=True)
    else:
        image = image.convert("RGB")
        image.save(output, "JPEG", quality=JPEG_QUALITY, optimize=True)
    candidate = output.getvalue()
    if len(candidate) < len(data):
        return candidate
    return data


def shrink_package(source, target, max_side, quality):
    global MAX_SIDE_PX, JPEG_QUALITY
    MAX_SIDE_PX = max_side
    JPEG_QUALITY = quality
    before = os.path.getsize(source)
    with zipfile.ZipFile(source) as zin:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                lower = item.filename.lower()
                if (item.filename.startswith("ppt/media/")
                        and lower.endswith(RASTER_EXTENSIONS)
                        and not lower.endswith(KEEP_EXTENSIONS)
                        and len(data) >= SKIP_BELOW_BYTES):
                    data = shrink_image(data, os.path.splitext(lower)[1])
                zout.writestr(item, data)
    with open(target, "wb") as handle:
        handle.write(buffer.getvalue())
    after = os.path.getsize(target)
    return before, after


def main():
    parser = argparse.ArgumentParser(description="压缩风格包内嵌媒体，便于发布到 GitHub")
    parser.add_argument("--src", required=True, help="源 pptx 或目录（目录下找 pack.pptx）")
    parser.add_argument("--outdir", default="", help="输出目录；留空时原地覆盖 pack.pptx")
    parser.add_argument("--max-side", type=int, default=MAX_SIDE_PX, help="媒体长边像素上限")
    parser.add_argument("--quality", type=int, default=JPEG_QUALITY, help="JPEG 质量")
    args = parser.parse_args()

    targets = []
    if os.path.isdir(args.src):
        for name in sorted(os.listdir(args.src)):
            path = os.path.join(args.src, name, "pack.pptx")
            if os.path.exists(path):
                targets.append((path, os.path.join(args.outdir or args.src, name, "pack.pptx")))
    else:
        targets.append((args.src, args.outdir or args.src))

    total_before = 0
    total_after = 0
    for source, target in targets:
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        before, after = shrink_package(source, target, args.max_side, args.quality)
        total_before += before
        total_after += after
        print("%-40s %.1f MB -> %.1f MB（%.0f%%）"
              % (os.path.basename(os.path.dirname(source)) + "/pack.pptx",
                 before / 1e6, after / 1e6, after * 100.0 / before))
    print("合计 %.1f MB -> %.1f MB" % (total_before / 1e6, total_after / 1e6))


if __name__ == "__main__":
    main()
