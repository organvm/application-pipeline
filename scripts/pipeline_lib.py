"""Shared utilities for the application pipeline scripts.

Consolidates load_entries, parse_date, format_amount, get_effort, get_score,
get_deadline, and common constants that were previously duplicated across
pipeline_status.py, standup.py, conversion_report.py, and score.py.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

import pipeline_entry_state as _entry_state
import pipeline_freshness as _pipeline_freshness
import yaml
from pipeline_market import build_market_intelligence_loader
from pipeline_market import http_request_with_retry as _http_request_with_retry

REPO_ROOT = Path(__file__).resolve().parent.parent

# Backward-compatible re-exports from extracted modules.
PRECISION_PIVOT_DATE = _pipeline_freshness.PRECISION_PIVOT_DATE
JOB_FRESH_HOURS = _pipeline_freshness.JOB_FRESH_HOURS
JOB_WARM_HOURS = _pipeline_freshness.JOB_WARM_HOURS
JOB_STALE_HOURS = _pipeline_freshness.JOB_STALE_HOURS
get_entry_era = _pipeline_freshness.get_entry_era
get_posting_age_hours = _pipeline_freshness.get_posting_age_hours
get_freshness_tier = _pipeline_freshness.get_freshness_tier
compute_freshness_score = _pipeline_freshness.compute_freshness_score
parse_date = _entry_state.parse_date
parse_datetime = _entry_state.parse_datetime
format_amount = _entry_state.format_amount
get_effort = _entry_state.get_effort
get_score = _entry_state.get_score
get_deadline = _entry_state.get_deadline
days_until = _entry_state.days_until
is_actionable = _entry_state.is_actionable
is_deferred = _entry_state.is_deferred
can_advance = _entry_state.can_advance

# ═══════════════════════════════════════════
# IDENTITY — single source of truth for all personal data
# ═══════════════════════════════════════════
IDENTITY_PATH = REPO_ROOT / "config" / "identity.yaml"
_identity_cache: dict | None = None


def load_identity() -> dict:
    """Load identity config. Cached after first call.

    Every script that needs personal data (name, email, phone, URLs, metrics,
    credentials, identity positions) MUST call this instead of hardcoding values.
    """
    global _identity_cache
    if _identity_cache is not None:
        return _identity_cache
    if IDENTITY_PATH.exists():
        _identity_cache = yaml.safe_load(IDENTITY_PATH.read_text())
    else:
        # Minimal fallback — should never happen in production
        _identity_cache = {
            "person": {"full_name": "Unknown", "email": "", "phone": ""},
            "links": {},
            "metrics": {},
            "identity_positions": {},
        }
    return _identity_cache


PIPELINE_DIR_ACTIVE = REPO_ROOT / "pipeline" / "active"
PIPELINE_DIR_SUBMITTED = REPO_ROOT / "pipeline" / "submitted"
PIPELINE_DIR_CLOSED = REPO_ROOT / "pipeline" / "closed"
PIPELINE_DIR_RESEARCH_POOL = REPO_ROOT / "pipeline" / "research_pool"

ALL_PIPELINE_DIRS = [PIPELINE_DIR_ACTIVE, PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED]

# Includes research pool — use when scripts need the full dataset (scoring, validation, analytics)
ALL_PIPELINE_DIRS_WITH_POOL = ALL_PIPELINE_DIRS + [PIPELINE_DIR_RESEARCH_POOL]

BLOCKS_DIR = REPO_ROOT / "blocks"
VARIANTS_DIR = REPO_ROOT / "materials" / "variants"
PROFILES_DIR = REPO_ROOT / "materials" / "targets" / "profiles"
DRAFTS_DIR = REPO_ROOT / "pipeline" / "archive" / "drafts"
SIGNALS_DIR = REPO_ROOT / "signals"
SUBMISSIONS_DIR = REPO_ROOT / "pipeline" / "submissions"
LEGACY_DIR = REPO_ROOT / "scripts" / "legacy-submission"
MATERIALS_DIR = REPO_ROOT / "materials"

(
    load_market_intelligence,
    get_portal_scores,
    get_strategic_base,
    PORTAL_SCORES_DEFAULT,
    STRATEGIC_BASE_DEFAULT,
) = build_market_intelligence_loader(REPO_ROOT)
http_request_with_retry = _http_request_with_retry


def _detect_current_batch() -> str:
    """Auto-detect the highest-numbered resume batch directory."""
    resumes_dir = MATERIALS_DIR / "resumes"
    if not resumes_dir.exists():
        return "batch-03"
    batches = sorted(
        (p for p in resumes_dir.iterdir() if p.is_dir() and p.name.startswith("batch-")),
        key=lambda p: int(p.name.removeprefix("batch-")) if p.name.removeprefix("batch-").isdigit() else 0,
    )
    return batches[-1].name if batches else "batch-03"


CURRENT_BATCH = _detect_current_batch()


def get_operator_name(default: str = "unknown") -> str:
    """Return the active human/operator identifier for audit trails."""
    return (
        os.environ.get("PIPELINE_OPERATOR")
        or os.environ.get("USER")
        or default
    )

# Maps entry IDs to profile file IDs where naming conventions differ.
PROFILE_ID_MAP = {
    "creative-capital-2027": "creative-capital",
    "doris-duke-amt": "doris-duke",
    "eyebeam-plurality": "eyebeam",
    "fire-island-residency": "fire-island",
    "google-creative-lab-five": "google-cl5",
    "google-creative-fellowship": "google-fellowship",
    "headlands-center": "headlands",
    "huggingface-dev-advocate": "huggingface",
    "mit-tr-wired-aeon": "mit-tech-review",
    "noema-magazine": "noema",
    "openai-se-evals": "openai-evals",
    "prix-ars-digital-humanity": "prix-ars",
    "prix-ars-electronica": "prix-ars",
    "rauschenberg-cycle-36": "rauschenberg-emergency",
}

# Maps legacy script filenames to entry IDs where naming conventions differ.
LEGACY_ID_MAP = {
    "cc-creative-capital": "creative-capital-2027",
    "doris-duke": "doris-duke-amt",
    "eyebeam": "eyebeam-plurality",
    "fire-island": "fire-island-residency",
    "google-cl5": "google-creative-lab-five",
    "google-fellowship": "google-creative-fellowship",
    "headlands": "headlands-center",
    "prix-ars-starts": "prix-ars-electronica",
    "rauschenberg-emergency": "rauschenberg-cycle-36",
}

VALID_TRACKS = {"grant", "residency", "job", "fellowship", "writing", "emergency", "prize", "program", "consulting", "academic"}
VALID_STATUSES = {"research", "qualified", "drafting", "staged", "deferred", "submitted", "acknowledged", "interview", "outcome", "withdrawn"}
ACTIONABLE_STATUSES = {"qualified", "drafting", "staged"}  # research is pre-pipeline (lives in research_pool/)

STATUS_ORDER = [
    "research", "qualified", "drafting", "staged", "deferred",
    "submitted", "acknowledged", "interview", "outcome", "withdrawn",
]

EFFORT_MINUTES = {
    "quick": 60,
    "standard": 180,
    "deep": 480,
    "complex": 720,
}

# Canonical scoring dimensions — single source of truth for score.py and validate.py.
# Core 9 dimensions (used across all pillars):
DIMENSION_ORDER = [
    "mission_alignment", "evidence_match", "track_record_fit",
    "network_proximity", "strategic_value", "financial_alignment",
    "effort_to_value", "deadline_feasibility", "portal_friction",
]
# Pillar-specific dimensions (added 2026-03-25 for three-pillar rubric):
PILLAR_DIMENSIONS = [
    "studio_alignment", "remote_flexibility",       # Pillar 1: Jobs
    "narrative_fit", "prestige_multiplier", "cycle_urgency",  # Pillar 2: Grants
    "recurring_potential", "client_fit",             # Pillar 3: Consulting
]
VALID_DIMENSIONS = set(DIMENSION_ORDER) | set(PILLAR_DIMENSIONS)

# Valid status transitions: each status maps to the set of statuses it can reach.
# Single source of truth — imported by validate.py and advance.py.
VALID_TRANSITIONS = {
    "research": {"qualified", "withdrawn"},
    "qualified": {"drafting", "staged", "deferred", "withdrawn"},
    "drafting": {"staged", "qualified", "deferred", "withdrawn"},
    "staged": {"submitted", "drafting", "deferred", "withdrawn"},
    "deferred": {"staged", "qualified", "drafting", "withdrawn"},
    "submitted": {"acknowledged", "interview", "outcome", "withdrawn"},
    "acknowledged": {"interview", "outcome", "withdrawn"},
    "interview": {"outcome", "withdrawn"},
    "outcome": set(),  # terminal
    "withdrawn": set(),  # terminal
}


# --- Safe YAML field mutation helpers ---


def update_yaml_field(
    content: str,
    field: str,
    new_value: str,
    *,
    nested: bool = False,
    parent_key: str | None = None,
) -> str:
    """Replace a scalar YAML field's value in raw text with verification.

    Uses targeted regex to preserve file formatting (comments, key order,
    quoting style) while validating the result is still parseable YAML.

    Args:
        content: Raw YAML text.
        field: Field name (e.g. "status", "score", "submitted").
        new_value: Replacement value string (caller handles quoting).
        nested: If True, field is expected to be indented under a parent key.
        parent_key: If provided, scope the replacement to within the parent key's
            block only — avoids ambiguous first-match when multiple blocks share
            a field name (e.g. `date` under `deadline` vs `timeline`).

    Returns:
        Modified YAML text.

    Raises:
        ValueError: If the field is not found or the result is invalid YAML.
    """
    if parent_key is not None:
        # Find the parent block, then scope the replacement within it.
        parent_pattern = re.compile(
            rf'^({re.escape(parent_key)}:\s*)$', re.MULTILINE
        )
        parent_match = parent_pattern.search(content)
        if not parent_match:
            raise ValueError(f"Parent key '{parent_key}' not found in YAML")
        start = parent_match.end()
        # Block ends at next top-level key (non-indented, non-blank line)
        end_match = re.search(r'^\S', content[start:], re.MULTILINE)
        block_end = start + end_match.start() if end_match else len(content)
        block = content[start:block_end]

        field_pattern = rf'^([ \t]+{re.escape(field)}:[ \t]+).*$'
        if not re.search(field_pattern, block, re.MULTILINE):
            raise ValueError(
                f"Field '{field}' not found under parent '{parent_key}'"
            )
        new_block = re.sub(
            field_pattern,
            lambda m: m.group(1) + new_value,
            block,
            count=1,
            flags=re.MULTILINE,
        )
        new_content = content[:start] + new_block + content[block_end:]
    elif nested:
        pattern = rf'^([ \t]+{re.escape(field)}:[ \t]+).*$'
        if not re.search(pattern, content, re.MULTILINE):
            raise ValueError(f"Field '{field}' not found in YAML (nested={nested})")
        new_content = re.sub(
            pattern,
            lambda m: m.group(1) + new_value,
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        pattern = rf'^({re.escape(field)}:[ \t]+).*$'
        if not re.search(pattern, content, re.MULTILINE):
            raise ValueError(f"Field '{field}' not found in YAML (nested={nested})")
        new_content = re.sub(
            pattern,
            lambda m: m.group(1) + new_value,
            content,
            count=1,
            flags=re.MULTILINE,
        )

    # Verify the result is still valid YAML
    try:
        yaml.safe_load(new_content)
    except yaml.YAMLError as e:
        raise ValueError(
            f"YAML became invalid after updating '{field}' to '{new_value}': {e}"
        )

    return new_content


def ensure_yaml_field(content: str, field: str, value: str) -> str:
    """Update a top-level field if it exists, or append it if missing."""
    if re.search(rf'^{re.escape(field)}:', content, re.MULTILINE):
        return update_yaml_field(content, field, value, nested=False)
    return content.rstrip() + f'\n{field}: {value}\n'


def update_last_touched(content: str) -> str:
    """Set last_touched to today's ISO date string."""
    today_str = date.today().isoformat()
    return ensure_yaml_field(content, "last_touched", f'"{today_str}"')


