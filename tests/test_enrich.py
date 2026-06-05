"""Tests for scripts/enrich.py"""

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from enrich import (
    COVER_LETTER_MAP,
    CURRENT_BATCH,
    DEFAULT_RESUME,
    GRANT_TEMPLATE_TRACKS,
    JOB_BLOCKS_BY_IDENTITY,
    RESUME_BY_IDENTITY,
    RESUME_TRACKS,
    detect_gaps,
    enrich_blocks,
    enrich_materials,
    enrich_variant,
    find_matching_variant,
    select_resume,
)
from pipeline_lib import MATERIALS_DIR, VARIANTS_DIR


def _make_temp_yaml(content: str) -> Path:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


SAMPLE_GRANT = """id: test-grant
name: Test Grant
track: grant
status: staged
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_GRANT_WITH_MATERIALS = """id: test-grant
name: Test Grant
track: grant
status: staged
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids: {}
  materials_attached:
    - resumes/multimedia-specialist.pdf
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_JOB = """id: anthropic-fde
name: Anthropic FDE
track: job
status: qualified
outcome: null
submission:
  effort_level: complex
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_WRITING = """id: test-writing
name: Test Writing Submission
track: writing
status: qualified
outcome: null
submission:
  effort_level: quick
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_ACADEMIC = """id: test-academic
name: Test Academic Position
track: academic
status: staged
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_WITH_VARIANTS = """id: test-entry
name: Test Entry
track: job
status: qualified
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids:
    cover_letter: cover-letters/existing
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_GRANT_WITH_IDENTITY = """id: test-grant-identity
name: Test Grant With Identity
track: grant
status: staged
outcome: null
fit:
  score: 7.0
  identity_position: systems-artist
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_JOB_WITH_IDENTITY = """id: test-job-identity
name: Test Job With Identity
track: job
status: qualified
outcome: null
fit:
  score: 8.0
  identity_position: independent-engineer
submission:
  effort_level: complex
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""


# --- enrich_materials ---


def test_enrich_materials_replaces_empty_list():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        })
        assert result is True
        content = filepath.read_text()
        assert DEFAULT_RESUME in content
        assert "materials_attached: []" not in content
    finally:
        filepath.unlink()


def test_enrich_materials_preserves_existing():
    filepath = _make_temp_yaml(SAMPLE_GRANT_WITH_MATERIALS)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": ["resumes/multimedia-specialist.pdf"]},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_academic_in_resume_and_grant_template_tracks():
    """Academic applications carry CVs (resume) and use the grant cover-letter template."""
    assert "academic" in RESUME_TRACKS
    assert "academic" in GRANT_TEMPLATE_TRACKS


def test_enrich_materials_populates_academic_track():
    """Academic entries get a resume wired in, like grants — they carry CVs."""
    filepath = _make_temp_yaml(SAMPLE_ACADEMIC)
    try:
        result = enrich_materials(filepath, {
            "track": "academic",
            "submission": {"materials_attached": []},
        })
        assert result is True
        content = filepath.read_text()
        assert DEFAULT_RESUME in content
        assert "materials_attached: []" not in content
    finally:
        filepath.unlink()


def test_enrich_materials_skips_writing_track():
    filepath = _make_temp_yaml(SAMPLE_WRITING)
    try:
        result = enrich_materials(filepath, {
            "track": "writing",
            "submission": {"materials_attached": []},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_materials_skips_consulting_track():
    filepath = _make_temp_yaml(SAMPLE_WRITING)
    try:
        result = enrich_materials(filepath, {
            "track": "consulting",
            "submission": {"materials_attached": []},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_materials_updates_last_touched():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        })
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_enrich_materials_dry_run():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        }, dry_run=True)
        assert result is True
        # File should be unchanged
        content = filepath.read_text()
        assert "materials_attached: []" in content
    finally:
        filepath.unlink()


# --- select_resume ---


def test_select_resume_independent_engineer():
    entry = {"fit": {"identity_position": "independent-engineer"}}
    assert select_resume(entry) == "resumes/base/independent-engineer-resume.pdf"


def test_select_resume_systems_artist():
    entry = {"fit": {"identity_position": "systems-artist"}}
    assert select_resume(entry) == "resumes/base/systems-artist-resume.pdf"


