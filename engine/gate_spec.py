"""把每页的版面规格先冻结成契约，再生成。

非数据图的「先填 figure-spec 再画」搬到 PPT：每页在填内容之前先有 slide-spec，
写明这页要支撑哪条主张、装什么、槽位上限、照片槽、口径档位。spec 未完成不许生成。

spec 存为 <项目>/slide_specs/spec_p<页码>.md，与内容 JSON、成品同目录可追溯。
"""
import argparse
import os
import re
import sys

import rules


STATUS_KEYS = ("spec_complete", "generated", "reviewed")
REQUIRED_SECTIONS = ("主张", "内容", "槽位上限", "状态")


def parse_spec(text):
    """解析 spec 的键值行：`- 键：值` 或 `键：值`。"""
    fields = {}
    for line in text.splitlines():
        match = re.match(r"^\s*-?\s*([^:：]+)[:：]\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key:
            fields[key] = value
    return fields


def spec_path(spec_dir, page):
    return os.path.join(spec_dir, "spec_p%02d.md" % page)


def check_spec(path, profile):
    """检查一份 spec 是否完整，返回 findings。"""
    findings = []
    if not os.path.exists(path):
        findings.append({"level": "FAIL", "rule": "spec存在", "detail": "缺少 %s" % path})
        return findings
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    fields = parse_spec(text)
    for section in REQUIRED_SECTIONS:
        if not re.search(r"(?m)^\s*#+\s*.*%s" % re.escape(section), text):
            findings.append({"level": "FAIL", "rule": "spec章节",
                             "detail": "%s 缺少「%s」小节" % (os.path.basename(path), section)})
    claim = ""
    for key in fields:
        if "主张" in key:
            claim = fields[key]
    if claim in ("", "待填", "TODO", "TBD"):
        findings.append({"level": "FAIL", "rule": "主张", "detail": "%s 的主张为空" % os.path.basename(path)})
    complete = fields.get("spec_complete", "")
    if complete.strip().upper() not in ("Y", "YES", "是"):
        findings.append({"level": "FAIL", "rule": "spec_complete",
                         "detail": "%s 的 spec_complete 不是 Y（当前 %r）"
                         % (os.path.basename(path), complete)})
    spec_profile = fields.get("口径", "")
    if spec_profile and spec_profile.strip() != profile:
        findings.append({"level": "WARN", "rule": "口径",
                         "detail": "%s 写的口径是 %s，命令行是 %s"
                         % (os.path.basename(path), spec_profile.strip(), profile)})
    return findings


def audit_specs(spec_dir, pages, profile):
    findings = []
    if not os.path.isdir(spec_dir):
        findings.append({"level": "FAIL", "rule": "spec目录", "detail": "spec 目录不存在：%s" % spec_dir})
        return findings
    for page in pages:
        findings.extend(check_spec(spec_path(spec_dir, page), profile))
    return findings


def template(page, profile, slide_w, slide_h):
    """生成一份可直接填的 spec 骨架。"""
    limits = rules.profile_limits(profile)
    lines = [
        "# 第 %d 页版面规格" % page,
        "",
        "## 主张",
        "",
        "- 主张：待填（这页要让读者记住的一句话，须能在证据文件里找到对应条目）",
        "- 叙事角色：待填（开场 / 机制说明 / 结果展示 / 收束）",
        "",
        "## 内容",
        "",
        "- 页面标题：待填",
        "- 正文要点：待填（一行一个要点）",
        "- 数据来源：待填（哪个文件或哪次实验，没有就写「无数据」）",
        "",
        "## 槽位上限",
        "",
        "- 页面尺寸：%.2f × %.2f cm" % (slide_w, slide_h),
        "- 口径：%s" % profile,
        "- 字号下限：%s" % "、".join("%s %.0fpt" % (role, size) for role, size in limits.items()),
        "- 最多正文行数：%d" % rules.MAX_BODY_LINES,
        "- 最多页面字数：%d" % rules.MAX_PAGE_CHARS,
        "",
        "## 照片",
        "",
        "- 照片槽：无 / 槽位编号",
        "- 照片来源：待填（自己的照片路径，没有就写「无」）",
        "",
        "## 状态",
        "",
        "- spec_complete：N",
        "- generated：N",
        "- reviewed：N",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="页面规格契约")
    parser.add_argument("--pptx", default="", help="从这份 pptx 的页数生成 spec 骨架")
    parser.add_argument("--pages", default="", help="页码，例如 1-21；留空按 pptx 全部页")
    parser.add_argument("--spec-dir", required=True, help="spec 目录")
    parser.add_argument("--profile", default="presentation", choices=rules.PROFILES)
    parser.add_argument("--init", action="store_true", help="生成骨架，不覆盖已有文件")
    parser.add_argument("--check", action="store_true", help="只检查，不生成")
    args = parser.parse_args()

    if args.pptx:
        presentation, slide_w, slide_h, _scheme = rules.open_presentation(args.pptx)
        total = len(presentation.slides)
    else:
        total = 0
        slide_w, slide_h = 33.867, 19.05

    pages = list(range(1, total + 1))
    if not args.pptx and os.path.isdir(args.spec_dir):
        discovered = []
        for name in sorted(os.listdir(args.spec_dir)):
            match = re.match(r"spec_p(\d+)\.md$", name)
            if match:
                discovered.append(int(match.group(1)))
        pages = discovered
    if args.pages:
        pages = []
        for token in args.pages.split(","):
            token = token.strip()
            if "-" in token:
                low, high = token.split("-")
                pages.extend(range(int(low), int(high) + 1))
            elif token:
                pages.append(int(token))

    if args.init:
        os.makedirs(args.spec_dir, exist_ok=True)
        created = 0
        for page in pages:
            path = spec_path(args.spec_dir, page)
            if os.path.exists(path):
                print("跳过已存在 %s" % path)
                continue
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(template(page, args.profile, slide_w, slide_h))
            created += 1
        print("生成 spec 骨架 %d 份于 %s" % (created, args.spec_dir))

    findings = audit_specs(args.spec_dir, pages, args.profile)
    for item in findings:
        print("%-4s %-10s %s" % (item["level"], item["rule"], item["detail"]))
    fails = [item for item in findings if item["level"] == "FAIL"]
    print("gate_spec: 页数=%d FAIL=%d" % (len(pages), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