def load_entries(
    dirs: list[Path] | None = None,
    include_filepath: bool = False,
) -> list[dict]:
    """Load pipeline YAML entries from given directories.

    Args:
        dirs: Directories to scan. Defaults to all pipeline dirs.
        include_filepath: If True, adds _filepath key to each entry.

    Returns:
        List of parsed YAML dicts with _dir and _file metadata.
    """
    import sys as _sys

    entries = []
    for pipeline_dir in (dirs or ALL_PIPELINE_DIRS):
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue
            try:
                with open(filepath) as f:
                    data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"[WARN] Skipping unparseable entry: {filepath} ({e})", file=_sys.stderr)
                continue
            if isinstance(data, dict):
                data["_dir"] = pipeline_dir.name
                data["_file"] = filepath.name
                if include_filepath:
                    data["_filepath"] = filepath
                entries.append(data)
            else:
                print(f"[WARN] Skipping non-dict entry: {filepath}", file=_sys.stderr)
    return entries


def load_entry_by_id(entry_id: str) -> tuple[Path | None, dict | None]:
    """Load a single pipeline entry by ID. Returns (filepath, data) or (None, None)."""
    for pipeline_dir in ALL_PIPELINE_DIRS_WITH_POOL:
        filepath = pipeline_dir / f"{entry_id}.yaml"
        if filepath.exists():
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return filepath, data
    return None, None


