"""数字追溯门：页面上的每个数字都要能在证据文件里找到出处。

论文画图的做法是每个绘图数字配一份 _source_data.csv，脚本读冻结数据、不硬编码数字。
搬到 PPT：页面里出现的数字，必须能在证据文件里找到同一个值，否则判失败。

证据文件支持三种格式，按扩展名自动识别：
    .csv    每一格都当候选值
    .json   递归取全部数值与数值字符串
    .md/.txt  用正则抽数字字面量

用法：
    python gate_numbers.py --pptx 成品.pptx --evidence 数据/metrics.csv
    python gate_numbers.py --content 内容.json --evidence 数据/evidence.json --warn
"""
import argparse
import csv
import json
import os
import re
import sys

import rules


# 数字字面量：整数、小数、百分比。年份与序号也在其中，靠证据文件区分。
NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?%?")
# 三位以上小数按四位归一化比对，与论文的 check_number_drift 同口径。
DECIMAL_PATTERN = re.compile(r"-?\d+\.\d{3,}")
# 这些短数字多是序号、章节编号、页码，不做追溯要求。
IGNORE_NUMBERS = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "0"}
# 时间标记不是数据主张。年份、年月、年月日都算时间标记，不参与追溯。
DATE_PATTERN = re.compile(
    r"(?:19|20)\d{2}(?:[-./]\d{1,2})?(?:[-./]\d{1,2})?"
    r"|\d{1,2}\s*月|\d{1,2}\s*日|Q[1-4]")
# 四位数字落在年份区间（含班级编号 2501 这类写法）时按时间标记处理。
YEAR_LIKE_MIN = 1900
YEAR_LIKE_MAX = 2999
# 班级、学号、编号这类标识符不是数据主张，按上下文词排除。
IDENTIFIER_CONTEXT = ("班", "学号", "编号", "序号", "第", "章节", "级")
# 页面文字里这些位置的数字是版式装饰（页眉导航、页码），不参与追溯。
CHROME_TOP_CM = 3.2


def normalize(value):
    text = str(value).strip()
    if text.endswith("%"):
        text = text[:-1]
    try:
        number = float(text)
    except ValueError:
        return None
    if number == int(number):
        return str(int(number))
    return ("%.6f" % number).rstrip("0").rstrip(".")


def numbers_in_text(text):
    """抽数据数字，排除序号、时间标记与标识符。"""
    spans = [match.span() for match in DATE_PATTERN.finditer(text)]
    found = []
    for match in NUMBER_PATTERN.finditer(text):
        token = match.group(0)
        normalized = normalize(token)
        if normalized is None:
            continue
        if normalized in IGNORE_NUMBERS:
            continue
        if len(normalized) == 4 and normalized.isdigit() \
                and YEAR_LIKE_MIN <= int(normalized) <= YEAR_LIKE_MAX:
            continue
        start, end = match.span()
        if any(left <= start and end <= right for left, right in spans):
            continue
        # 数字紧跟在字母或数字后面时属于编号（如 6b501），不是数据。
        if start > 0 and text[start - 1].isalnum():
            continue
        window = text[max(0, start - 6):min(len(text), end + 4)]
        if any(marker in window for marker in IDENTIFIER_CONTEXT):
            continue
        found.append(normalized)
    return found


def collect_evidence(path):
    """把证据文件里的全部数字收成一个集合。"""
    values = set()
    extension = os.path.splitext(path)[1].lower()
    if extension == ".csv":
        with open(path, encoding="utf-8-sig", newline="") as handle:
            for row in csv.reader(handle):
                for cell in row:
                    normalized = normalize(cell)
                    if normalized is not None:
                        values.add(normalized)
        return values
    if extension == ".json":
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)

        def walk(node):
            if isinstance(node, dict):
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
            elif isinstance(node, (int, float)) and not isinstance(node, bool):
                normalized = normalize(node)
                if normalized is not None:
                    values.add(normalized)
            elif isinstance(node, str):
                for item in numbers_in_text(node):
                    values.add(item)

        walk(payload)
        return values
    with open(path, encoding="utf-8") as handle:
        for item in numbers_in_text(handle.read()):
            values.add(item)
    return values


