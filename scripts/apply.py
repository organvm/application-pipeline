#!/usr/bin/env python3
"""apply.py — Single-command application pipeline.

Produces a complete, correct application package for a pipeline entry:
1. Loads entry YAML
2. Runs Level 1 standards audit (Course Regulator — entry-level quality gate)
3. Fetches ACTUAL portal questions from Greenhouse API
4. Auto-fills standard answers, generates role-specific answers
5. Resolves or generates cover letter (unique from resume)
6. Composes Protocol-validated outreach DM for contacts at the org
7. Checks cover letter vs resume overlap
8. Builds cover letter PDF (Chrome headless)
9. Copies resume PDF
10. Creates application directory with all files
11. Validates completeness — all gates must pass
12. Prints portal URL + outreach DM

Usage:
    python scripts/apply.py --target <entry-id>
    python scripts/apply.py --target <entry-id> --dry-run
    python scripts/apply.py --batch  # all staged entries
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from greenhouse_submit import fetch_job_questions, get_custom_questions
from pipeline_lib import (
    MATERIALS_DIR,
    PIPELINE_DIR_ACTIVE,
    REPO_ROOT,
    SIGNALS_DIR,
    load_entry_by_id,
    load_submit_config,
    resolve_cover_letter,
)


def _load_standards_board():
    """Lazy-load StandardsBoard to avoid circular imports."""
    try:
        from standards import StandardsBoard
        return StandardsBoard()
    except Exception:
        return None


def _load_contacts_for_org(org: str) -> list[dict]:
    """Load contacts from contacts.yaml for a given organization."""
    contacts_path = SIGNALS_DIR / "contacts.yaml"
    if not contacts_path.exists():
        return []
    data = yaml.safe_load(contacts_path.read_text())
    contacts = data.get("contacts", data) if isinstance(data, dict) else data
    if not isinstance(contacts, list):
        return []
    return [c for c in contacts if c.get("organization", "").lower() == org.lower()]

APPLICATIONS_DIR = REPO_ROOT / "applications"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Standard answers — single source of truth
STANDARD_ANSWERS = {
    "first_name": "Anthony",
    "last_name": "Padavano",
    "preferred_first_name": "Anthony",
    "preferred_last_name": "Padavano",
    "email": None,  # loaded from .submit-config.yaml
    "phone": None,  # loaded from .submit-config.yaml
    "linkedin": "https://www.linkedin.com/in/anthonyjamespadavano",
    "website": "https://4444j99.github.io/portfolio/",
    "location": "New York, NY",
    "country": "United States",
    "timezone": "Eastern (ET)",
    "work_authorized": "Yes",
    "sponsorship_needed": "No",
    "how_heard": "LinkedIn",
    "open_to_relocation": "Yes",
    "us_citizen": True,
    "previously_employed": "No",
    "sanctions_clear": True,
}


def _load_personal_info() -> dict:
    """Load personal info from .submit-config.yaml."""
    config = load_submit_config(strict=False)
    answers = dict(STANDARD_ANSWERS)
    if config:
        answers["email"] = config.get("email", "")
        answers["phone"] = config.get("phone", "")
        answers["first_name"] = config.get("first_name", answers["first_name"])
        answers["last_name"] = config.get("last_name", answers["last_name"])
    return answers


def _extract_board_and_job(entry: dict) -> tuple[str, str] | None:
    """Extract Greenhouse board token and job ID from application URL."""
    url = entry.get("target", {}).get("application_url", "")
    # Pattern: boards.greenhouse.io/{board}/jobs/{id} or ?gh_jid={id}
    m = re.search(r"greenhouse\.io/(\w+)/jobs/(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    # Pattern: ?gh_jid=XXXX with board in URL path
    m = re.search(r"gh_jid=(\d+)", url)
    if m:
        job_id = m.group(1)
        # Try to extract board from URL
        board_m = re.search(r"greenhouse\.io/(\w+)", url)
        if board_m:
            return board_m.group(1), job_id
        # Try org name as board
        org = entry.get("target", {}).get("organization", "").lower().replace(" ", "")
        return org, job_id
    return None


def _answer_question(question: dict, entry: dict, personal: dict) -> str:
    """Generate the correct answer for a portal question."""
    label = (question.get("label") or "").strip().lower()
    fields = question.get("fields", [])
    field_type = fields[0].get("type", "text") if fields else "text"
    values = []
    for f in fields:
        for v in f.get("values", []):
            values.append(v.get("label", ""))

    # Standard field matching
    if "first name" in label and "preferred" not in label:
        return personal["first_name"]
    if "last name" in label and "preferred" not in label:
        return personal["last_name"]
    if "preferred first" in label:
        return personal["preferred_first_name"]
    if "preferred last" in label:
        return personal["preferred_last_name"]
    if "email" in label:
        return personal.get("email", "")
    if "phone" in label:
        return personal.get("phone", "")
    if "linkedin" in label:
        return personal["linkedin"]
    if "website" in label:
        return personal["website"]
    if "country" in label and "time zone" in label:
        return f"{personal['country']}, {personal['timezone']}"
    if "how did you hear" in label:
        if values and "LinkedIn" in values:
            return "LinkedIn"
        return personal["how_heard"]
    if "authorized" in label or "authorization" in label:
        return "Yes"
    if "sponsorship" in label:
        return "No"
    if "relocat" in label:
        return personal["open_to_relocation"]

    # Clearance / export controls
    if "clearance" in label and "eligib" in label:
        if values:
            for v in values:
                if "eligible" in v.lower():
                    return v
        return "Yes, I am eligible for a U.S. security clearance"
    if "clearance" in label and "held" in label:
        return "N/A - have never held U.S. security clearance"
    if "export control" in label or "united states citizen" in label.lower():
        if values:
            for v in values:
                if "citizen" in v.lower() and "united states" in v.lower():
                    return v
            for v in values:
                if "citizen" in v.lower():
                    return v
        return "A United States citizen"
    if "sanctions" in label or "cuba" in label or "iran" in label:
        if values:
            for v in values:
                if "none" in v.lower():
                    return v
        return "None of the above"
    if "previously" in label or "employed by" in label or "worked for" in label:
        return "No"
    if "conflict of interest" in label:
        return "No"
    if "history with" in label:
        return "No"
    if "human being" in label:
        return "I am a human being"
    if "acknowledge" in label or "consent" in label or "confirm" in label:
        if values:
            for v in values:
                if "acknowledge" in v.lower() or "agree" in v.lower():
                    return v
        return "Acknowledge"

    # Yes/No qualification questions — answer based on content, NOT blanket "Yes"
    if field_type == "multi_value_single_select" and values == ["Yes", "No"]:
        q_text = label
        # Positive qualification: authorized, eligible, open to, willing, comfortable
        if any(kw in q_text for kw in [
            "authorized", "eligible", "open to", "willing", "comfortable",
            "acknowledge", "consent", "agree", "confirm",
        ]):
            return "Yes"
        # Negative qualification: require sponsorship, previously employed, interviewed before
        if any(kw in q_text for kw in [
            "sponsorship", "previously", "interviewed", "employed by",
            "worked for", "conflict", "history with",
        ]):
            return "No"
        # Unknown — leave blank for human review rather than guessing
        return ""

    # Free text fields — this is the opportunity for unique content
    if field_type in ("input_text", "textarea") and not any(
        kw in label for kw in ["name", "email", "phone", "linkedin", "website", "url", "country", "location"]
    ):
        return _generate_free_text_answer(label, entry)

    return ""


def _generate_free_text_answer(label: str, entry: dict) -> str:
    """Generate a short, unique free-text answer for a portal question.

    This is where we use every opportunity to present the case for life.
    Keep it short (2-3 sentences), specific to the question, and different
    from the cover letter content.
    """
    org = entry.get("target", {}).get("organization", "")

    # "Anything else you'd like to share?"
    if "anything else" in label.lower() or "additional" in label.lower():
        return (
            f"I maintain a 113-repository system governed by the same patterns this role requires — "
            f"forward-only state transitions, CI-enforced quality gates, and daily health monitoring. "
            f"The system runs 23,470 tests. I built every piece of it alone, which means every component "
            f"had to be self-service, self-healing, and documented well enough that an AI assistant "
            f"can navigate it. That discipline is what I bring to {org}."
        )

    # Generic fallback — should rarely hit
    return ""


def _check_overlap(cover_letter: str, resume_html: str) -> list[str]:
    """Check for 4-word phrase overlaps between cover letter and resume."""
    resume_text = re.sub(r"<[^>]+>", " ", resume_html)
    resume_text = re.sub(r"\s+", " ", resume_text).strip()

    cl_words = cover_letter.lower().split()
    resume_words = resume_text.lower().split()

    cl_phrases = set()
    for i in range(len(cl_words) - 3):
        phrase = " ".join(cl_words[i : i + 4]).strip(".,;:")
        if len(phrase) > 15:
            cl_phrases.add(phrase)

    overlaps = set()
    for i in range(len(resume_words) - 3):
        phrase = " ".join(resume_words[i : i + 4]).strip(".,;:")
        if phrase in cl_phrases:
            overlaps.add(phrase)

    return list(overlaps)


def _build_cover_letter_pdf(
    md_path: Path, pdf_path: Path, entry: dict | None = None
) -> bool:
    """Convert cover letter markdown to PDF via Chrome headless.

    Uses the resume-matching template at materials/resumes/base/cover-letter-template.html
    with title-line, credentials, and sign-off matching the resume visual identity.
    """
    md_text = md_path.read_text()

    # Load the proper template (matches resume visual identity)
    template_path = MATERIALS_DIR / "resumes" / "base" / "cover-letter-template.html"
    if template_path.exists():
        template = template_path.read_text()
    else:
        # Fallback — but this should never happen
        template = (
            '<!DOCTYPE html><html><head><style>'
            'body{font-family:Georgia,serif;font-size:10.5pt;line-height:1.5;'
            'margin:0.45in 0.55in;color:#1a1a1a}p{margin:0 0 11pt 0}'
            '</style></head><body>\n{{BODY}}\n</body></html>'
        )

    # Identity position → title-line and credentials for template
    TITLE_LINES = {
        "systems-artist": "Systems Artist & Creative Technologist",
        "creative-technologist": "Creative Technologist & Systems Builder",
        "independent-engineer": "Software Engineer & Systems Architect",
        "documentation-engineer": "Documentation Engineer & Systems Architect",
        "educator": "Educator & Learning Architect",
        "platform-orchestrator": "Platform Engineer & Systems Builder",
        "governance-architect": "Governance & Compliance Architect",
        "founder-operator": "Full-Stack Engineer & Systems Builder",
        "community-practitioner": "Community Practitioner & Creative Technologist",
    }
    CREDENTIALS = {
        "systems-artist": "Systems Artist & Creative Technologist | MFA, Creative Writing | New York City",
        "creative-technologist": "Creative Technologist | MFA, Creative Writing | New York City",
        "independent-engineer": "Software Engineer | Full-Stack Developer (Meta) | New York City",
        "documentation-engineer": "Documentation Engineer | MFA, Creative Writing | New York City",
        "educator": "Educator & Learning Architect | MFA, Creative Writing | New York City",
        "platform-orchestrator": "Platform Engineer | Full-Stack Developer (Meta) | New York City",
        "governance-architect": "Governance & Compliance Architect | New York City",
        "founder-operator": "Founder & Operator | Full-Stack Developer (Meta) | New York City",
        "community-practitioner": "Community Practitioner | MFA, Creative Writing | New York City",
    }

    position = "independent-engineer"
    if entry:
        position = (
            entry.get("submission", {}).get("identity_position", "")
            or entry.get("fit", {}).get("identity_position", "")
            or entry.get("identity_position", "")
            or "independent-engineer"
        )

    title_line = TITLE_LINES.get(position, "Software Engineer & Systems Architect")
    credentials = CREDENTIALS.get(
        position, "Software Engineer & Systems Architect | MFA, Creative Writing | New York City"
    )

    # Try to match title-line from resume HTML if available
    # Entry ID from entry dict or derive from app dir name
    entry_id = entry.get("id", "") if entry else ""
    if not entry_id:
        entry_id = md_path.parent.name
    resume_dir = MATERIALS_DIR / "resumes" / "batch-03" / entry_id
    if resume_dir.exists():
        for rhtml in resume_dir.glob("*.html"):
            m = re.search(r'class="title-line"[^>]*>([^<]+)<', rhtml.read_text())
            if m:
                title_line = m.group(1).strip()
                break

    # Convert markdown to HTML paragraphs — blank-line-separated paragraphs
    lines = md_text.strip().split("\n")
    paragraphs = []
    current = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))

    # Build body HTML, skipping sign-off and author lines
    SKIP_PATTERNS = (
        "Anthony Padavano", "Anthony James Padavano", "New York, NY",
        "New York City", "padavano.anthony@gmail.com",
    )
    body_parts = []
    for para in paragraphs:
        if para.startswith("Sincerely,") or para.startswith("Sincerely."):
            break
        if any(para.startswith(s) for s in SKIP_PATTERNS):
            continue
        # Convert markdown formatting
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", para)
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        body_parts.append(f"<p>{text}</p>")

    body_html = "\n".join(body_parts)

    # Substitute all template placeholders
    html = template.replace("{{BODY}}", body_html)
    html = html.replace("{{TITLE_LINE}}", title_line)
    html = html.replace("{{CREDENTIALS}}", credentials)

    html_path = md_path.with_suffix(".html").resolve()
    html_path.write_text(html)

    file_url = f"file://{html_path}"
    abs_pdf = pdf_path.resolve()
    for headless_flag in ["--headless=new", "--headless"]:
        if abs_pdf.exists():
            abs_pdf.unlink()
        try:
            result = subprocess.run(
                [
                    CHROME_PATH,
                    headless_flag,
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-software-rasterizer",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={abs_pdf}",
                    file_url,
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and abs_pdf.exists() and abs_pdf.stat().st_size > 0:
                return True
        except subprocess.TimeoutExpired:
            subprocess.run(["pkill", "-f", f"chrome.*{html_path.name}"], capture_output=True)
            continue
        except FileNotFoundError:
            break
    return False


def apply_to_entry(entry_id: str, dry_run: bool = False) -> bool:
    """Run the full application pipeline for a single entry."""
    print(f"\n{'=' * 60}")
    print(f"  APPLYING: {entry_id}")
    print(f"{'=' * 60}\n")

    # 1. Load entry
    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"  ERROR: Entry not found: {entry_id}")
        return False

    org = entry.get("target", {}).get("organization", "")
    role = entry.get("name", "")

    # 1b. CLEARANCE GATE — check before anything else
    desc = entry.get("target", {}).get("description", "").lower()
    # Check eligibility first (softer) to avoid false-positive hard blocks
    eligibility_terms = re.findall(r"(eligible.*clearance|eligib.*obtain|eligib.*security)", desc)
    # Hard blocks: must CURRENTLY HOLD (not just eligible)
    clearance_terms = re.findall(
        r"(active.*clearance|must hold.*clearance|requires active.*clearance|"
        r"current.*clearance required|hold a ts.sci|active ts.sci|polygraph required)",
        desc,
    )
    # If the posting says "eligible to obtain" but NOT "must hold active", it's soft
    if clearance_terms:
        print("  CLEARANCE GATE: HARD BLOCK — requires active clearance")
        for t in clearance_terms:
            print(f"    Found: \"{t}\"")
        print("  ABORTING — do not apply without active clearance")
        return False
    elif eligibility_terms:
        print("  CLEARANCE GATE: SOFT — requires eligibility (US citizen = eligible)")
        for t in eligibility_terms:
            print(f"    Found: \"{t}\"")
        print("  Proceeding — you are eligible as a US citizen")
    url = entry.get("target", {}).get("application_url", "")
    portal = entry.get("target", {}).get("portal", "")
    print(f"  Organization: {org}")
    print(f"  Role: {role}")
    print(f"  URL: {url}")
    print(f"  Portal: {portal}")

    # 1c. APPLICATION URL LIVENESS CHECK
    if url:
        import urllib.error
        import urllib.request
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status >= 400:
                print(f"  URL CHECK: WARNING — returned HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("  URL CHECK: DEAD LINK — HTTP 404. Job posting may have been removed.")
            else:
                print(f"  URL CHECK: WARNING — HTTP {e.code}")
        except Exception:
            print("  URL CHECK: Could not verify (timeout or network error)")

    # 2. Standards audit — Level 1 (Course Regulator)
    print("\n  Running standards audit (Level 1)...")
    board = _load_standards_board()
    if board:
        try:
            level1 = board.check_entry(entry)
            if level1.passed:
                print(f"  Standards L1: PASS (quorum {level1.quorum})")
            else:
                print(f"  Standards L1: FAIL (quorum {level1.quorum})")
                for gate in level1.gates:
                    if not gate.passed:
                        print(f"    FAIL: {gate.gate} — {gate.evidence[:80]}")
        except Exception as e:
            print(f"  Standards L1: SKIP ({e})")
    else:
        print("  Standards L1: SKIP (module not available)")

    # 3. Fetch portal questions from API
    print("\n  Fetching portal questions...")
    board_job = _extract_board_and_job(entry)
    questions = []
    custom_questions = []
    if board_job and portal == "greenhouse":
        board, job_id = board_job
        questions = fetch_job_questions(board, job_id)
        custom_questions = get_custom_questions(questions)
        print(f"  Found {len(questions)} total questions, {len(custom_questions)} custom")
    else:
        print("  Non-Greenhouse portal or could not extract board/job — using standard fields only")

    # 3. Generate answers
    print("  Generating answers...")
    personal = _load_personal_info()
    answers = []
    for q in questions:
        label = (q.get("label") or "").strip()
        answer = _answer_question(q, entry, personal)
        required = q.get("required", False)
        answers.append({"label": label, "answer": answer, "required": required})

    # 4. Resolve cover letter
    print("  Resolving cover letter...")
    cover_letter = resolve_cover_letter(entry, strip_md=False)
    if not cover_letter:
        print("  WARNING: No cover letter found — generate one before submitting")
        cover_letter = ""

    # 5. Find resume
    resume_dir = MATERIALS_DIR / "resumes" / "batch-03" / entry_id
    resume_pdf = None
    resume_html = None
    if resume_dir.exists():
        pdfs = list(resume_dir.glob("*.pdf"))
        htmls = list(resume_dir.glob("*.html"))
        if pdfs:
            resume_pdf = pdfs[0]
        if htmls:
            resume_html = htmls[0]
    if not resume_pdf:
        print(f"  WARNING: No resume PDF found in {resume_dir}")

    # 6. Check overlap
    overlaps = []
    if cover_letter and resume_html and resume_html.exists():
        overlaps = _check_overlap(cover_letter, resume_html.read_text())
        if len(overlaps) > 3:
            print(f"  WARNING: {len(overlaps)} overlapping phrases between cover letter and resume")
            for o in overlaps[:5]:
                print(f"    \"{o}\"")
        else:
            print(f"  Overlap check: {len(overlaps)} phrases (OK)")

    # 7. Protocol-validated outreach DM
    print("\n  Composing outreach DM...")
    org_contacts = _load_contacts_for_org(org)
    dm_text = ""
    if org_contacts:
        # Find the connect note from outreach log
        try:
            from dm_composer import compose_acceptance_dm
            primary_contact = org_contacts[0]
            result = compose_acceptance_dm(primary_contact.get("name", ""))
            if result and result.dm_text:
                dm_text = result.dm_text
                protocol_status = "PASS" if result.protocol_valid else "FAIL"
                print(f"  Protocol validation: {protocol_status}")
                print(f"  DM for: {primary_contact.get('name', '?')} ({org})")
                if not result.protocol_valid:
                    print(f"  Protocol report:\n{result.protocol_report}")
            else:
                print("  DM: Could not compose (no connect note found)")
        except Exception as e:
            print(f"  DM: SKIP ({e})")
    else:
        print(f"  DM: No contacts at {org} — research contacts after submission")

    # 8. Create application directory
    today = str(date.today())
    org_slug = re.sub(r"[^a-z0-9]+", "-", org.lower()).strip("-")
    role_slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")[:60]
    app_dir = APPLICATIONS_DIR / today / f"{org_slug}--{role_slug}"

    if dry_run:
        print(f"\n  [DRY RUN] Would create: {app_dir}")
        print(f"  Questions: {len(questions)}")
        print(f"  Cover letter: {'found' if cover_letter else 'MISSING'}")
        print(f"  Resume PDF: {resume_pdf.name if resume_pdf else 'MISSING'}")
        return True

    app_dir.mkdir(parents=True, exist_ok=True)

    # 8. Write all files
    # Entry YAML (snapshot)
    if filepath:
        (app_dir / "entry.yaml").write_text(Path(filepath).read_text())
        print("  Wrote: entry.yaml")

    # Portal answers
    pa_lines = [f"# {org} — {role} — Portal Answers\n"]
    pa_lines.append(f"**Portal URL:** {url}\n")
    pa_lines.append(f"**Date:** {today}\n")
    pa_lines.append("**Questions fetched from Greenhouse API**\n")
    pa_lines.append("---\n")
    for a in answers:
        req = " (required)" if a["required"] else ""
        pa_lines.append(f"## {a['label']}{req}\n")
        pa_lines.append(f"{a['answer']}\n")
    (app_dir / "portal-answers.md").write_text("\n".join(pa_lines))
    print(f"  Wrote: portal-answers.md ({len(answers)} answers)")

    # Portal answer validation — catch blank required fields
    blank_required = [a for a in answers if a["required"] and not a["answer"].strip()]
    if blank_required:
        print(f"  PORTAL VALIDATION: {len(blank_required)} BLANK REQUIRED FIELD(S):")
        for a in blank_required:
            print(f"    BLANK: {a['label']}")
        print("  These must be filled before submission.")

    # Cover letter
    if cover_letter:
        cl_path = app_dir / "cover-letter.md"
        cl_path.write_text(cover_letter)
        print("  Wrote: cover-letter.md")

        # Build PDF
        pdf_name = f"Anthony-Padavano-{org.replace(' ', '-')}-Cover-Letter.pdf"
        pdf_path = app_dir / pdf_name
        if _build_cover_letter_pdf(cl_path, pdf_path, entry=entry):
            print(f"  Built: {pdf_name}")
        else:
            print("  WARNING: Failed to build cover letter PDF")

    # Resume
    if resume_pdf:
        dest = app_dir / f"Anthony-Padavano-{org.replace(' ', '-')}-Resume.pdf"
        import shutil
        shutil.copy2(resume_pdf, dest)
        print(f"  Copied: {dest.name}")
    if resume_html:
        dest = app_dir / f"Anthony-Padavano-{org.replace(' ', '-')}-Resume.html"
        import shutil
        shutil.copy2(resume_html, dest)

    # HARD RULE CHECKS — automated, not memory-dependent
    # Rule 1: No "Independent Engineer" anywhere
    for check_file in app_dir.iterdir():
        if check_file.suffix in (".md", ".html"):
            content = check_file.read_text()
            if "Independent Engineer" in content:
                print(f"  RED FLAG: '{check_file.name}' contains 'Independent Engineer' — must use ORGANVM")
    # Rule 2: Cover letter must not have metadata headers
    if cover_letter and cover_letter.startswith("#"):
        print("  RED FLAG: Cover letter starts with markdown header — strip metadata")
    # Rule 3: Cover letter word count (550-700 target, RED FLAG if < 500)
    if cover_letter:
        cl_words = len(cover_letter.split())
        if cl_words < 500:
            print(f"  RED FLAG: Cover letter is {cl_words} words — minimum 550, target 550-700")
        elif cl_words < 550:
            print(f"  WARNING: Cover letter is {cl_words} words — target 550-700")
    # Rule 4: Resume experience entry count (minimum 4)
    if resume_html and resume_html.exists():
        resume_content = resume_html.read_text()
        entry_count = resume_content.count("entry-header")
        if entry_count < 4:
            print(f"  RED FLAG: Resume has {entry_count} experience entries — minimum 4")
        # Rule 5: No columnar layout in experience
        if "grid-template-columns" in resume_content or "column-count" in resume_content:
            print("  RED FLAG: Resume uses columnar layout — must be vertical stacked")

    # Outreach DM
    if dm_text:
        dm_contact = org_contacts[0].get("name", "TBD") if org_contacts else "TBD"
        (app_dir / "outreach-dm.md").write_text(
            f"# Outreach DM — {org}\n\n"
            f"**Contact:** {dm_contact}\n\n"
            f"---\n\n{dm_text}\n"
        )
        print("  Wrote: outreach-dm.md")

    # 9. Validate — continuity test (all connections checked)
    files = list(app_dir.iterdir())
    print(f"\n  {'─' * 50}")
    print(f"  CONTINUITY TEST — {org}")
    print(f"  {'─' * 50}")

    checks = {
        "entry.yaml": (app_dir / "entry.yaml").exists(),
        "portal-answers.md": (app_dir / "portal-answers.md").exists(),
        "cover-letter.md": any(f.name.endswith("cover-letter.md") for f in files),
        "cover-letter.pdf": any("Cover-Letter.pdf" in f.name for f in files),
        "resume.pdf": any("Resume.pdf" in f.name for f in files),
    }

    all_pass = True
    for check_name, passed in checks.items():
        icon = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{icon}] {check_name}")

    # Optional but valuable
    if dm_text:
        print("  [PASS] outreach-dm.md (Protocol-validated)")
    else:
        print("  [WARN] outreach-dm.md (no contacts — research needed)")

    overlap_status = f"{len(overlaps)} phrases" if overlaps else "0 (clean)"
    overlap_icon = "PASS" if len(overlaps) <= 3 else "WARN"
    print(f"  [{overlap_icon}] overlap check: {overlap_status}")

    print(f"\n  Files: {len(files)}")
    for f in sorted(files):
        size = f.stat().st_size
        print(f"    {f.name} ({size:,} bytes)")

    print(f"\n  PORTAL URL: {url}")
    verdict = "READY" if all_pass else "INCOMPLETE — fix failures above"
    print(f"  STATUS: {verdict}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Single-command application pipeline")
    parser.add_argument("--target", help="Pipeline entry ID")
    parser.add_argument("--batch", action="store_true", help="Process all staged entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    if args.batch:
        # Find all staged entries
        staged = []
        for f in PIPELINE_DIR_ACTIVE.glob("*.yaml"):
            if f.name.startswith("_"):
                continue
            try:
                e = yaml.safe_load(f.read_text())
            except Exception:
                continue
            if e and e.get("status") == "staged":
                staged.append(e.get("id", f.stem))
        if not staged:
            print("No staged entries found.")
            return
        print(f"Processing {len(staged)} staged entries...")
        for entry_id in staged:
            apply_to_entry(entry_id, dry_run=args.dry_run)
    elif args.target:
        apply_to_entry(args.target, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