def load_profile(target_id: str) -> dict | None:
    """Load a target profile JSON by ID, falling back to PROFILE_ID_MAP."""
    filepath = PROFILES_DIR / f"{target_id}.json"
    if not filepath.exists():
        mapped = PROFILE_ID_MAP.get(target_id)
        if mapped:
            filepath = PROFILES_DIR / f"{mapped}.json"
    if filepath.exists():
        return json.loads(filepath.read_text())
    return None


def _build_reverse_legacy_map() -> dict[str, str]:
    """Build entry_id → legacy_filename map from LEGACY_ID_MAP."""
    reverse = {}
    for legacy_name, entry_id in LEGACY_ID_MAP.items():
        reverse[entry_id] = legacy_name
    return reverse


_REVERSE_LEGACY_MAP = _build_reverse_legacy_map()


def load_legacy_script(target_id: str) -> dict | None:
    """Load and parse a legacy submission script into field sections.

    Returns a dict mapping canonical field names to paste-ready content,
    or None if no legacy script exists.
    """
    # Try direct match first, then reverse legacy map
    filepath = LEGACY_DIR / f"{target_id}.md"
    if not filepath.exists():
        legacy_name = _REVERSE_LEGACY_MAP.get(target_id)
        if legacy_name:
            filepath = LEGACY_DIR / f"{legacy_name}.md"
    if not filepath.exists():
        return None

    return _parse_legacy_markdown(filepath.read_text())


