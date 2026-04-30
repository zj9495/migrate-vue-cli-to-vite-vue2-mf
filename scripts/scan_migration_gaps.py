#!/usr/bin/env python3
"""
Scan a project for common Vue CLI -> Vite migration gaps.

Usage:
  python3 scripts/scan_migration_gaps.py --project-root <path> --format markdown|json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


TEXT_FILE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".mjs",
    ".cjs",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".pcss",
    ".json",
    ".html",
    ".md",
}

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
}

LEGACY_CONFIG_FILES = [
    "vue.config.js",
    "webpack.alias.config.js",
    "setup-public-path.js",
    "generateProxy.js",
    "babel.config.js",
]


@dataclass
class Match:
    file: str
    line: int
    snippet: str


@dataclass
class Rule:
    rule_id: str
    title: str
    severity: str
    description: str
    next_action: str
    regex: re.Pattern | None = None
    file_scope: Tuple[str, ...] | None = None


RULES: List[Rule] = [
    Rule(
        rule_id="webpack-require-context",
        title="webpack require.context usage",
        severity="blocker",
        description="Vite does not support require.context in browser runtime.",
        next_action="Replace with import.meta.glob(...).",
        regex=re.compile(r"\brequire\.context\s*\("),
    ),
    Rule(
        rule_id="webpack-module-hot",
        title="webpack module.hot usage",
        severity="blocker",
        description="Vite HMR API differs from webpack.",
        next_action="Replace module.hot with import.meta.hot patterns.",
        regex=re.compile(r"\bmodule\.hot\b"),
    ),
    Rule(
        rule_id="webpack-public-path",
        title="webpack __webpack_public_path__ usage",
        severity="blocker",
        description="Runtime webpack public path mutation is not supported in Vite.",
        next_action="Remove and use Vite base path strategy.",
        regex=re.compile(r"__webpack_public_path__"),
    ),
    Rule(
        rule_id="process-env-usage",
        title="process.env usage in source",
        severity="warning",
        description="Legacy env access can break in Vite source modules.",
        next_action="Replace with import.meta.env or a local explicit mapping. Do not keep legacy process.env bridges in migrated source.",
        regex=re.compile(r"\bprocess\.env\b"),
        file_scope=("src/",),
    ),
    Rule(
        rule_id="legacy-vue-app-prefix",
        title="legacy VUE_APP env contract",
        severity="blocker",
        description="Completed Vite migrations should not retain Vue CLI VUE_APP_* env names.",
        next_action="Rename runtime vars to VITE_* and rename deploy-only/private vars to neutral names such as SERVER_ID.",
        regex=re.compile(r"\bVUE_APP_[A-Z0-9_]+\b"),
    ),
    Rule(
        rule_id="legacy-base-url-contract",
        title="legacy process.env.BASE_URL contract",
        severity="blocker",
        description="Vite source should consume BASE_URL through import.meta.env.BASE_URL, not process.env.BASE_URL.",
        next_action="Replace process.env.BASE_URL with import.meta.env.BASE_URL and remove any Vite define bridge for BASE_URL.",
        regex=re.compile(r"\bprocess\.env\.BASE_URL\b"),
    ),
    Rule(
        rule_id="css-tilde-alias",
        title="CSS url(~@/...) usage",
        severity="warning",
        description="Webpack-specific tilde alias is not recognized by Vite.",
        next_action="Use url(@/...) or resolved relative paths.",
        regex=re.compile(r"url\(\s*['\"]?~@/"),
    ),
    Rule(
        rule_id="asset-require-call",
        title="asset require(...) usage",
        severity="warning",
        description="Asset require patterns are fragile under Vite static analysis.",
        next_action="Use static import or import.meta.glob where dynamic lookup is needed.",
        regex=re.compile(r"\brequire\s*\(\s*['\"`].*\.(png|jpe?g|gif|svg|webp|ttf|woff2?)", re.IGNORECASE),
    ),
    Rule(
        rule_id="dynamic-require-template",
        title="dynamic require with template literal",
        severity="blocker",
        description="Dynamic require(`...${x}...`) is not analyzable by Vite bundling.",
        next_action="Replace with import.meta.glob lookup map.",
        regex=re.compile(r"\brequire\s*\(\s*`"),
    ),
    Rule(
        rule_id="dynamic-import-missing-vue-extension",
        title="dynamic import may miss .vue extension",
        severity="warning",
        description="Dynamic import paths without explicit .vue may warn/fail in SFC scenarios.",
        next_action="When importing Vue components dynamically, append .vue in template literal path.",
        regex=re.compile(r"\bimport\s*\(\s*`[^`]*\$\{[^}]+\}[^`]*`\s*\)"),
    ),
    Rule(
        rule_id="webpack-loader-inline-syntax",
        title="webpack inline loader syntax",
        severity="blocker",
        description="Inline loaders (file-loader/url-loader/raw-loader) are webpack-only.",
        next_action="Replace with Vite asset imports, often ?url suffix.",
        regex=re.compile(r"(file-loader|url-loader|raw-loader)!"),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan Vue CLI to Vite migration gaps.")
    parser.add_argument("--project-root", required=True, help="Target project root path")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format",
    )
    return parser.parse_args()


def iter_text_files(project_root: Path) -> Iterable[Path]:
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_FILE_EXTENSIONS:
            continue
        yield path


def should_scan_rule_for_file(rule: Rule, relpath: str) -> bool:
    if not rule.file_scope:
        return True
    return any(relpath.startswith(prefix) for prefix in rule.file_scope)


def find_line_matches(content: str, rule: Rule, relpath: str) -> List[Match]:
    if rule.regex is None or not should_scan_rule_for_file(rule, relpath):
        return []

    matches: List[Match] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if rule.regex.search(line):
            matches.append(Match(file=relpath, line=line_number, snippet=line.strip()))
    return matches


def scan_source_rules(project_root: Path) -> Tuple[Dict[str, List[Match]], int]:
    findings: Dict[str, List[Match]] = {rule.rule_id: [] for rule in RULES}
    files_scanned = 0

    for path in iter_text_files(project_root):
        relpath = path.relative_to(project_root).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files_scanned += 1
        for rule in RULES:
            findings[rule.rule_id].extend(find_line_matches(content, rule, relpath))

    return findings, files_scanned


def scan_legacy_files(project_root: Path) -> List[Match]:
    matches: List[Match] = []
    for filename in LEGACY_CONFIG_FILES:
        path = project_root / filename
        if path.exists():
            matches.append(Match(file=filename, line=1, snippet=f"legacy config file exists: {filename}"))
    return matches


def scan_package_scripts(project_root: Path) -> List[Match]:
    package_json = project_root / "package.json"
    if not package_json.exists():
        return []
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [Match(file="package.json", line=1, snippet="failed to parse package.json")]

    scripts = data.get("scripts") or {}
    if not isinstance(scripts, dict):
        return []

    matches: List[Match] = []
    for key, value in scripts.items():
        if not isinstance(value, str):
            continue
        if "vue-cli-service" in value:
            matches.append(
                Match(
                    file="package.json",
                    line=1,
                    snippet=f"scripts.{key} still uses vue-cli-service: {value}",
                )
            )
    return matches


def build_categories(
    source_findings: Dict[str, List[Match]],
    legacy_files: List[Match],
    script_findings: List[Match],
) -> List[Dict]:
    rule_map = {rule.rule_id: rule for rule in RULES}
    categories: List[Dict] = []

    for rule_id, matches in source_findings.items():
        if not matches:
            continue
        rule = rule_map[rule_id]
        categories.append(
            {
                "id": rule.rule_id,
                "title": rule.title,
                "severity": rule.severity,
                "description": rule.description,
                "next_action": rule.next_action,
                "count": len(matches),
                "matches": [match.__dict__ for match in matches],
            }
        )

    if legacy_files:
        categories.append(
            {
                "id": "legacy-config-files",
                "title": "legacy Vue CLI/webpack config files exist",
                "severity": "blocker",
                "description": "Legacy config files typically conflict with Vite migration assumptions.",
                "next_action": "Migrate settings into vite.config.* and remove stale files.",
                "count": len(legacy_files),
                "matches": [match.__dict__ for match in legacy_files],
            }
        )

    if script_findings:
        categories.append(
            {
                "id": "legacy-package-scripts",
                "title": "package scripts still reference vue-cli-service",
                "severity": "blocker",
                "description": "Primary package scripts still target Vue CLI commands.",
                "next_action": "Switch scripts to vite / vite build / vite preview.",
                "count": len(script_findings),
                "matches": [match.__dict__ for match in script_findings],
            }
        )

    severity_order = {"blocker": 0, "warning": 1, "info": 2}
    categories.sort(key=lambda item: (severity_order.get(item["severity"], 99), item["id"]))
    return categories


def summarize(categories: List[Dict], files_scanned: int) -> Dict[str, int]:
    blockers = sum(item["count"] for item in categories if item["severity"] == "blocker")
    warnings = sum(item["count"] for item in categories if item["severity"] == "warning")
    infos = sum(item["count"] for item in categories if item["severity"] == "info")
    return {
        "files_scanned": files_scanned,
        "categories": len(categories),
        "blocker": blockers,
        "warning": warnings,
        "info": infos,
        "total_matches": blockers + warnings + infos,
    }


def render_markdown(report: Dict) -> str:
    lines: List[str] = []
    summary = report["summary"]
    lines.append("# Migration Gap Scan")
    lines.append("")
    lines.append(f"- Project: `{report['project_root']}`")
    lines.append(f"- Files scanned: `{summary['files_scanned']}`")
    lines.append(f"- Categories: `{summary['categories']}`")
    lines.append(
        "- Match counts: "
        f"`blocker={summary['blocker']}`, "
        f"`warning={summary['warning']}`, "
        f"`info={summary['info']}`, "
        f"`total={summary['total_matches']}`"
    )
    lines.append("")

    if not report["categories"]:
        lines.append("No migration gaps detected by current rules.")
        return "\n".join(lines)

    for category in report["categories"]:
        lines.append(f"## [{category['severity'].upper()}] {category['title']} ({category['count']})")
        lines.append(f"- id: `{category['id']}`")
        lines.append(f"- description: {category['description']}")
        lines.append(f"- next_action: {category['next_action']}")
        lines.append("- matches:")
        for match in category["matches"]:
            lines.append(f"  - `{match['file']}:{match['line']}` -> `{match['snippet']}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise SystemExit(f"[ERROR] project root is not a directory: {project_root}")

    source_findings, files_scanned = scan_source_rules(project_root)
    legacy_files = scan_legacy_files(project_root)
    script_findings = scan_package_scripts(project_root)
    categories = build_categories(source_findings, legacy_files, script_findings)
    report = {
        "project_root": project_root.as_posix(),
        "summary": summarize(categories, files_scanned),
        "categories": categories,
    }

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report), end="")

    # Non-zero when blockers exist.
    return 1 if report["summary"]["blocker"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
