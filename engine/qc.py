"""把 pptx 转成 PDF，再把每页渲染成 PNG，并拼一张 contact sheet 供目视检查。

用法：
    python engine/qc.py --pptx 成品.pptx --outdir _work/qc/成品

环境要求：LibreOffice（soffice）与 pymupdf。soffice 路径可用 --soffice 覆盖，
也可以用环境变量 SOFFICE_PATH 指定。
"""
import argparse
import os
import shutil
import subprocess
import sys

CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_soffice(explicit):
    if explicit:
        return explicit
    env = os.environ.get("SOFFICE_PATH")
    if env:
        return env
    for path in CANDIDATES:
        if os.path.exists(path):
            return path
    found = shutil.which("soffice")
    if found:
        return found
    raise SystemExit("找不到 soffice，请用 --soffice 指定路径或设置 SOFFICE_PATH")


def to_pdf(pptx, outdir, soffice):
    os.makedirs(outdir, exist_ok=True)
    profile = "file:///" + os.path.join(os.path.abspath(outdir), "_soffice-profile").replace("\\", "/")
    command = [soffice, "-env:UserInstallation=" + profile, "--headless",
               "--convert-to", "pdf", "--outdir", outdir, pptx]
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-2000:] + "\n" + result.stderr[-2000:] + "\n")
        raise SystemExit("LibreOffice 转换失败")
    base = os.path.splitext(os.path.basename(pptx))[0] + ".pdf"
    pdf = os.path.join(outdir, base)
    if not os.path.exists(pdf):
        raise SystemExit("转换后没有找到 PDF：%s" % pdf)
    return pdf


def to_png(pdf, outdir, zoom, max_side):
    import pymupdf
    from PIL import Image

    os.makedirs(outdir, exist_ok=True)
    document = pymupdf.open(pdf)
    pages = []
    for number, page in enumerate(document, 1):
        path = os.path.join(outdir, "p%02d.png" % number)
        rect = page.rect
        scale = zoom
        if rect.width * scale > max_side or rect.height * scale > max_side:
            scale = min(max_side / rect.width, max_side / rect.height)
        page.get_pixmap(matrix=pymupdf.Matrix(scale, scale)).save(path)
        pages.append(path)
    return pages


def contact_sheet(pages, out_path, columns, cell_width):
    from PIL import Image

    images = [Image.open(path).convert("RGB") for path in pages]
    width = images[0].width
    ratio = cell_width / float(width)
    cell_height = int(images[0].height * ratio)
    rows = (len(images) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * (cell_width + 8), rows * (cell_height + 8)), "white")
    for index, image in enumerate(images):
        row, column = divmod(index, columns)
        canvas.paste(image.resize((cell_width, cell_height), Image.LANCZOS),
                     (column * (cell_width + 8), row * (cell_height + 8)))
    canvas.save(out_path, quality=90)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--soffice", default="")
    parser.add_argument("--zoom", type=float, default=1.4)
    parser.add_argument("--max-side", type=int, default=4000)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--cell-width", type=int, default=560)
    args = parser.parse_args()

    soffice = find_soffice(args.soffice)
    pdf_dir = os.path.join(args.outdir, "pdf")
    png_dir = os.path.join(args.outdir, "png")
    pdf = to_pdf(args.pptx, pdf_dir, soffice)
    pages = to_png(pdf, png_dir, args.zoom, args.max_side)
    sheet = contact_sheet(pages, os.path.join(args.outdir, "sheet.jpg"),
                          args.columns, args.cell_width)
    print("pdf  %s" % pdf)
    print("pages %d" % len(pages))
    print("sheet %s" % sheet)


if __name__ == "__main__":
    main()