# Map legacy section headers to canonical field names
_LEGACY_SECTION_MAP = {
    "artist statement": "artist_statement",
    "artistic statement": "artist_statement",
    "bio": "bio",
    "bio / cv summary": "bio",
    "bio/cv summary": "bio",
    "cv summary": "bio",
    "project description": "project_description",
    "project description / why this opportunity": "project_description",
    "project summary / abstract": "project_description",
    "project summary": "project_description",
    "project title": "project_title",
    "project narrative": "project_description",
    "proposal narrative": "project_description",
    "cover letter": "cover_letter",
    "work samples": "work_samples",
    "work samples — descriptions": "work_samples",
    "links to submit": "links",
    "performing arts connection statement": "performing_arts_connection",
    "financial hardship statement": "financial_hardship",
    "documentation of need": "documentation_of_need",
    "budget": "budget",
    "budget outline": "budget",
    "methodology": "methodology",
    "technical plan": "technical_plan",
}


def _parse_legacy_markdown(text: str) -> dict:
    """Parse a legacy submission script markdown into sections.

    Extracts content from between --- delimiters within each ## section.
    Falls back to raw section content if no delimiters found.
    """
    sections = {}
    current_header = None
    current_lines = []

    for line in text.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_header is not None:
                content = _extract_section_content("\n".join(current_lines))
                if content:
                    sections[current_header] = content

            header_text = line[3:].strip()
            # Map to canonical name
            header_lower = header_text.lower()
            current_header = _LEGACY_SECTION_MAP.get(header_lower, header_lower)
            current_lines = []
        elif current_header is not None:
            current_lines.append(line)

    # Save last section
    if current_header is not None:
        content = _extract_section_content("\n".join(current_lines))
        if content:
            sections[current_header] = content

    # Skip non-content sections
    for skip in ("pre-flight (2 minutes)", "pre-flight (3 minutes)",
                 "pre-flight (5 minutes)", "post-submission checklist",
                 "if something goes wrong", "fit assessment — 7/10",
                 "fit assessment"):
        sections.pop(skip, None)

    return sections


