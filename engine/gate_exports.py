import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

from PIL import Image


TYPES = ("png", "jpeg", "pdf", "svg")
RASTER_TYPES = ("png", "jpeg")
SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "pdf": (b"%PDF",),
    "jpeg": (b"\xff\xd8\xff",),
}
HEAD_BYTES = 4096
# PNG 的 pHYs 换算成 dpi 会取整，留 1 dpi 容差。
DPI_TOLERANCE = 1.0
# DSH read_image 单边 8192 像素硬上限，超过后审阅阶段读不进来。
MAX_PNG_SIDE = 8192
# 单张栅格件体积上限，超过后传输与审阅成本过高。
MAX_RASTER_BYTES = 20 * 1024 * 1024
# PDF 页对象标记，取不到 pymupdf 时用它估算页数。
PAGE_MARK = re.compile(rb"/Type\s*/Page[^s]")


def finding(path, level, rule, actual, limit):
    return {"file": str(path), "level": level, "rule": rule,
            "actual": actual, "limit": limit}


def pdf_reader():
    """按 pymupdf 优先、fitz 次之的顺序取一个能读 PDF 的模块，都没有就返回 None。"""
    for name in ("pymupdf", "fitz"):
        if importlib.util.find_spec(name) is not None:
            return importlib.import_module(name)
    return None


def parse_declaration(text):
    """拆 PATH:TYPE[:页数或dpi]，容忍 Windows 盘符里的冒号。"""
    head, separator, tail = text.rpartition(":")
    if separator and tail.lower() in TYPES:
        path_text, kind, third = head, tail.lower(), None
    elif separator and tail.isdigit():
        head2, separator2, kind_text = head.rpartition(":")
        if not separator2 or kind_text.lower() not in TYPES:
            raise SystemExit("--file 声明格式错误（应为 PATH:TYPE[:页数或dpi]）：%s" % text)
        path_text, kind, third = head2, kind_text.lower(), int(tail)
    else:
        raise SystemExit("--file 声明格式错误（应为 PATH:TYPE[:页数或dpi]）：%s" % text)
    if not path_text:
        raise SystemExit("--file 声明缺少路径：%s" % text)
    return path_text, kind, third


def detect_signature(path):
    with path.open("rb") as handle:
        head = handle.read(HEAD_BYTES)
    for kind, signatures in SIGNATURES.items():
        for signature in signatures:
            if head.startswith(signature):
                return kind
    if b"<svg" in head.lower():
        return "svg"
    return None


def raster_info(path):
    with Image.open(path) as image:
        return {"width": image.width, "height": image.height,
                "dpi": image.info.get("dpi")}


def pdf_page_count(path):
    """返回 (页数, 来源)。页数读不出时返回 (None, 来源)。"""
    module = pdf_reader()
    if module is not None:
        with module.open(str(path)) as document:
            return document.page_count, "pymupdf"
    data = path.read_bytes()
    count = len(PAGE_MARK.findall(data))
    if count == 0:
        return None, "正则"
    return count, "正则"


def check_dpi(path, findings, info, declared):
    dpi = info["dpi"]
    if not dpi:
        findings.append(finding(path, "WARN", "dpi", "读不到 dpi", declared))
        return
    actual = float(dpi[0] if isinstance(dpi, (tuple, list)) else dpi)
    if actual + DPI_TOLERANCE < declared:
        findings.append(finding(path, "FAIL", "dpi", "%.0f" % actual, declared))
    else:
        findings.append(finding(path, "PASS", "dpi", "%.0f" % actual, declared))


def check_raster(path, findings, kind, third, size):
    info = raster_info(path)
    longest = max(info["width"], info["height"])
    if kind == "png" and longest > MAX_PNG_SIDE:
        findings.append(finding(path, "WARN", "尺寸",
                               "%dx%d 单边 %d" % (info["width"], info["height"], longest),
                               MAX_PNG_SIDE))
    elif kind == "png":
        findings.append(finding(path, "PASS", "尺寸",
                               "%dx%d" % (info["width"], info["height"]), MAX_PNG_SIDE))
    if size > MAX_RASTER_BYTES:
        findings.append(finding(path, "WARN", "体积上限", "%d 字节" % size, MAX_RASTER_BYTES))
    else:
        findings.append(finding(path, "PASS", "体积上限", "%d 字节" % size, MAX_RASTER_BYTES))
    if third is not None:
        check_dpi(path, findings, info, third)


def check_pdf(path, findings, third):
    count, source = pdf_page_count(path)
    if count is None:
        findings.append(finding(path, "WARN", "页数", "读不出页数（pymupdf 与正则均失败）",
                               third if third is not None else "可读"))
        return
    label = "%d" % count if source == "pymupdf" else "%d(正则)" % count
    if third is None:
        findings.append(finding(path, "PASS", "页数", label, "可读"))
    elif count != third:
        findings.append(finding(path, "FAIL", "页数", label, third))
    else:
        findings.append(finding(path, "PASS", "页数", label, third))


def check_file(declaration):
    path_text, kind, third = parse_declaration(declaration)
    path = Path(path_text)
    findings = []
    if not path.is_file():
        findings.append(finding(path, "FAIL", "存在", "文件不存在", "存在且非空"))
        return findings
    size = path.stat().st_size
    if size == 0:
        findings.append(finding(path, "FAIL", "体积", "0 字节", "大于 0 字节"))
        return findings
    findings.append(finding(path, "PASS", "存在", "%d 字节" % size, "存在且非空"))
    detected = detect_signature(path)
    if detected == kind:
        findings.append(finding(path, "PASS", "签名", detected, kind))
    else:
        findings.append(finding(path, "FAIL", "签名", detected or "未知", kind))
    if kind in RASTER_TYPES:
        if detected != kind:
            findings.append(finding(path, "WARN", "尺寸",
                                   "签名与声明不符，跳过尺寸与 dpi 检查", kind))
            return findings
        check_raster(path, findings, kind, third, size)
    elif kind == "pdf":
        check_pdf(path, findings, third)
    elif kind == "svg":
        if third is not None:
            findings.append(finding(path, "WARN", "页数", "svg 页数不可测", third))
        else:
            findings.append(finding(path, "PASS", "页数", "不声明页数", "不声明页数"))
    return findings


def main():
    parser = argparse.ArgumentParser(description="导出件量化门")
    parser.add_argument("--file", action="append", default=[],
                        metavar="PATH:TYPE[:页数或dpi]")
    parser.add_argument("--json", default="")
    args = parser.parse_args()
    if not args.file:
        raise SystemExit("至少需要一个 --file 声明")
    findings = []
    for declaration in args.file:
        findings.extend(check_file(declaration))
    for item in findings:
        print("%-4s  %s  %s  实测=%s  阈值=%s"
              % (item["level"], item["file"], item["rule"],
                 item["actual"], item["limit"]))
    fails = [item for item in findings if item["level"] == "FAIL"]
    warns = [item for item in findings if item["level"] == "WARN"]
    passes = [item for item in findings if item["level"] == "PASS"]
    print("gate_exports: FAIL=%d WARN=%d PASS=%d" % (len(fails), len(warns), len(passes)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(findings, handle, ensure_ascii=False, indent=1)
        print("报告 %s" % args.json)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