def test_select_resume_creative_technologist():
    entry = {"fit": {"identity_position": "creative-technologist"}}
    assert select_resume(entry) == "resumes/base/creative-technologist-resume.pdf"


def test_select_resume_community_practitioner():
    entry = {"fit": {"identity_position": "community-practitioner"}}
    assert select_resume(entry) == "resumes/base/community-practitioner-resume.pdf"


def test_select_resume_educator():
    entry = {"fit": {"identity_position": "educator"}}
    assert select_resume(entry) == "resumes/base/educator-resume.pdf"


def test_select_resume_unknown_position_falls_back():
    entry = {"fit": {"identity_position": "unknown-position"}}
    assert select_resume(entry) == DEFAULT_RESUME


def test_select_resume_no_fit_falls_back():
    entry = {"track": "grant"}
    assert select_resume(entry) == DEFAULT_RESUME


def test_select_resume_empty_position_falls_back():
    entry = {"fit": {"identity_position": ""}}
    assert select_resume(entry) == DEFAULT_RESUME


# --- enrich_materials with identity ---


def test_enrich_materials_uses_identity_position():
    filepath = _make_temp_yaml(SAMPLE_GRANT_WITH_IDENTITY)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "fit": {"identity_position": "systems-artist"},
            "submission": {"materials_attached": []},
        })
        assert result is True
        content = filepath.read_text()
        assert "systems-artist-resume.pdf" in content
        assert "multimedia-specialist" not in content
    finally:
        filepath.unlink()


def test_enrich_materials_uses_engineer_identity():
    filepath = _make_temp_yaml(SAMPLE_JOB_WITH_IDENTITY)
    try:
        result = enrich_materials(filepath, {
            "track": "job",
            "fit": {"identity_position": "independent-engineer"},
            "submission": {"materials_attached": []},
        })
        assert result is True
        content = filepath.read_text()
        assert "independent-engineer-resume.pdf" in content
    finally:
        filepath.unlink()


def test_enrich_materials_falls_back_without_identity():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        })
        assert result is True
        content = filepath.read_text()
        assert DEFAULT_RESUME in content
    finally:
        filepath.unlink()


# --- resume file existence ---


def test_identity_resume_html_files_exist():
    """All identity-position resume HTML files should exist."""
    for position, pdf_path in RESUME_BY_IDENTITY.items():
        html_path = MATERIALS_DIR / pdf_path.replace(".pdf", ".html")
        assert html_path.exists(), f"Missing HTML: {html_path} (for {position})"


# --- enrich_variant ---


def test_enrich_variant_replaces_empty_dict():
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        result = enrich_variant(filepath, {
            "submission": {"variant_ids": {}},
        }, "cover-letters/anthropic-fde-custom-agents")
        assert result is True
        content = filepath.read_text()
        assert "anthropic-fde-custom-agents" in content
        assert "variant_ids: {}" not in content
    finally:
        filepath.unlink()


def test_enrich_variant_preserves_existing():
    filepath = _make_temp_yaml(SAMPLE_WITH_VARIANTS)
    try:
        result = enrich_variant(filepath, {
            "submission": {"variant_ids": {"cover_letter": "cover-letters/existing"}},
        }, "cover-letters/new-one")
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_variant_updates_last_touched():
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        enrich_variant(filepath, {
            "submission": {"variant_ids": {}},
        }, "cover-letters/test")
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_enrich_variant_dry_run():
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        result = enrich_variant(filepath, {
            "submission": {"variant_ids": {}},
        }, "cover-letters/test", dry_run=True)
        assert result is True
        content = filepath.read_text()
        assert "variant_ids: {}" in content
    finally:
        filepath.unlink()


# --- find_matching_variant ---


def test_find_matching_variant_known():
    assert find_matching_variant("anthropic-fde") == "cover-letters/anthropic-fde-custom-agents"
    assert find_matching_variant("huggingface-dev-advocate") == "cover-letters/huggingface-dev-advocate-hub-enterprise"
    assert find_matching_variant("openai-se-evals") == "cover-letters/openai-se-applied-evals"
    assert find_matching_variant("together-ai") == "cover-letters/together-ai-lead-dx-documentation"