def _extract_section_content(text: str) -> str | None:
    """Extract paste-ready content from between --- delimiters.

    If delimiters found, extracts content between them (skipping metadata).
    If no delimiters, returns the full text stripped of metadata lines.
    """
    parts = text.split("---")

    # If we have delimiter-separated parts, look for the substantive one
    # Skip the first part (usually metadata like word counts) and empty parts
    if len(parts) >= 3:
        # Try parts between delimiters (index 1, 3, 5...)
        for i in range(1, len(parts)):
            stripped = parts[i].strip()
            if not stripped:
                continue
            lines = stripped.split("\n")
            non_meta = [
                l for l in lines
                if l.strip()
                and not l.strip().startswith("**")
                and not l.strip().startswith(">")
                and not l.strip().startswith("- [ ]")
                and not l.strip().startswith("Copy")
            ]
            if non_meta:
                result = "\n".join(non_meta).strip()
                if result:
                    return result

    # Fallback: no delimiters or nothing found between them
    lines = text.strip().split("\n")
    non_meta = [
        l for l in lines
        if l.strip()
        and not l.strip().startswith("**")
        and not l.strip().startswith(">")
        and not l.strip().startswith("- [ ]")
        and not l.strip().startswith("Copy")
        and l.strip() != "---"
    ]
    if non_meta:
        result = "\n".join(non_meta).strip()
        if len(result) > 10:
            return result

    return None


# --- Block/variant loading (shared by compose.py, submit.py, draft.py) ---


def load_block(block_path: str) -> str | None:
    """Load a block file by its reference path relative to BLOCKS_DIR."""
    full_path = (BLOCKS_DIR / block_path).resolve()
    if not full_path.is_relative_to(BLOCKS_DIR.resolve()):
        return None
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text().strip()
    return None


def load_block_index() -> dict:
    """Load the block index from blocks/_index.yaml.

    Returns the full index dict with 'blocks' and 'tag_index' keys.
    Returns an empty dict if the index file doesn't exist.
    """
    import sys as _sys

    index_path = BLOCKS_DIR / "_index.yaml"
    if not index_path.exists():
        print("[WARN] blocks/_index.yaml not found — run build_block_index.py", file=_sys.stderr)
        return {}
    return yaml.safe_load(index_path.read_text()) or {}


def load_block_frontmatter(block_path: str) -> dict | None:
    """Parse YAML frontmatter from a single block file.

    Args:
        block_path: Path relative to BLOCKS_DIR (e.g. 'methodology/ai-conductor')

    Returns the frontmatter dict, or None if not found.
    """
    full_path = BLOCKS_DIR / block_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if not full_path.exists():
        return None
    text = full_path.read_text()
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None


def load_variant(variant_path: str) -> str | None:
    """Load a variant file by its reference path relative to VARIANTS_DIR."""
    full_path = (VARIANTS_DIR / variant_path).resolve()
    if not full_path.is_relative_to(VARIANTS_DIR.resolve()):
        return None
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text().strip()
    return None


# --- Text utilities (shared by compose.py, draft.py) ---


def strip_markdown(text: str) -> str:
    """Strip markdown formatting for plain text output."""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def count_words(text: str) -> int:
    """Count words in a text string."""
    return len(text.split())


def count_chars(text: str) -> int:
    """Count characters (excluding leading/trailing whitespace)."""
    return len(text.strip())


# --- Portal URL detection ---


PORTAL_URL_PATTERNS = [
    (re.compile(r'(?:job-)?boards(?:-api)?\.greenhouse\.io'), 'greenhouse'),
    (re.compile(r'jobs\.(?:eu\.)?lever\.co'), 'lever'),
    (re.compile(r'jobs\.ashbyhq\.com'), 'ashby'),
    (re.compile(r'apply\.workable\.com'), 'workable'),
    (re.compile(r'jobs\.smartrecruiters\.com'), 'smartrecruiters'),
    (re.compile(r'\.submittable\.com'), 'submittable'),
    (re.compile(r'slideroom\.com'), 'slideroom'),
]


def detect_portal(url: str) -> str | None:
    """Detect the portal type from an application URL.

    Returns the portal name string or None if no pattern matches.
    """
    if not url:
        return None
    for pattern, portal in PORTAL_URL_PATTERNS:
        if pattern.search(url):
            return portal
    return None


# --- Submit config ---

SUBMIT_CONFIG_PATH = Path(__file__).resolve().parent / ".submit-config.yaml"


def detect_entry_portal(entry: dict) -> str:
    """Detect portal type from entry fields (dict-level wrapper).

    Checks target.portal first, then falls back to URL-based detection.
    """
    portal = (entry.get("target") or {}).get("portal", "")
    if portal:
        return portal
    app_url = (entry.get("target") or {}).get("application_url", "")
    return detect_portal(app_url) or "unknown"


