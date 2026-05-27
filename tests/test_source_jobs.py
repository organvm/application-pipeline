"""Tests for scripts/source_jobs.py"""

import json
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from source_jobs import (
    VALID_LOCATION_CLASSES,
    _slugify,
    _strip_html,
    _yaml_quote,
    classify_location,
    create_pipeline_entry,
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    filter_by_freshness,
    filter_by_title,
)

# --- _slugify ---


def test_normalize_job_id():
    """ID normalization produces valid kebab-case."""
    assert _slugify("Senior Software Engineer") == "senior-software-engineer"
    assert _slugify("AI/ML Engineer (Remote)") == "aiml-engineer-remote"
    assert _slugify("Developer Advocate, Platform") == "developer-advocate-platform"


def test_slugify_truncation():
    """Long titles are truncated to 60 chars."""
    long_title = "A " * 50  # very long
    result = _slugify(long_title)
    assert len(result) <= 60


# --- create_pipeline_entry ---


def test_build_entry_yaml():
    """Generated entry has required schema fields."""
    job = {
        "title": "Software Engineer",
        "id": "12345",
        "url": "https://example.com/apply",
        "location": "San Francisco, CA",
        "company": "testco",
        "company_display": "TestCo",
        "portal": "greenhouse",
        "company_url": "https://boards.greenhouse.io/testco",
    }
    entry_id, entry = create_pipeline_entry(job)
    assert entry_id == "testco-software-engineer"
    assert entry["track"] == "job"
    assert entry["status"] == "research"
    assert entry["target"]["organization"] == "TestCo"
    assert entry["target"]["application_url"] == "https://example.com/apply"
    assert entry["target"]["portal"] == "greenhouse"
    assert "timeline" in entry
    assert "conversion" in entry
    assert "tags" in entry
    assert "auto-sourced" in entry["tags"]


# --- classify_location ---


def test_location_us_onsite():
    """US city classified as us-onsite."""
    assert classify_location("San Francisco, CA") == "us-onsite"


def test_location_us_remote():
    """Remote US classified as us-remote."""
    assert classify_location("Remote - US") == "us-remote"
    assert classify_location("United States (Remote)") == "us-remote"


def test_location_international():
    """International locations classified correctly."""
    assert classify_location("London, UK") == "international"
    assert classify_location("Tokyo, Japan") == "international"


def test_location_remote_global():
    """Plain 'Remote' classified as remote-global."""
    assert classify_location("Remote") == "remote-global"


def test_location_unknown():
    """Empty or ambiguous classified as unknown."""
    assert classify_location("") == "unknown"
    assert classify_location("   ") == "unknown"


def test_location_classes_complete():
    """All classify_location outputs are in VALID_LOCATION_CLASSES."""
    test_locs = ["San Francisco, CA", "Remote - US", "London, UK", "Remote", ""]
    for loc in test_locs:
        result = classify_location(loc)
        assert result in VALID_LOCATION_CLASSES, f"{loc!r} -> {result!r} not in valid set"


# --- filter_by_title ---


def test_filter_by_title_match():
    """Matching title passes filter."""
    jobs = [
        {"title": "Senior Software Engineer"},
        {"title": "Marketing Manager"},
    ]
    result = filter_by_title(jobs, ["software engineer"], ["intern"])
    assert len(result) == 1
    assert result[0]["title"] == "Senior Software Engineer"


def test_filter_by_title_exclude():
    """Excluded title filtered out."""
    jobs = [{"title": "Staff Engineer, Platform"}]
    result = filter_by_title(jobs, ["engineer"], ["staff engineer"])
    assert len(result) == 0


# --- _yaml_quote ---


def test_yaml_quote_plain():
    """Plain text without special chars should pass through unquoted."""
    assert _yaml_quote("hello world") == "hello world"


def test_yaml_quote_empty():
    """Empty string should produce empty single-quoted string."""
    assert _yaml_quote("") == "''"


def test_yaml_quote_single_quotes():
    """Text with special chars but no single quotes uses single quotes."""
    assert _yaml_quote("hello: world") == "'hello: world'"


def test_yaml_quote_has_single_quotes():
    """Text with single quotes should use double quotes."""
    assert _yaml_quote("it's a test") == '"it\'s a test"'


def test_yaml_quote_both_quote_types():
    """Text with both single and double quotes should escape double quotes."""
    result = _yaml_quote("""He said "it's fine" """.strip())
    assert result.startswith('"')
    assert result.endswith('"')
    # Should be valid — double quotes escaped inside
    assert '\\"' in result