def test_find_matching_variant_unknown():
    assert find_matching_variant("artadia-nyc") is None
    assert find_matching_variant("nonexistent") is None


# --- File existence checks ---


def test_cover_letter_map_files_exist():
    """All mapped variant files should exist on disk."""
    for entry_id, variant_path in COVER_LETTER_MAP.items():
        full_path = VARIANTS_DIR / f"{variant_path}.md"
        assert full_path.exists(), f"Missing variant: {full_path} (for {entry_id})"


def test_default_resume_exists():
    """The default resume file should exist on disk."""
    full_path = MATERIALS_DIR / DEFAULT_RESUME
    assert full_path.exists(), f"Missing resume: {full_path}"


# --- detect_gaps ---


def test_detect_gaps_materials():
    entry = {
        "id": "test",
        "track": "grant",
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "materials" in gaps


def test_detect_gaps_no_materials_for_writing():
    entry = {
        "id": "test",
        "track": "writing",
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "materials" not in gaps


def test_detect_gaps_variants_for_mapped_entry():
    entry = {
        "id": "anthropic-fde",
        "track": "job",
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "variants" in gaps


def test_detect_gaps_no_variant_gap_when_populated():
    entry = {
        "id": "anthropic-fde",
        "track": "job",
        "submission": {
            "materials_attached": ["resumes/multimedia-specialist.pdf"],
            "variant_ids": {"cover_letter": "cover-letters/existing"},
        },
    }
    gaps = detect_gaps(entry)
    assert "variants" not in gaps


def test_resume_tracks_complete():
    """Ensure RESUME_TRACKS covers expected tracks."""
    expected = {"job", "fellowship", "grant", "residency", "prize", "program", "academic"}
    assert RESUME_TRACKS == expected


def test_grant_template_tracks():
    """Ensure GRANT_TEMPLATE_TRACKS covers expected tracks."""
    expected = {"grant", "residency", "prize", "academic"}
    assert GRANT_TEMPLATE_TRACKS == expected


# --- enrich_blocks ---


def test_enrich_blocks_job_entry():
    """Job entry with identity_position should get blocks wired."""
    filepath = _make_temp_yaml(SAMPLE_JOB_WITH_IDENTITY)
    try:
        result = enrich_blocks(filepath, {
            "track": "job",
            "fit": {"identity_position": "independent-engineer"},
            "submission": {"blocks_used": {}},
        })
        assert result is True
        content = filepath.read_text()
        assert "framings/independent-engineer" in content
        assert "evidence/differentiators" in content
        assert "evidence/work-samples" in content
        assert "pitches/credentials-creative-tech" in content
        assert "methodology/ai-conductor" in content
        assert "blocks_used: {}" not in content
    finally:
        filepath.unlink()


def test_enrich_blocks_skips_existing():
    """Existing blocks_used should not be overwritten."""
    yaml_content = """id: test-job
name: Test Job
track: job
status: qualified
outcome: null
fit:
  score: 8.0
  identity_position: independent-engineer
submission:
  effort_level: complex
  blocks_used:
    custom: some/custom-block
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""
    filepath = _make_temp_yaml(yaml_content)
    try:
        result = enrich_blocks(filepath, {
            "track": "job",
            "fit": {"identity_position": "independent-engineer"},
            "submission": {"blocks_used": {"custom": "some/custom-block"}},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_blocks_skips_grant():
    """Grant entries should not get auto-blocks (only jobs)."""
    filepath = _make_temp_yaml(SAMPLE_GRANT_WITH_IDENTITY)
    try:
        result = enrich_blocks(filepath, {
            "track": "grant",
            "fit": {"identity_position": "systems-artist"},
            "submission": {"blocks_used": {}},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_blocks_dry_run():
    """Dry run should return True but not modify the file."""
    filepath = _make_temp_yaml(SAMPLE_JOB_WITH_IDENTITY)
    try:
        result = enrich_blocks(filepath, {
            "track": "job",
            "fit": {"identity_position": "independent-engineer"},
            "submission": {"blocks_used": {}},
        }, dry_run=True)
        assert result is True
        content = filepath.read_text()
        assert "blocks_used: {}" in content  # unchanged
    finally:
        filepath.unlink()


def test_enrich_blocks_updates_last_touched():
    """Blocks enrichment should update last_touched."""
    filepath = _make_temp_yaml(SAMPLE_JOB_WITH_IDENTITY)
    try:
        enrich_blocks(filepath, {
            "track": "job",
            "fit": {"identity_position": "independent-engineer"},
            "submission": {"blocks_used": {}},
        })
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_enrich_blocks_skips_unknown_identity():
    """Job with unrecognized identity_position should not get blocks."""
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        result = enrich_blocks(filepath, {
            "track": "job",
            "fit": {"identity_position": "unknown-position"},
            "submission": {"blocks_used": {}},
        })
        assert result is False
    finally:
        filepath.unlink()


# --- detect_gaps with blocks ---


def test_detect_gaps_includes_blocks_for_job():
    """Job entry with empty blocks and known identity should have blocks gap."""
    entry = {
        "id": "test-job",
        "track": "job",
        "fit": {"identity_position": "independent-engineer"},
        "submission": {"materials_attached": [], "blocks_used": {}, "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "blocks" in gaps


def test_detect_gaps_no_blocks_for_grant():
    """Grant entry should not have blocks gap (blocks enrichment is job-only)."""
    entry = {
        "id": "test-grant",
        "track": "grant",
        "fit": {"identity_position": "systems-artist"},
        "submission": {"materials_attached": [], "blocks_used": {}, "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "blocks" not in gaps


def test_detect_gaps_no_blocks_when_populated():
    """Job entry with blocks already populated should not have blocks gap."""
    entry = {
        "id": "test-job",
        "track": "job",
        "fit": {"identity_position": "independent-engineer"},
        "submission": {
            "materials_attached": [],
            "blocks_used": {"framing": "framings/independent-engineer"},
            "variant_ids": {},
        },
    }
    gaps = detect_gaps(entry)
    assert "blocks" not in gaps


def test_job_blocks_by_identity_keys():
    """JOB_BLOCKS_BY_IDENTITY should cover the same identities as RESUME_BY_IDENTITY."""
    assert set(JOB_BLOCKS_BY_IDENTITY.keys()) == set(RESUME_BY_IDENTITY.keys())


# --- select_resume: tailored resume preference ---


def test_select_resume_prefers_tailored_over_base():
    """When a tailored resume exists in batch-03, it should be selected over base."""
    batch_dir = MATERIALS_DIR / "resumes" / CURRENT_BATCH
    # Find any entry that has a tailored resume in batch-03
    if not batch_dir.exists():
        return  # skip if no batch dir
    entry_dirs = [d for d in batch_dir.iterdir() if d.is_dir()]
    if not entry_dirs:
        return  # skip if no entries
    entry_dir = entry_dirs[0]
    entry_id = entry_dir.name
    entry = {"id": entry_id, "fit": {"identity_position": "independent-engineer"}}
    result = select_resume(entry)
    # Should NOT be a base resume
    assert "resumes/base/" not in result
    # Should reference the batch directory
    assert CURRENT_BATCH in result


def test_select_resume_falls_back_to_base_without_tailored():
    """When no tailored resume exists, falls back to identity-based base resume."""
    entry = {"id": "nonexistent-entry-xyz-999", "fit": {"identity_position": "systems-artist"}}
    result = select_resume(entry)
    assert result == "resumes/base/systems-artist-resume.pdf"


def test_select_resume_real_entries_prefer_tailored():
    """All entries in batch-03 should get tailored resumes from select_resume."""
    batch_dir = MATERIALS_DIR / "resumes" / CURRENT_BATCH
    if not batch_dir.exists():
        return
    for entry_dir in batch_dir.iterdir():
        if not entry_dir.is_dir():
            continue
        has_resume = any(
            f.suffix in (".pdf", ".html")
            for f in entry_dir.iterdir()
            if "resume" in f.name.lower() or "cv" in f.name.lower()
        )
        if not has_resume:
            continue
        entry = {"id": entry_dir.name}
        result = select_resume(entry)
        assert "resumes/base/" not in result, (
            f"Entry {entry_dir.name} has tailored resume but select_resume returned base: {result}"
        )
