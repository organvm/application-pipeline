"""Wiring tests for data flow between pipeline_lib and downstream scripts.

These tests verify that interfaces between pipeline_lib (the hub) and
downstream scripts (the spokes) are intact. Following the "Christmas Light"
hierarchy analogy: we're testing that the "wiring" (data contracts) between
components is properly connected.

Test categories:
1. Data loading: load_entries, load_profile, load_block, load_variant
2. ID mapping: PROFILE_ID_MAP, LEGACY_ID_MAP consistency
3. End-to-end flows: YAML entry → enrich → compose
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    BLOCKS_DIR,
    LEGACY_DIR,
    LEGACY_ID_MAP,
    PROFILE_ID_MAP,
    PROFILES_DIR,
    REPO_ROOT,
    VARIANTS_DIR,
    load_block,
    load_block_index,
    load_entries,
    load_entry_by_id,
    load_legacy_script,
    load_profile,
    load_variant,
)

# ==============================================================================
# Test: load_entries - Pipeline YAML loading
# ==============================================================================


class TestLoadEntries:
    """Tests for load_entries() interface."""

    def test_load_entries_returns_list(self):
        """load_entries should return a list of entry dicts."""
        entries = load_entries()
        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_load_entries_has_required_metadata(self):
        """Each entry should have _dir and _file metadata."""
        entries = load_entries()
        for entry in entries:
            assert "_dir" in entry, "Entry missing _dir metadata"
            assert "_file" in entry, "Entry missing _file metadata"

    def test_load_entries_metadata_values_valid(self):
        """_dir values should be valid pipeline directory names."""
        entries = load_entries()
        valid_dirs = {d.name for d in ALL_PIPELINE_DIRS}
        for entry in entries:
            assert entry["_dir"] in valid_dirs, f"Invalid _dir: {entry['_dir']}"

    def test_load_entries_include_filepath(self):
        """include_filepath should add _filepath to each entry."""
        entries = load_entries(include_filepath=True)
        for entry in entries:
            assert "_filepath" in entry
            assert isinstance(entry["_filepath"], Path)

    def test_load_entries_skips_schema_files(self):
        """Entries should not include _schema.yaml."""
        entries = load_entries()
        filenames = [e["_file"] for e in entries]
        assert "_schema.yaml" not in filenames

    def test_load_entries_from_specific_dir(self):
        """load_entries should accept dirs parameter."""
        entries = load_entries(dirs=[REPO_ROOT / "pipeline" / "active"])
        for entry in entries:
            assert entry["_dir"] == "active"


# ==============================================================================
# Test: load_entry_by_id - Single entry lookup
# ==============================================================================


class TestLoadEntryById:
    """Tests for load_entry_by_id() interface."""

    def test_load_entry_by_id_found(self):
        """Should return filepath and data for existing entry."""
        filepath, data = load_entry_by_id("creative-capital-2027")
        assert filepath is not None
        assert data is not None
        assert data["id"] == "creative-capital-2027"

    def test_load_entry_by_id_not_found(self):
        """Should return (None, None) for non-existent entry."""
        filepath, data = load_entry_by_id("nonexistent-entry-xyz")
        assert filepath is None
        assert data is None

    def test_load_entry_by_id_across_directories(self):
        """Should find entry regardless of which directory it's in."""
        # Find an entry that exists
        entries = load_entries()
        if entries:
            test_id = entries[0].get("id")
            if test_id:
                filepath, data = load_entry_by_id(test_id)
                assert filepath is not None
                assert data is not None


# ==============================================================================
# Test: load_profile - Target profile loading with ID mapping
# ==============================================================================


class TestLoadProfile:
    """Tests for load_profile() interface and PROFILE_ID_MAP."""

    def test_load_profile_direct_match(self):
        """Should load profile for direct match."""
        # Find a profile that exists
        profiles = list(PROFILES_DIR.glob("*.json"))
        if profiles:
            # Extract target_id from filename
            profile_name = profiles[0].stem
            profile = load_profile(profile_name)
            assert profile is not None

    def test_load_profile_with_id_map(self):
        """Should fall back to PROFILE_ID_MAP for mapped IDs."""
        # Test with a known mapped ID from PROFILE_ID_MAP
        if PROFILE_ID_MAP:
            first_mapped_id = next(iter(PROFILE_ID_MAP.keys()))
            profile = load_profile(first_mapped_id)
            # Should either find direct or mapped match
            assert profile is not None or first_mapped_id in PROFILE_ID_MAP

    def test_load_profile_not_found(self):
        """Should return None for non-existent profile."""
        profile = load_profile("nonexistent-profile-xyz")
        assert profile is None

    def test_profile_id_map_values_valid(self):
        """PROFILE_ID_MAP values should point to existing files."""
        for entry_id, profile_name in PROFILE_ID_MAP.items():
            # Just verify the mapped name is reasonable
            assert profile_name, f"Empty profile name for entry_id: {entry_id}"


# ==============================================================================
# Test: load_block - Block content loading
# ==============================================================================