# --- _strip_html ---


def test_strip_html_basic():
    """HTML tags are removed and entities unescaped."""
    result = _strip_html("<p>Hello &amp; World</p>")
    assert result == "Hello & World"


def test_strip_html_cap():
    """Output is capped at 5000 chars."""
    long_text = "a" * 10000
    result = _strip_html(long_text)
    assert len(result) == 5000


def test_strip_html_whitespace_collapsed():
    """Multiple whitespace is collapsed to single space."""
    result = _strip_html("<p>foo</p>   <p>bar</p>")
    assert result == "foo bar"


# --- description fetching: Greenhouse ---


def _make_greenhouse_list_response(jobs: list[dict]) -> bytes:
    return json.dumps({"jobs": jobs}).encode()


def _make_greenhouse_detail_response(content: str) -> bytes:
    return json.dumps({"id": 1, "title": "Eng", "content": content}).encode()


def test_greenhouse_description_fetched(monkeypatch):
    """Greenhouse jobs include description fetched from detail endpoint."""
    list_payload = _make_greenhouse_list_response([
        {"id": 111, "title": "Software Engineer", "absolute_url": "https://example.com/jobs/111",
         "location": {"name": "Remote"}, "updated_at": "2026-03-14T00:00:00Z"},
    ])
    detail_payload = _make_greenhouse_detail_response("<p>Build great things &amp; more.</p>")

    call_count = {"n": 0}

    def fake_http_get(url: str) -> bytes:
        call_count["n"] += 1
        if "/jobs/111" in url and url.endswith("/111"):
            return detail_payload
        return list_payload

    monkeypatch.setattr("source_jobs._http_get", fake_http_get)
    # Parallel implementation — no sleep to patch

    jobs = fetch_greenhouse_jobs(
        "testboard",
        title_keywords=["software engineer"],
        title_excludes=[],
    )
    assert len(jobs) == 1
    assert jobs[0]["description"] == "Build great things & more."
    assert call_count["n"] == 2  # list + detail


def test_greenhouse_description_only_for_filtered(monkeypatch):
    """Greenhouse only fetches detail for jobs that pass the title filter."""
    list_payload = _make_greenhouse_list_response([
        {"id": 1, "title": "Software Engineer", "absolute_url": "https://example.com/1",
         "location": {"name": "Remote"}, "updated_at": "2026-03-14T00:00:00Z"},
        {"id": 2, "title": "Marketing Manager", "absolute_url": "https://example.com/2",
         "location": {"name": "Remote"}, "updated_at": "2026-03-14T00:00:00Z"},
    ])

    detail_calls = []

    def fake_http_get(url: str) -> bytes:
        if url.endswith("/1") or url.endswith("/2"):
            detail_calls.append(url)
            return json.dumps({"content": "<p>desc</p>"}).encode()
        return list_payload

    monkeypatch.setattr("source_jobs._http_get", fake_http_get)
    # Parallel implementation — no sleep to patch

    fetch_greenhouse_jobs(
        "testboard",
        title_keywords=["software engineer"],
        title_excludes=[],
    )
    # Only the matching job's detail should have been fetched
    assert len(detail_calls) == 1
    assert detail_calls[0].endswith("/1")


def test_greenhouse_failed_detail_gives_empty_description(monkeypatch):
    """A failed Greenhouse detail fetch results in empty description, not a crash."""
    list_payload = _make_greenhouse_list_response([
        {"id": 999, "title": "Software Engineer", "absolute_url": "https://example.com/999",
         "location": {"name": "Remote"}, "updated_at": "2026-03-14T00:00:00Z"},
    ])

    def fake_http_get(url: str) -> bytes:
        if url.endswith("/999"):
            raise HTTPError(url, 404, "Not Found", {}, None)
        return list_payload

    monkeypatch.setattr("source_jobs._http_get", fake_http_get)
    # Parallel implementation — no sleep to patch

    jobs = fetch_greenhouse_jobs(
        "testboard",
        title_keywords=["software engineer"],
        title_excludes=[],
    )
    assert len(jobs) == 1
    assert jobs[0]["description"] == ""


# --- description fetching: Lever ---


