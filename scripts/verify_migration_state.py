#!/usr/bin/env python3
"""
Verify expected migration end-state for Vue2 + Module Federation projects on Vite 7.

Usage:
  python3 scripts/verify_migration_state.py --project-root <path>
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


VITE_CONFIG_CANDIDATES = [
    "vite.config.js",
    "vite.config.ts",
    "vite.config.mjs",
    "vite.config.cjs",
]

LEGACY_BLOCKER_FILES = [
    "vue.config.js",
    "webpack.alias.config.js",
    "setup-public-path.js",
    "generateProxy.js",
]

LEGACY_WARN_FILES = [
    "babel.config.js",
]

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


@dataclass
class Check:
    check_id: str
    title: str
    severity: str
    status: str
    detail: str
    next_action: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Vue CLI -> Vite migration state.")
    parser.add_argument("--project-root", required=True, help="Project root directory")
    return parser.parse_args()


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def iter_text_files(project_root: Path) -> Iterable[Path]:
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_FILE_EXTENSIONS:
            continue
        yield path


def find_regex_matches(project_root: Path, pattern: re.Pattern) -> List[Tuple[str, int, str]]:
    matches: List[Tuple[str, int, str]] = []
    for path in iter_text_files(project_root):
        relpath = path.relative_to(project_root).as_posix()
        for line_number, line in enumerate(safe_read(path).splitlines(), start=1):
            if pattern.search(line):
                matches.append((relpath, line_number, line.strip()))
    return matches


def format_match_preview(matches: List[Tuple[str, int, str]], limit: int = 5) -> str:
    preview = [f"{file}:{line} `{snippet}`" for file, line, snippet in matches[:limit]]
    if len(matches) > limit:
        preview.append(f"... and {len(matches) - limit} more")
    return "; ".join(preview)


def check_vite_config(project_root: Path) -> Check:
    existing = [name for name in VITE_CONFIG_CANDIDATES if (project_root / name).exists()]
    if not existing:
        return Check(
            check_id="vite-config-exists",
            title="Vite config exists",
            severity="blocker",
            status="FAIL",
            detail="No vite.config.* file found.",
            next_action="Create vite.config.js (or .ts/.mjs/.cjs) and configure Vue2 plugins.",
        )
    return Check(
        check_id="vite-config-exists",
        title="Vite config exists",
        severity="blocker",
        status="PASS",
        detail=f"Found: {', '.join(existing)}",
        next_action="None.",
    )


def check_index_entry(project_root: Path) -> Check:
    index_html = project_root / "index.html"
    if not index_html.exists():
        return Check(
            check_id="index-html-entry",
            title="Root index.html exists with Vite entry",
            severity="blocker",
            status="FAIL",
            detail="index.html is missing.",
            next_action="Add root index.html with module entry script to src/main.js.",
        )
    text = safe_read(index_html)
    if re.search(r'<script[^>]+type=["\']module["\'][^>]+src=["\']/src/main\.(js|ts|mjs|jsx|tsx)["\']', text):
        return Check(
            check_id="index-html-entry",
            title="Root index.html exists with Vite entry",
            severity="blocker",
            status="PASS",
            detail="Module entry script to /src/main.* detected.",
            next_action="None.",
        )
    return Check(
        check_id="index-html-entry",
        title="Root index.html exists with Vite entry",
        severity="warning",
        status="WARN",
        detail="index.html exists but /src/main.* module entry was not detected.",
        next_action="Ensure index.html has <script type=\"module\" src=\"/src/main.js\"></script> or equivalent.",
    )


def check_package_scripts(project_root: Path) -> Check:
    package_json = project_root / "package.json"
    if not package_json.exists():
        return Check(
            check_id="package-scripts",
            title="package.json scripts migrated to Vite",
            severity="blocker",
            status="FAIL",
            detail="package.json missing.",
            next_action="Add package.json with scripts.dev/build/preview for Vite.",
        )
    try:
        data = json.loads(safe_read(package_json))
    except json.JSONDecodeError:
        return Check(
            check_id="package-scripts",
            title="package.json scripts migrated to Vite",
            severity="blocker",
            status="FAIL",
            detail="package.json parse failed.",
            next_action="Fix JSON format and set scripts.dev/build/preview.",
        )
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return Check(
            check_id="package-scripts",
            title="package.json scripts migrated to Vite",
            severity="blocker",
            status="FAIL",
            detail="scripts field missing or invalid.",
            next_action="Set scripts.dev/build/preview with Vite commands.",
        )

    missing = [name for name in ("dev", "build", "preview") if name not in scripts]
    if missing:
        return Check(
            check_id="package-scripts",
            title="package.json scripts migrated to Vite",
            severity="blocker",
            status="FAIL",
            detail=f"Missing scripts: {', '.join(missing)}.",
            next_action="Add missing scripts mapped to vite commands.",
        )

    invalid = []
    if "vite" not in str(scripts.get("dev", "")):
        invalid.append("scripts.dev")
    if "vite build" not in str(scripts.get("build", "")):
        invalid.append("scripts.build")
    if "vite preview" not in str(scripts.get("preview", "")):
        invalid.append("scripts.preview")
    legacy = [k for k, v in scripts.items() if isinstance(v, str) and "vue-cli-service" in v]

    if invalid:
        return Check(
            check_id="package-scripts",
            title="package.json scripts migrated to Vite",
            severity="blocker",
            status="FAIL",
            detail=f"Unexpected values in {', '.join(invalid)}.",
            next_action="Set scripts.dev='vite', scripts.build='vite build', scripts.preview='vite preview'.",
        )

    if legacy:
        return Check(
            check_id="package-scripts",
            title="package.json scripts migrated to Vite",
            severity="warning",
            status="WARN",
            detail=f"Legacy vue-cli-service script entries still exist: {', '.join(legacy)}.",
            next_action="Remove or rename legacy scripts after migration stabilization.",
        )

    return Check(
        check_id="package-scripts",
        title="package.json scripts migrated to Vite",
        severity="blocker",
        status="PASS",
        detail="scripts.dev/build/preview are mapped to Vite commands.",
        next_action="None.",
    )


def check_legacy_files(project_root: Path) -> List[Check]:
    checks: List[Check] = []
    for filename in LEGACY_BLOCKER_FILES:
        exists = (project_root / filename).exists()
        checks.append(
            Check(
                check_id=f"legacy-file-{filename}",
                title=f"Legacy file removed: {filename}",
                severity="blocker",
                status="FAIL" if exists else "PASS",
                detail=f"{filename} {'still exists' if exists else 'not found'}",
                next_action="Migrate content into vite.config.* then delete legacy file." if exists else "None.",
            )
        )
    for filename in LEGACY_WARN_FILES:
        exists = (project_root / filename).exists()
        checks.append(
            Check(
                check_id=f"legacy-file-{filename}",
                title=f"Legacy file removed or justified: {filename}",
                severity="warning",
                status="WARN" if exists else "PASS",
                detail=f"{filename} {'exists' if exists else 'not found'}",
                next_action="Keep only if still needed by non-Vite tooling; otherwise remove." if exists else "None.",
            )
        )
    return checks


def check_module_federation(project_root: Path) -> Check:
    config_paths = [project_root / name for name in VITE_CONFIG_CANDIDATES if (project_root / name).exists()]
    vite_config_text = "\n".join(safe_read(path) for path in config_paths)
    has_mf_plugin = bool(
        re.search(r"@module-federation/vite", vite_config_text)
        or re.search(r"\bfederation\s*\(", vite_config_text)
    )
    has_preserve_plugin = bool(
        re.search(
            r"plugins\s*:\s*\[[\s\S]*?\bpreserveVueFederationSingleton\s*\(\s*\)",
            vite_config_text,
        )
    )

    remote_wrapper = project_root / "public" / "remoteEntry.js"
    has_wrapper = remote_wrapper.exists()

    if has_mf_plugin and not has_preserve_plugin:
        return Check(
            check_id="module-federation-compat",
            title="Module Federation + Vue singleton preservation",
            severity="blocker",
            status="FAIL",
            detail="MF plugin detected but preserveVueFederationSingleton() was not found in vite.config plugins.",
            next_action="Add preserveVueFederationSingleton() before federation() so Vue shared singleton resolution still targets bare vue.",
        )
    if has_mf_plugin and has_wrapper:
        return Check(
            check_id="module-federation-compat",
            title="Module Federation + Vue singleton preservation",
            severity="warning",
            status="PASS",
            detail="Detected MF plugin config, preserveVueFederationSingleton(), and public/remoteEntry.js wrapper.",
            next_action="None.",
        )
    if has_mf_plugin and not has_wrapper:
        return Check(
            check_id="module-federation-compat",
            title="Module Federation + Vue singleton preservation",
            severity="warning",
            status="WARN",
            detail="MF plugin and preserveVueFederationSingleton() detected but public/remoteEntry.js wrapper is missing.",
            next_action="Add wrapper if any webpack consumer expects script/var remote.",
        )
    return Check(
        check_id="module-federation-compat",
        title="Module Federation + Vue singleton preservation",
        severity="info",
        status="WARN",
        detail="MF plugin was not detected in vite config.",
        next_action="If project uses Module Federation, add @module-federation/vite configuration.",
    )


def check_env_migration_gate(project_root: Path) -> Check:
    legacy_vue_app_matches = find_regex_matches(project_root, re.compile(r"\bVUE_APP_[A-Z0-9_]+\b"))
    legacy_base_url_matches = find_regex_matches(project_root, re.compile(r"\bprocess\.env\.BASE_URL\b"))

    if legacy_vue_app_matches or legacy_base_url_matches:
        details: List[str] = []
        if legacy_vue_app_matches:
            details.append(
                "legacy VUE_APP contract found: "
                f"{format_match_preview(legacy_vue_app_matches)}"
            )
        if legacy_base_url_matches:
            details.append(
                "legacy process.env.BASE_URL usage found: "
                f"{format_match_preview(legacy_base_url_matches)}"
            )
        return Check(
            check_id="env-migration-gate",
            title="Env migration gate completed",
            severity="blocker",
            status="FAIL",
            detail="; ".join(details),
            next_action="Rename runtime vars to VITE_*, consume BASE_URL via import.meta.env.BASE_URL, and remove remaining legacy Vue CLI env contracts.",
        )

    package_json_text = safe_read(project_root / "package.json")
    vite_config_text = "\n".join(
        safe_read(project_root / name)
        for name in VITE_CONFIG_CANDIDATES
        if (project_root / name).exists()
    )

    missing = []
    if "VITE_APP_MODE" not in package_json_text:
        missing.append("package.json is missing VITE_APP_MODE in scripts")
    if "VITE_APP_DEPEND_SITUATION" not in package_json_text:
        missing.append("package.json is missing VITE_APP_DEPEND_SITUATION in scripts")
    if "VITE_APP_MODE" not in vite_config_text:
        missing.append("vite.config.* is missing VITE_APP_MODE usage")
    if "VITE_APP_DEPEND_SITUATION" not in vite_config_text:
        missing.append("vite.config.* is missing VITE_APP_DEPEND_SITUATION usage")

    if missing:
        return Check(
            check_id="env-migration-gate",
            title="Env migration gate completed",
            severity="blocker",
            status="FAIL",
            detail="; ".join(missing),
            next_action="Switch scripts and vite.config.* to VITE_* runtime vars together before closing the migration.",
        )

    return Check(
        check_id="env-migration-gate",
        title="Env migration gate completed",
        severity="blocker",
        status="PASS",
        detail="No legacy VUE_APP_* or process.env.BASE_URL contract was detected, and scripts/config use VITE_* runtime vars.",
        next_action="None.",
    )


def check_deploy_env_contract(project_root: Path) -> Check:
    paths = [
        project_root / ".env.dev",
        project_root / ".env.prod",
        project_root / ".env.nesting",
        project_root / "deploy" / "products.js",
    ]
    missing_paths = [path.as_posix() for path in paths if not path.exists()]
    if missing_paths:
        return Check(
            check_id="deploy-env-contract",
            title="Deploy env contract uses neutral names",
            severity="warning",
            status="WARN",
            detail=f"Skipped some deploy env files: {', '.join(missing_paths)}",
            next_action="If the project has deploy-only env files, ensure they use neutral names such as SERVER_ID.",
        )

    legacy_matches = []
    for path in paths:
        text = safe_read(path)
        if "VUE_APP_SERVER_ID" in text:
            legacy_matches.append(path.relative_to(project_root).as_posix())

    if legacy_matches:
        return Check(
            check_id="deploy-env-contract",
            title="Deploy env contract uses neutral names",
            severity="blocker",
            status="FAIL",
            detail=f"Legacy deploy env key VUE_APP_SERVER_ID still exists in: {', '.join(legacy_matches)}",
            next_action="Rename deploy-only env keys to neutral names such as SERVER_ID and update deploy scripts accordingly.",
        )

    server_id_missing = []
    for path in paths[:-1]:
        if "SERVER_ID" not in safe_read(path):
            server_id_missing.append(path.relative_to(project_root).as_posix())
    if "envObj.SERVER_ID" not in safe_read(paths[-1]):
        server_id_missing.append(paths[-1].relative_to(project_root).as_posix())

    if server_id_missing:
        return Check(
            check_id="deploy-env-contract",
            title="Deploy env contract uses neutral names",
            severity="blocker",
            status="FAIL",
            detail=f"SERVER_ID contract not fully wired in: {', '.join(server_id_missing)}",
            next_action="Use SERVER_ID in deploy env files and read envObj.SERVER_ID in deploy/products.js.",
        )

    return Check(
        check_id="deploy-env-contract",
        title="Deploy env contract uses neutral names",
        severity="blocker",
        status="PASS",
        detail="Deploy-only env files and deploy/products.js use SERVER_ID.",
        next_action="None.",
    )


def summarize(checks: List[Check]) -> Dict[str, int]:
    fail = sum(1 for check in checks if check.status == "FAIL")
    warn = sum(1 for check in checks if check.status == "WARN")
    passed = sum(1 for check in checks if check.status == "PASS")
    blockers_failed = sum(1 for check in checks if check.status == "FAIL" and check.severity == "blocker")
    return {
        "total_checks": len(checks),
        "passed": passed,
        "warn": warn,
        "fail": fail,
        "blockers_failed": blockers_failed,
    }


def render(checks: List[Check], project_root: Path) -> str:
    summary = summarize(checks)
    lines: List[str] = []
    lines.append("# Migration State Verification")
    lines.append("")
    lines.append(f"- Project: `{project_root.as_posix()}`")
    lines.append(
        "- Summary: "
        f"`passed={summary['passed']}` "
        f"`warn={summary['warn']}` "
        f"`fail={summary['fail']}` "
        f"`blockers_failed={summary['blockers_failed']}`"
    )
    lines.append("")

    for check in checks:
        lines.append(f"## [{check.status}] {check.title}")
        lines.append(f"- id: `{check.check_id}`")
        lines.append(f"- severity: `{check.severity}`")
        lines.append(f"- detail: {check.detail}")
        lines.append(f"- next_action: {check.next_action}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise SystemExit(f"[ERROR] project root is not a directory: {project_root}")

    checks: List[Check] = []
    checks.append(check_vite_config(project_root))
    checks.append(check_index_entry(project_root))
    checks.append(check_package_scripts(project_root))
    checks.extend(check_legacy_files(project_root))
    checks.append(check_env_migration_gate(project_root))
    checks.append(check_deploy_env_contract(project_root))
    checks.append(check_module_federation(project_root))

    print(render(checks, project_root), end="")
    summary = summarize(checks)
    return 1 if summary["blockers_failed"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