def load_submit_config(*, strict: bool = True) -> dict:
    """Load personal info from .submit-config.yaml.

    Args:
        strict: If True (default), exit on missing file or unfilled fields.
                If False, return {} on missing file (for non-submission use).
    """
    if not SUBMIT_CONFIG_PATH.exists():
        if not strict:
            return {}
        import sys
        print(f"Error: Config file not found: {SUBMIT_CONFIG_PATH}", file=sys.stderr)
        print("Create it with first_name, last_name, email, phone fields.", file=sys.stderr)
        sys.exit(1)
    # Warn if credentials file is readable by group/others
    try:
        mode = SUBMIT_CONFIG_PATH.stat().st_mode
        if mode & 0o077:
            import sys
            print(f"WARNING: {SUBMIT_CONFIG_PATH.name} is readable by others (mode {oct(mode)})",
                  file=sys.stderr)
            print("  Fix with: chmod 600 " + str(SUBMIT_CONFIG_PATH), file=sys.stderr)
    except OSError:
        pass
    config = yaml.safe_load(SUBMIT_CONFIG_PATH.read_text())
    if not isinstance(config, dict):
        if not strict:
            return {}
        import sys
        print("Error: Config file is not a valid YAML dict.", file=sys.stderr)
        sys.exit(1)
    if strict:
        import sys
        for field in ("first_name", "last_name", "email"):
            val = config.get(field, "")
            if not val or "FILL_IN" in str(val):
                print(f"Error: Fill in '{field}' in {SUBMIT_CONFIG_PATH}", file=sys.stderr)
                sys.exit(1)
    return config


# --- Material resolution ---


def resolve_cover_letter(entry: dict, *, strip_md: bool = True) -> str | None:
    """Resolve cover letter content from variant file.

    Strips YAML frontmatter (always). If strip_md=True (default), also
    strips markdown formatting for plain-text ATS submission.
    If strip_md=False, returns markdown body (for AI prompting / templating).
    """
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return None
    variant_ids = submission.get("variant_ids", {})
    if not isinstance(variant_ids, dict):
        return None
    cl_ref = variant_ids.get("cover_letter")
    if not cl_ref:
        return None
    variant_path = VARIANTS_DIR / cl_ref
    if not variant_path.suffix:
        variant_path = variant_path.with_suffix(".md")
    if not variant_path.exists():
        return None
    raw = variant_path.read_text().strip()
    # Strip YAML frontmatter
    lines = raw.split("\n")
    body_start = 0
    found_separator = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if found_separator:
                body_start = i + 1
                break
            found_separator = True
    body = "\n".join(lines[body_start:]).strip()
    if strip_md:
        return strip_markdown(body)
    return body