def test_lever_description_from_plain(monkeypatch):
    """Lever jobs use descriptionPlain when available."""
    payload = json.dumps([
        {
            "id": "abc-123",
            "text": "Software Engineer",
            "hostedUrl": "https://jobs.lever.co/testco/abc-123",
            "applyUrl": "",
            "createdAt": 1700000000000,
            "categories": {"location": "Remote"},
            "descriptionPlain": "Build cool stuff.",
            "description": "<p>Build cool stuff.</p>",
        }
    ]).encode()

    monkeypatch.setattr("source_jobs._http_get", lambda url: payload)

    jobs = fetch_lever_jobs("testco")
    assert len(jobs) == 1
    assert jobs[0]["description"] == "Build cool stuff."


def test_lever_description_falls_back_to_html(monkeypatch):
    """Lever jobs strip HTML from description when descriptionPlain is absent."""
    payload = json.dumps([
        {
            "id": "def-456",
            "text": "Backend Engineer",
            "hostedUrl": "https://jobs.lever.co/testco/def-456",
            "applyUrl": "",
            "createdAt": 1700000000000,
            "categories": {"location": "Remote"},
            "description": "<p>Build &amp; ship fast.</p>",
        }
    ]).encode()

    monkeypatch.setattr("source_jobs._http_get", lambda url: payload)

    jobs = fetch_lever_jobs("testco")
    assert len(jobs) == 1
    assert jobs[0]["description"] == "Build & ship fast."


def test_lever_description_empty_when_missing(monkeypatch):
    """Lever jobs have empty description when neither field is present."""
    payload = json.dumps([
        {
            "id": "ghi-789",
            "text": "DevOps Engineer",
            "hostedUrl": "https://jobs.lever.co/testco/ghi-789",
            "applyUrl": "",
            "createdAt": 1700000000000,
            "categories": {"location": "Remote"},
        }
    ]).encode()

    monkeypatch.setattr("source_jobs._http_get", lambda url: payload)

    jobs = fetch_lever_jobs("testco")
    assert len(jobs) == 1
    assert jobs[0]["description"] == ""


# --- description fetching: Ashby ---


def test_ashby_description_from_html(monkeypatch):
    """Ashby jobs strip HTML from descriptionHtml."""
    payload = json.dumps({
        "jobs": [
            {
                "id": "ashby-job-1",
                "title": "Staff Engineer",
                "location": "Remote",
                "publishedDate": "2026-03-14",
                "descriptionHtml": "<h2>About the Role</h2><p>Build &amp; grow.</p>",
            }
        ]
    }).encode()

    monkeypatch.setattr("source_jobs._http_get", lambda url: payload)

    jobs = fetch_ashby_jobs("testco")
    assert len(jobs) == 1
    assert jobs[0]["description"] == "About the Role Build & grow."


def test_ashby_description_empty_when_missing(monkeypatch):
    """Ashby jobs have empty description when descriptionHtml is absent."""
    payload = json.dumps({
        "jobs": [
            {
                "id": "ashby-job-2",
                "title": "Data Engineer",
                "location": "New York, NY",
                "publishedDate": "2026-03-14",
            }
        ]
    }).encode()

    monkeypatch.setattr("source_jobs._http_get", lambda url: payload)

    jobs = fetch_ashby_jobs("testco")
    assert len(jobs) == 1
    assert jobs[0]["description"] == ""


# --- create_pipeline_entry includes description ---


def test_create_entry_includes_description():
    """Pipeline entry template includes description from job dict."""
    job = {
        "title": "Software Engineer",
        "id": "123",
        "url": "https://example.com/apply",
        "location": "Remote",
        "company": "testco",
        "company_display": "TestCo",
        "portal": "greenhouse",
        "company_url": "https://boards.greenhouse.io/testco",
        "description": "We build distributed systems at scale.",
    }
    _, entry = create_pipeline_entry(job)
    assert entry["target"]["description"] == "We build distributed systems at scale."


def test_create_entry_description_defaults_to_empty():
    """Pipeline entry target.description defaults to empty string when absent."""
    job = {
        "title": "Backend Engineer",
        "id": "456",
        "url": "https://example.com/apply2",
        "location": "Remote",
        "company": "testco",
        "company_display": "TestCo",
        "portal": "lever",
        "company_url": "https://jobs.lever.co/testco",
    }
    _, entry = create_pipeline_entry(job)
    assert entry["target"]["description"] == ""


# --- posting date accuracy ---


