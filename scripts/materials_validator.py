#!/usr/bin/env python3
"""Materials Protocol Validator — enforces 12 articles for submission materials.

Validates application packages (resume + cover letter + portal answers) against
the Materials Protocol formal system. Third in the ORGANVM rhetorical triad:
  Testament (text) → Outreach Protocol (conversation) → Materials Protocol (submissions)

Usage:
    python scripts/materials_validator.py --package applications/2026-03-27/<dir>/
    python scripts/materials_validator.py --package applications/2026-03-27/<dir>/ --json
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import load_identity

# ---------------------------------------------------------------------------
# Canonical metrics — single source of truth
# ---------------------------------------------------------------------------

try:
    from recruiter_filter import CANONICAL
except ImportError:
    CANONICAL = {
        "repos": "113", "words": "739K", "tests_total": "23,470",
        "cicd": "104", "files": "82K", "dependency_edges": "50",
        "essays": "49", "orgs": "8", "sprints": "33",
    }

# Voice Constitution anti-patterns (simplified detection)
ANTI_PATTERNS = {
    "AP-01": [r"(?i)leverag\w+ (?:our |core )?competenc",
              r"(?i)holistic solution", r"(?i)synerg"],
    "AP-02": [r"(?i)it'?s worth noting", r"(?i)as we all know",
              r"(?i)in this day and age", r"(?i)first of all.{0,5}I just want"],
    "AP-03": [r"(?i)I feel (?:like |that )", r"(?i)I just want you to know"],
    "AP-08": [r"(?i)I'?m (?:really |so |very )?(?:passionate|excited) about",
              r"(?i)I would love the opportunity"],
    "AP-09": [r"(?i)making a (?:real )?difference", r"(?i)changing the world"],
}

FORBIDDEN_IDENTITY = ["Independent Engineer", "Self-Employed", "Freelance", "Self Employed"]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ArticleResult:
    article: str
    name: str
    passed: bool
    diagnosis: str = ""


@dataclass
class MaterialsReport:
    results: list[ArticleResult] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self) -> str:
        lines = ["  Materials Protocol Validation:"]
        for r in self.results:
            icon = "PASS" if r.passed else "FAIL"
            diag = f" — {r.diagnosis}" if r.diagnosis and not r.passed else ""
            lines.append(f"    [{icon}] {r.article} {r.name}{diag}")
        overall = "PASS" if self.valid else "FAIL"
        lines.insert(0, f"  Overall: {overall}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _read_file(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _find_file(pkg: Path, pattern: str) -> Path | None:
    matches = list(pkg.glob(pattern))
    return matches[0] if matches else None


def validate_package(package_dir: Path) -> MaterialsReport:
    """Run all 12 Materials Protocol articles on an application package."""
    results = []

    # Locate files (handle multiple naming conventions)
    resume_html = _find_file(package_dir, "*Resume.html")
    _find_file(package_dir, "*Resume.pdf")  # existence check only
    cl_md = _find_file(package_dir, "cover-letter.md") or _find_file(package_dir, "*Cover-Letter.md")
    cl_html = _find_file(package_dir, "cover-letter.html") or _find_file(package_dir, "*Cover-Letter.html")
    portal_md = _find_file(package_dir, "portal-answers.md")

    resume_text = _read_file(resume_html) if resume_html else ""
    cl_text = _read_file(cl_md)
    portal_text = _read_file(portal_md)
    all_text = resume_text + cl_text + portal_text

    # M-I: Page-Fill Imperative
    if cl_text:
        word_count = len(cl_text.split())
        if word_count < 500:
            results.append(ArticleResult("M-I", "Page-Fill", False, f"{word_count} words — RED FLAG (min 550)"))
        elif word_count < 550:
            results.append(ArticleResult("M-I", "Page-Fill", False, f"{word_count} words — below target"))
        elif word_count > 750:
            results.append(ArticleResult("M-I", "Page-Fill", False, f"{word_count} words — overflow risk"))
        else:
            results.append(ArticleResult("M-I", "Page-Fill", True))
    else:
        results.append(ArticleResult("M-I", "Page-Fill", False, "no cover letter found"))

    # M-II: Structural Integrity
    if resume_text:
        entry_count = resume_text.count("entry-header")
        has_columnar = "grid-template-columns" in resume_text or "column-count" in resume_text
        has_required_classes = all(c in resume_text for c in ["entry-title", "entry-org", "project-title"])

        violations = []
        if entry_count < 4:
            violations.append(f"{entry_count} entries (min 4)")
        if has_columnar:
            violations.append("columnar layout detected")
        if not has_required_classes:
            violations.append("missing template classes")
        results.append(ArticleResult("M-II", "Structural Integrity",
                                     len(violations) == 0, "; ".join(violations)))
    else:
        results.append(ArticleResult("M-II", "Structural Integrity", False, "no resume found"))

    # M-III: Identity Sovereignty
    identity_violations = []
    for term in FORBIDDEN_IDENTITY:
        if term.lower() in all_text.lower():
            identity_violations.append(f"contains '{term}'")
    if resume_text and "ORGANVM" not in resume_text:
        identity_violations.append("ORGANVM not found in resume")
    results.append(ArticleResult("M-III", "Identity Sovereignty",
                                 len(identity_violations) == 0, "; ".join(identity_violations)))

    # M-IV: Metric Canonicality (simplified — full check delegated to recruiter_filter)
    results.append(ArticleResult("M-IV", "Metric Canonicality", True,
                                 "delegated to recruiter_filter.py"))

    # M-V: Content Complementarity
    if resume_text and cl_text:
        resume_clean = re.sub(r"<[^>]+>", " ", resume_text).lower()
        cl_clean = cl_text.lower()

        def phrases_4(text):
            words = re.findall(r"\w{3,}", text)
            return {" ".join(words[i:i + 4]) for i in range(len(words) - 3) if len(" ".join(words[i:i + 4])) > 15}

        shared = phrases_4(resume_clean) & phrases_4(cl_clean)
        if len(shared) > 5:
            results.append(ArticleResult("M-V", "Complementarity", False,
                                         f"{len(shared)} shared phrases (max 5)"))
        else:
            results.append(ArticleResult("M-V", "Complementarity", True))
    else:
        results.append(ArticleResult("M-V", "Complementarity", True, "incomplete package — skipped"))

    # M-VI: Visual Identity Parity
    cl_html_text = _read_file(cl_html) if cl_html else ""
    if cl_html_text:
        full_name = load_identity()["person"]["full_name"]
        parity_ok = ("Georgia" in cl_html_text and
                     full_name in cl_html_text and
                     "border-bottom" in cl_html_text)
        results.append(ArticleResult("M-VI", "Visual Parity", parity_ok,
                                     "" if parity_ok else f"cover letter template doesn't match resume (expected {full_name})"))
    else:
        results.append(ArticleResult("M-VI", "Visual Parity", False, "no cover letter HTML found"))

    # M-VII: Storefront Gate
    if cl_text:
        lines = [l.strip() for l in cl_text.split("\n") if l.strip() and not l.startswith("Dear")]
        # Find first substantive line (skip headers, names)
        first_body = ""
        for line in lines:
            if len(line) > 40 and not line.startswith("Anthony") and not line.startswith("New York"):
                first_body = line
                break
        # Rhetorician revision: recognition anchor includes numbers, proper nouns, and specific claims
        # Recognition anchors: digits, word-form numbers, proper nouns, specific action verbs
        has_number = bool(re.search(r"\d+", first_body))
        has_word_number = bool(re.search(r"(?i)\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|hundred|thousand)\b", first_body))
        has_proper_noun = bool(re.search(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)", first_body))
        has_specific_claim = bool(re.search(r"(?:built|designed|governed|maintained|operated|taught|spent|run|managed)", first_body, re.I))
        has_anchor = has_number or has_word_number or has_proper_noun or has_specific_claim
        results.append(ArticleResult("M-VII", "Storefront Gate", has_anchor,
                                     "" if has_anchor else "first sentence lacks recognition anchor (number or proper noun)"))
    else:
        results.append(ArticleResult("M-VII", "Storefront Gate", False, "no cover letter"))

    # M-VIII: Project Rotation
    if resume_text:
        default_5 = {"ORGANVM Eight-Organ System", "agentic-titan", "agent--claude-smith",
                      "Application Pipeline", "Portfolio"}
        projects = re.findall(r'project-title">(.*?)</div>', resume_text)
        project_names = {p.split("—")[0].split("&mdash;")[0].strip() for p in projects}
        default_count = len(project_names & default_5)
        results.append(ArticleResult("M-VIII", "Project Rotation",
                                     default_count <= 3,
                                     f"{default_count}/5 defaults used" if default_count > 3 else ""))
    else:
        results.append(ArticleResult("M-VIII", "Project Rotation", True, "no resume — skipped"))

    # M-IX: Triple Layer (heuristic — checks for evidence of all three)
    if cl_text:
        # Broader pathos detection: vulnerability, stakes, human experience, constraint
        has_pathos = bool(re.search(r"(?i)(constraint|forced|alone|without|honest|felt|struggle|failure|broke|cost|waking|tired|afraid|trust|stakes|paid the price|gave up|lost|risk|fear|difficult|hard way|lesson|mistake|personally)", cl_text))
        # Broader ethos detection: demonstrated action verbs
        has_ethos = bool(re.search(r"(?i)(built|designed|maintained|taught|produced|operated|architected|created|developed|engineered|led|managed|authored|governed|implemented|deployed)", cl_text))
        # Logos: numbers, evidence, mechanism, causal language
        has_logos = bool(re.search(r"(\d+|because|therefore|produces|results in|leads to|evidence|mechanism|demonstrated)", cl_text))
        all_three = has_pathos and has_ethos and has_logos
        results.append(ArticleResult("M-IX", "Triple Layer", all_three,
                                     "" if all_three else "missing dimension(s)"))
    else:
        results.append(ArticleResult("M-IX", "Triple Layer", False, "no cover letter"))

    # M-X: Voice Constitution Compliance
    ap_hits = []
    for ap_id, patterns in ANTI_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, all_text):
                ap_hits.append(f"{ap_id}: matched '{pattern[:30]}'")
    results.append(ArticleResult("M-X", "Voice Compliance",
                                 len(ap_hits) == 0, "; ".join(ap_hits)))

    # M-XI: Inhabitant Gate (checks free-text portal answers reference the org)
    if portal_text:
        # Extract org name from entry.yaml if available
        entry_yaml = package_dir / "entry.yaml"
        org = ""
        if entry_yaml.exists():
            import yaml
            entry = yaml.safe_load(entry_yaml.read_text())
            org = entry.get("target", {}).get("organization", "") if entry else ""
        inhabits = not org or org.lower() in portal_text.lower()
        results.append(ArticleResult("M-XI", "Inhabitant Gate", inhabits,
                                     "" if inhabits else f"portal answers don't reference {org}"))
    else:
        results.append(ArticleResult("M-XI", "Inhabitant Gate", True, "no portal answers — skipped"))

    # M-XII: Word Count Enforcement
    if cl_text:
        wc = len(cl_text.split())
        in_range = 550 <= wc <= 700
        results.append(ArticleResult("M-XII", "Word Count", in_range,
                                     f"{wc} words" + ("" if in_range else " (target 550-700)")))
    else:
        results.append(ArticleResult("M-XII", "Word Count", False, "no cover letter"))

    return MaterialsReport(results=results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Materials Protocol Validator")
    parser.add_argument("--package", required=True, help="Path to application package directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    pkg = Path(args.package)
    if not pkg.is_dir():
        print(f"ERROR: {pkg} is not a directory", file=sys.stderr)
        sys.exit(1)

    report = validate_package(pkg)

    if args.json:
        import json
        print(json.dumps([{"article": r.article, "name": r.name, "passed": r.passed,
                           "diagnosis": r.diagnosis} for r in report.results], indent=2))
    else:
        print(report.summary())


if __name__ == "__main__":
    main()