def resolve_resume(entry: dict) -> Path | None:
    """Find the resume PDF from materials_attached."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return None
    materials = submission.get("materials_attached", [])
    if not isinstance(materials, list):
        return None
    for m in materials:
        mat_path = MATERIALS_DIR / m
        if mat_path.exists() and mat_path.suffix.lower() == ".pdf":
            return mat_path
    # Fallback: look for sibling .pdf next to any .html resume reference
    for m in materials:
        mat_path = MATERIALS_DIR / m
        if mat_path.suffix.lower() == ".html":
            pdf_sibling = mat_path.with_suffix(".pdf")
            if pdf_sibling.exists():
                return pdf_sibling
    return None


# --- Tier priority ---

TIER_PRIORITY = {
    "job-tier-1": 1,
    "job-tier-2": 2,
    "job-tier-3": 3,
    "job-tier-4": 4,
}


def get_tier(entry: dict) -> int:
    """Get tier priority from tags (lower = higher priority)."""
    tags = entry.get("tags", []) or []
    for tag in tags:
        if tag in TIER_PRIORITY:
            return TIER_PRIORITY[tag]
    return 5  # default: untiered


# --- Block stats formatting ---

NOISE_LANGS = {"markdown", "shell", "yaml", "jekyll"}


def format_block_stats(block_path: str) -> str | None:
    """Extract Key Stats line from block frontmatter, if available."""
    fm = load_block_frontmatter(block_path)
    if not fm:
        return None
    stats = fm.get("stats", {})
    if not stats:
        return None
    parts = []
    if stats.get("languages"):
        langs = stats["languages"]
        if isinstance(langs, list):
            useful = [lang for lang in langs if lang not in NOISE_LANGS]
        else:
            useful = [langs] if langs not in NOISE_LANGS else []
        if useful:
            parts.append(f"Languages: {', '.join(useful)}")
    if stats.get("test_count"):
        parts.append(f"Tests: {stats['test_count']}")
    if stats.get("coverage"):
        parts.append(f"Coverage: {stats['coverage']}%")
    if parts:
        return f"**Key Stats:** {' | '.join(parts)}"
    return None


# HTTP and market-intelligence helpers are imported from pipeline_market.py.


# --- Pipeline mode functions ---

_MODE_THRESHOLDS_DEFAULT = {
    "precision": {"auto_qualify_min": 7.0, "max_active": 10, "max_weekly_submissions": 2, "stale_days": 14, "stagnant_days": 30},
    "volume": {"auto_qualify_min": 7.0, "max_active": 30, "max_weekly_submissions": 10, "stale_days": 7, "stagnant_days": 14},
    "hybrid": {"auto_qualify_min": 8.0, "max_active": 15, "max_weekly_submissions": 5, "stale_days": 10, "stagnant_days": 21},
}


def get_pipeline_mode() -> str:
    """Return current pipeline mode from market intelligence (precision/volume/hybrid)."""
    intel = load_market_intelligence()
    strategy = intel.get("precision_strategy", {})
    return strategy.get("mode", "precision")


def get_mode_thresholds() -> dict:
    """Return thresholds for the current pipeline mode."""
    intel = load_market_intelligence()
    strategy = intel.get("precision_strategy", {})
    custom = strategy.get("mode_thresholds", {})
    mode = strategy.get("mode", "precision")
    if custom and mode in custom:
        return custom[mode]
    return _MODE_THRESHOLDS_DEFAULT.get(mode, _MODE_THRESHOLDS_DEFAULT["precision"])


def get_mode_review_status() -> dict:
    """Return review status for the precision pivot."""
    from datetime import date as _date
    intel = load_market_intelligence()
    strategy = intel.get("precision_strategy", {})
    review_str = strategy.get("review_date", "2026-04-04")
    today = _date.today()
    try:
        review_date = _date.fromisoformat(review_str)
    except (ValueError, TypeError):
        review_date = _date(2026, 4, 4)
    days_until_review = (review_date - today).days
    return {
        "review_date": review_str,
        "days_until_review": days_until_review,
        "past_review": days_until_review < 0,
        "mode": get_pipeline_mode(),
        "revert_trigger": strategy.get("revert_trigger", "0 interviews by review_date"),
    }


COMPANY_CAP = 1  # Max active+submitted entries per organization (precision mode)


def company_entry_counts(entries: list[dict], actionable_only: bool = True) -> dict[str, int]:
    """Count entries per organization. If actionable_only, exclude closed/expired/withdrawn."""
    counts: dict[str, int] = {}
    for entry in entries:
        org = (entry.get("target") or {}).get("organization", "Unknown")
        if actionable_only:
            status = entry.get("status", "")
            if status in ("closed", "expired", "withdrawn", "rejected"):
                continue
        counts[org] = counts.get(org, 0) + 1
    return counts


def check_company_cap(org: str, entries: list[dict], cap: int = COMPANY_CAP) -> tuple[bool, int]:
    """Check if an organization is under the cap. Returns (allowed, current_count).

    Only counts entries in active pursuit statuses — research and deferred
    entries don't count toward the cap since they're not consuming effort.
    """
    # Statuses that represent active pursuit of the org
    _CAP_STATUSES = {"qualified", "drafting", "staged", "submitted", "acknowledged", "interview"}
    count = 0
    for entry in entries:
        entry_org = (entry.get("target") or {}).get("organization", "")
        entry_status = entry.get("status", "")
        if entry_org == org and entry_status in _CAP_STATUSES:
            count += 1
    return count < cap, count


def atomic_write(filepath: Path, content: str) -> None:
    """Write content to a file atomically via temp-file-then-rename.

    Prevents data loss from crashes mid-write by writing to a temporary file
    in the same directory first, then atomically renaming.
    """
    import tempfile

    parent = filepath.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp", prefix=f".{filepath.name}.")
    try:
        with open(fd, "w") as f:
            f.write(content)
        Path(tmp_path).replace(filepath)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


# STATE MACHINE QUERY FUNCTIONS are imported from pipeline_entry_state.py.