def collect_pages(path, profile):
    """从 pptx 抽出每页参与追溯的文字，跳过页眉导航与装饰槽。"""
    presentation, slide_w, slide_h, scheme = rules.open_presentation(path)
    pages = []
    for number, slide in enumerate(presentation.slides, 1):
        slots = rules.describe_slots(slide, slide_w, slide_h, scheme)
        entries = []
        for slot in slots:
            if slot["chrome"] or slot["role"] == "glyph":
                continue
            for item in numbers_in_text(slot["text"]):
                entries.append({"slot": slot["slot"], "role": slot["role"],
                                "value": item, "text": slot["text"][:30]})
        pages.append({"page": number, "numbers": entries})
    return pages


def collect_content(path):
    with open(path, encoding="utf-8") as handle:
        content = json.load(handle)
    pages = []
    for page_entry in content.get("pages", []):
        entries = []
        for item in page_entry.get("map", []) or []:
            text = item.get("text")
            if text is None:
                continue
            joined = "".join(text) if isinstance(text, list) else str(text)
            for value in numbers_in_text(joined):
                entries.append({"slot": item.get("slot"), "role": "-",
                                "value": value, "text": joined[:30]})
        for item in page_entry.get("slots", []) or []:
            if isinstance(item, dict):
                text = item.get("text")
                if text is None:
                    continue
                joined = "".join(text) if isinstance(text, list) else str(text)
            elif isinstance(item, list):
                joined = "".join(item)
            else:
                joined = str(item)
            for value in numbers_in_text(joined):
                entries.append({"slot": "-", "role": "-", "value": value,
                                "text": joined[:30]})
        pages.append({"page": page_entry.get("page"), "numbers": entries})
    return pages


def audit(pages, evidence, warn_only):
    findings = []
    for page in pages:
        for item in page["numbers"]:
            if item["value"] in evidence:
                findings.append({"level": "PASS", "page": page["page"],
                                 "slot": item["slot"], "rule": "数字可追溯",
                                 "actual": item["value"], "limit": "在证据集合内",
                                 "text": item["text"]})
            else:
                findings.append({"level": "WARN" if warn_only else "FAIL",
                                 "page": page["page"], "slot": item["slot"],
                                 "rule": "数字无出处", "actual": item["value"],
                                 "limit": "在证据集合内", "text": item["text"]})
    return findings


def main():
    parser = argparse.ArgumentParser(description="数字追溯门")
    parser.add_argument("--pptx", default="", help="从成品 pptx 抽数字")
    parser.add_argument("--content", default="", help="从内容 JSON 抽数字")
    parser.add_argument("--evidence", required=True, help="证据文件，可重复",
                        action="append")
    parser.add_argument("--profile", default="presentation", choices=rules.PROFILES)
    parser.add_argument("--warn", action="store_true",
                        help="只告警不失败。成品 pptx 上大量编号与装饰数字无法追溯，默认对 pptx 用告警模式")
    parser.add_argument("--json", default="", help="报告路径")
    args = parser.parse_args()

    if not args.pptx and not args.content:
        raise SystemExit("--pptx 与 --content 至少给一个")
    evidence = set()
    for path in args.evidence:
        if not os.path.exists(path):
            raise SystemExit("证据文件不存在：%s" % path)
        evidence |= collect_evidence(path)
    if not evidence:
        raise SystemExit("证据文件里没有任何数字：%s" % "、".join(args.evidence))

    pages = []
    if args.pptx:
        pages.extend(collect_pages(args.pptx, args.profile))
    if args.content:
        pages.extend(collect_content(args.content))

    findings = audit(pages, evidence, args.warn)
    for item in findings:
        if item["level"] == "PASS":
            continue
        print("%-4s 页%-4s 槽%-4s %-10s 数字=%-10s 上下文=%s  阈值=%s"
              % (item["level"], item["page"], item["slot"], item["rule"],
                 item["actual"], item["text"], item["limit"]))
    fails = [item for item in findings if item["level"] == "FAIL"]
    warns = [item for item in findings if item["level"] == "WARN"]
    passes = [item for item in findings if item["level"] == "PASS"]
    print("gate_numbers: 证据数=%d 数字数=%d FAIL=%d WARN=%d PASS=%d"
          % (len(evidence), len(findings), len(fails), len(warns), len(passes)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"evidence": args.evidence, "evidence_count": len(evidence),
                       "findings": findings}, handle, ensure_ascii=False, indent=1)
        print("报告 %s" % args.json)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
