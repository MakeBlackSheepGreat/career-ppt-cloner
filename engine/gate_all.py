"""统一校验入口：一次跑完全部量化门，任一失败即退出码 1。

用法：
    python gate_all.py --pptx 成品.pptx --profile presentation
    python gate_all.py --pptx 成品.pptx --style styles/t-warm-orange --content 内容.json
    python gate_all.py --pptx 成品.pptx --spec-dir slide_specs --export 成品.pdf:pdf:21

门与判据：
    gate_spec      页面规格契约（主张、槽位上限、spec_complete）
    gate_content   内容 JSON 与风格包的匹配度
    gate_layout    版面几何（越界、溢出、遮挡、字号、层级、居中、变形）
    gate_palette   配色可及性（色觉缺陷、灰度、WCAG 对比度）
    gate_numbers   数字追溯（页面上的数字能否在证据文件里找到）
    gate_exports   导出件（签名、dpi、页数、尺寸）

报告写到 <pptx 同名>.gates.json，含每道门的结果与汇总。
"""
import argparse
import json
import os
import subprocess
import sys

import rules

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_gate(script, arguments):
    """跑一道门，返回 (退出码, 输出行)。"""
    path = os.path.join(ENGINE_DIR, script)
    if not os.path.exists(path):
        return 127, ["门脚本不存在：%s" % path]
    command = [sys.executable, path] + arguments
    result = subprocess.run(command, capture_output=True, text=True)
    lines = (result.stdout + result.stderr).strip().splitlines()
    return result.returncode, lines


def summarize(lines):
    for line in reversed(lines):
        if ":" in line and "FAIL=" in line:
            return line.strip()
    return lines[-1].strip() if lines else "无输出"


def main():
    parser = argparse.ArgumentParser(description="统一量化门")
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--profile", default="presentation", choices=rules.PROFILES)
    parser.add_argument("--style", default="", help="风格包目录，给了才跑内容门")
    parser.add_argument("--content", default="", help="内容 JSON，给了才跑内容门")
    parser.add_argument("--spec-dir", default="", help="spec 目录，给了才跑规格门")
    parser.add_argument("--evidence", action="append", default=[],
                        metavar="PATH", help="数字追溯的证据文件，可重复")
    parser.add_argument("--export", action="append", default=[],
                        metavar="PATH:TYPE[:PAGES或DPI]", help="导出件，可重复")
    parser.add_argument("--json", default="", help="报告路径，默认 <pptx>.gates.json")
    args = parser.parse_args()

    if not os.path.exists(args.pptx):
        raise SystemExit("文件不存在：%s" % args.pptx)

    report_path = args.json or os.path.splitext(args.pptx)[0] + ".gates.json"
    gates = []

    if args.spec_dir:
        code, lines = run_gate("gate_spec.py", ["--spec-dir", args.spec_dir, "--profile", args.profile])
        gates.append({"gate": "gate_spec", "exit": code, "summary": summarize(lines), "lines": lines})

    if args.style and args.content:
        code, lines = run_gate("gate_content.py",
                               ["--style", args.style, "--content", args.content,
                                "--profile", args.profile])
        gates.append({"gate": "gate_content", "exit": code, "summary": summarize(lines), "lines": lines})

    code, lines = run_gate("gate_layout.py",
                           ["--pptx", args.pptx, "--profile", args.profile])
    gates.append({"gate": "gate_layout", "exit": code, "summary": summarize(lines), "lines": lines})

    code, lines = run_gate("gate_palette.py",
                           ["--pptx", args.pptx, "--profile", args.profile])
    gates.append({"gate": "gate_palette", "exit": code, "summary": summarize(lines), "lines": lines})

    if args.evidence:
        arguments = ["--pptx", args.pptx, "--warn"]
        for path in args.evidence:
            arguments.extend(["--evidence", path])
        code, lines = run_gate("gate_numbers.py", arguments)
        gates.append({"gate": "gate_numbers", "exit": code, "summary": summarize(lines), "lines": lines})

    if args.export:
        arguments = ["--file", args.export[0]]
        for item in args.export[1:]:
            arguments.extend(["--file", item])
        code, lines = run_gate("gate_exports.py", arguments)
        gates.append({"gate": "gate_exports", "exit": code, "summary": summarize(lines), "lines": lines})

    for item in gates:
        print("%-14s %s" % (item["gate"], item["summary"]))
        for line in item["lines"]:
            if line.startswith("FAIL"):
                print("    " + line)
    failed = [item for item in gates if item["exit"] != 0]
    print("gate_all: 门=%d 通过=%d 失败=%d 报告=%s"
          % (len(gates), len(gates) - len(failed), len(failed), report_path))

    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"pptx": args.pptx, "profile": args.profile,
                   "gates": [{"gate": item["gate"], "exit": item["exit"],
                              "summary": item["summary"], "lines": item["lines"]}
                             for item in gates]},
                  handle, ensure_ascii=False, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