def test_greenhouse_uses_first_published(monkeypatch):
    """Greenhouse must use first_published, not updated_at, for posting_date."""
    list_payload = _make_greenhouse_list_response([
        {"id": 42, "title": "Software Engineer", "absolute_url": "https://example.com/42",
         "location": {"name": "Remote"},
         "first_published": "2026-01-15T09:00:00-05:00",
         "updated_at": "2026-03-29T22:00:00-04:00"},
    ])
    detail_payload = _make_greenhouse_detail_response("<p>desc</p>")

    def fake_http_get(url: str) -> bytes:
        if "/jobs/42" in url and url.endswith("/42"):
            return detail_payload
        return list_payload

    monkeypatch.setattr("source_jobs._http_get", fake_http_get)
    jobs = fetch_greenhouse_jobs("testboard", title_keywords=["software engineer"], title_excludes=[])
    assert len(jobs) == 1
    assert jobs[0]["posting_date"] == "2026-01-15", f"Expected first_published date, got {jobs[0]['posting_date']}"
    assert jobs[0]["date_source"] == "first_published"


def test_greenhouse_falls_back_to_updated_at(monkeypatch):
    """Without first_published, Greenhouse falls back to updated_at."""
    list_payload = _make_greenhouse_list_response([
        {"id": 43, "title": "Software Engineer", "absolute_url": "https://example.com/43",
         "location": {"name": "Remote"},
         "updated_at": "2026-03-29T22:00:00-04:00"},
    ])
    detail_payload = _make_greenhouse_detail_response("<p>desc</p>")

    def fake_http_get(url: str) -> bytes:
        if "/jobs/43" in url and url.endswith("/43"):
            return detail_payload
        return list_payload

    monkeypatch.setattr("source_jobs._http_get", fake_http_get)
    jobs = fetch_greenhouse_jobs("testboard", title_keywords=["software engineer"], title_excludes=[])
    assert len(jobs) == 1
    assert jobs[0]["posting_date"] == "2026-03-29"
    assert jobs[0]["date_source"] == "updated_at_fallback"


def test_ashby_uses_published_at(monkeypatch):
    """Ashby must use publishedAt (not the nonexistent publishedDate)."""
    payload = json.dumps({"jobs": [
        {"id": "ash-1", "title": "Software Engineer", "location": "Remote",
         "publishedAt": "2026-02-10T12:00:00+00:00",
         "updatedAt": "2026-03-30T08:00:00+00:00",
         "descriptionHtml": "<p>desc</p>"},
    ]}).encode()

    monkeypatch.setattr("source_jobs._http_get", lambda url: payload)
    jobs = fetch_ashby_jobs("testco")
    assert len(jobs) == 1
    assert jobs[0]["posting_date"] == "2026-02-10", f"Expected publishedAt date, got {jobs[0]['posting_date']}"
    assert jobs[0]["date_source"] == "published_at"


def test_filter_freshness_rejects_null_date():
    """Jobs without posting_date must be rejected, not given benefit of the doubt."""
    jobs = [
        {"title": "No Date Job", "posting_date": None},
        {"title": "Fresh Job", "posting_date": date.today().isoformat()},
    ]
    fresh, skipped = filter_by_freshness(jobs, max_hours=72)
    assert len(skipped) == 1
    assert skipped[0]["title"] == "No Date Job"


def test_filter_freshness_passes_recent():
    """Jobs within the freshness window pass."""
    from datetime import UTC, datetime, timedelta
    recent = (datetime.now(UTC) - timedelta(hours=12)).strftime("%Y-%m-%d")
    jobs = [{"title": "Fresh", "posting_date": recent}]
    fresh, skipped = filter_by_freshness(jobs, max_hours=72)
    assert len(fresh) == 1
    assert len(skipped) == 0


def test_filter_freshness_rejects_old():
    """Jobs outside the freshness window are rejected."""
    from datetime import UTC, datetime, timedelta
    old = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    jobs = [{"title": "Old", "posting_date": old}]
    fresh, skipped = filter_by_freshness(jobs, max_hours=72)
    assert len(fresh) == 0
    assert len(skipped) == 1


def test_date_source_persisted_in_pipeline_entry():
    """Pipeline entry timeline includes date_source from the job dict."""
    job = {
        "title": "Software Engineer",
        "id": "789",
        "url": "https://example.com/apply",
        "location": "Remote",
        "company": "testco",
        "company_display": "TestCo",
        "portal": "greenhouse",
        "company_url": "https://boards.greenhouse.io/testco",
        "posting_date": "2026-01-15",
        "date_source": "first_published",
    }
    _, entry = create_pipeline_entry(job)
    assert entry["timeline"]["date_source"] == "first_published"