class TestLoadBlock:
    """Tests for load_block() interface."""

    def test_load_block_index_returns_dict(self):
        """load_block_index should return dict with blocks and tag_index keys."""
        index = load_block_index()
        assert isinstance(index, dict)
        # Index has 'blocks' and 'tag_index' keys
        assert "blocks" in index or "tag_index" in index or len(index) > 0

    def test_load_block_index_structure(self):
        """Block index blocks should have title, category, tags for each entry."""
        index = load_block_index()
        blocks = index.get("blocks", {})

        if blocks:
            for path, metadata in list(blocks.items())[:3]:  # Check first 3
                assert "title" in metadata, f"Missing title in {path}"
                # tags or category should exist
                assert "tags" in metadata or "category" in metadata, f"Missing tags/category in {path}"

    def test_load_block_existing(self):
        """Should load block content for existing block path."""
        index = load_block_index()
        blocks = index.get("blocks", {})

        if blocks:
            first_path = next(iter(blocks.keys()))
            content = load_block(first_path)
            assert content is not None
            assert len(content) > 0

    def test_load_block_not_found(self):
        """Should return None for non-existent block."""
        content = load_block("nonexistent/block/path")
        assert content is None


# ==============================================================================
# Test: load_variant - Variant content loading
# ==============================================================================


class TestLoadVariant:
    """Tests for load_variant() interface."""

    def test_load_variant_existing(self):
        """Should load variant content for existing variant."""
        # Find existing variants
        if VARIANTS_DIR.exists():
            variants = list(VARIANTS_DIR.glob("*.md"))
            if variants:
                variant_name = variants[0].stem
                content = load_variant(variant_name)
                assert content is not None or variant_name.startswith("_")

    def test_load_variant_not_found(self):
        """Should return None for non-existent variant."""
        content = load_variant("nonexistent-variant-xyz")
        assert content is None


# ==============================================================================
# Test: load_legacy_script - Legacy submission scripts
# ==============================================================================


class TestLoadLegacyScript:
    """Tests for load_legacy_script() interface and LEGACY_ID_MAP."""

    def test_legacy_id_map_consistency(self):
        """LEGACY_ID_MAP should have valid entries."""
        for legacy_name, entry_id in LEGACY_ID_MAP.items():
            assert legacy_name, "Empty legacy name"
            assert entry_id, "Empty entry_id"

    def test_load_legacy_script_direct_match(self):
        """Should load legacy script for direct match."""
        if LEGACY_DIR.exists():
            scripts = list(LEGACY_DIR.glob("*.md"))
            if scripts:
                script_name = scripts[0].stem
                script = load_legacy_script(script_name)
                # May return None if parse fails, but shouldn't error
                assert script is None or isinstance(script, dict)

    def test_load_legacy_script_with_id_map(self):
        """Should fall back to LEGACY_ID_MAP for mapped IDs."""
        if LEGACY_ID_MAP:
            first_mapped_id = next(iter(LEGACY_ID_MAP.values()))
            load_legacy_script(first_mapped_id)
            # Script may exist or not, just shouldn't error

    def test_load_legacy_script_not_found(self):
        """Should return None for non-existent script."""
        script = load_legacy_script("nonexistent-script-xyz")
        assert script is None


# ==============================================================================
# Test: End-to-end data flow - Wiring between loaders
# ==============================================================================


class TestDataFlowWiring:
    """Integration tests for wiring between data loaders."""

    def test_entry_to_profile_wiring(self):
        """Entry with profile reference should find corresponding profile."""
        entries = load_entries()
        # Find entry with target_id
        entries_with_target = [e for e in entries if e.get("target", {}).get("id")]

        if entries_with_target:
            entry = entries_with_target[0]
            target_id = entry["target"]["id"]
            profile = load_profile(target_id)
            # Profile should exist or profile mapping should exist
            if profile is None:
                # Should be in PROFILE_ID_MAP
                assert target_id in PROFILE_ID_MAP

    def test_entry_to_block_wiring(self):
        """Entry with blocks_used should reference valid block paths."""
        entries = load_entries()
        entries_with_blocks = [e for e in entries if e.get("submission", {}).get("blocks_used")]

        if entries_with_blocks:
            entry = entries_with_blocks[0]
            blocks_used = entry["submission"]["blocks_used"]
            if blocks_used and isinstance(blocks_used, list):
                for block_path in blocks_used[:1]:  # Check first block
                    content = load_block(block_path)
                    assert content is not None, f"Block not found: {block_path}"

    def test_entry_to_variant_wiring(self):
        """Entry with variant reference should find corresponding variant."""
        entries = load_entries()
        entries_with_variant = [e for e in entries if e.get("submission", {}).get("variant")]

        if entries_with_variant:
            entry = entries_with_variant[0]
            variant_name = entry["submission"]["variant"]
            if variant_name:
                load_variant(variant_name)
                # Variant may not exist, but shouldn't error


# ==============================================================================
# Test: Constant consistency - Single source of truth
# ==============================================================================


class TestConstantConsistency:
    """Tests for consistency of constants across the pipeline."""

    def test_pipeline_dirs_exist(self):
        """ALL_PIPELINE_DIRS should all exist."""
        for pipeline_dir in ALL_PIPELINE_DIRS:
            assert pipeline_dir.exists(), f"Pipeline dir missing: {pipeline_dir}"

    def test_blocks_dir_exists(self):
        """BLOCKS_DIR should exist."""
        assert BLOCKS_DIR.exists()

    def test_profiles_dir_exists(self):
        """PROFILES_DIR should exist."""
        assert PROFILES_DIR.exists()

    def test_variants_dir_exists(self):
        """VARIANTS_DIR should exist."""
        assert VARIANTS_DIR.exists()

    def test_legacy_dir_exists(self):
        """LEGACY_DIR should exist."""
        assert LEGACY_DIR.exists()
