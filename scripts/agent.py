#!/usr/bin/env python3
"""Autonomous pipeline agent: reads state, decides actions, executes.

The agent loops through the pipeline state machine, making decisions based on
rules (e.g., "score >= 7 AND deadline < 7 days → submit"). This enables
unattended batch processing while maintaining human decision-making authority.

Usage:
    python scripts/agent.py --plan                  # Show planned actions (dry-run)
    python scripts/agent.py --execute --yes         # Execute autonomously
    python scripts/agent.py --target <id> --yes     # Single entry
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_api import (
    ResultStatus,
    advance_entry,
    score_entry,
)
from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    SIGNALS_DIR,
    can_advance,
    get_deadline,
    is_actionable,
    load_entries,
)

# --- Agent rules loader ---

_RULES_PATH = Path(__file__).resolve().parent.parent / "strategy" / "agent-rules.yaml"


def _load_agent_rules() -> dict:
    """Load agent decision rules from YAML, falling back to defaults."""
    if _RULES_PATH.exists():
        try:
            with open(_RULES_PATH) as f:
                data = yaml.safe_load(f) or {}
            return data.get("rules", {})
        except Exception:
            pass
    return {}


_RULES = _load_agent_rules()

# Extract configurable thresholds from rules YAML (with hardcoded fallback)
RESEARCH_QUALIFY_THRESHOLD = _RULES.get("advance_research_to_qualified", {}).get("threshold", 7.0)
QUALIFIED_DRAFTING_THRESHOLD = _RULES.get("advance_qualified_to_drafting", {}).get("threshold", 8.0)
DRAFTING_STAGED_MIN_DAYS = _RULES.get("advance_drafting_to_staged", {}).get("min_days", 7)
DRAFTING_STAGED_MIN_SCORE = _RULES.get("advance_drafting_to_staged", {}).get("min_score", 9.0)
STAGED_SUBMIT_MAX_DAYS = _RULES.get("flag_staged_for_submission", {}).get("max_days", 7)
CHANNEL_ALLOCATOR_ENABLED = _RULES.get("channel_allocator", {}).get("enabled", True)
CHANNEL_ALLOCATOR_MIN_SAMPLES = _RULES.get("channel_allocator", {}).get("min_samples", 3)
ADAPTIVE_ENABLED = _RULES.get("adaptive_feedback", {}).get("enabled", True)
ADAPTIVE_MIN_SAMPLES = _RULES.get("adaptive_feedback", {}).get("min_samples", 12)
ADAPTIVE_WINDOW_MONTHS = _RULES.get("adaptive_feedback", {}).get("window_months", 3)


def _rule_enabled(rule_name: str) -> bool:
    """Check if a rule is enabled in config (defaults to True)."""
    return _RULES.get(rule_name, {}).get("enabled", True)


def _mode_adjusted_threshold(base: float) -> float:
    """Return the higher of base threshold and mode-required minimum.

    Mode can only raise thresholds, never lower them.
    """
    try:
        from pipeline_lib import get_mode_thresholds
        t = get_mode_thresholds()
        mode_min = float(t.get("auto_qualify_min", 0))
        return max(base, mode_min)
    except ImportError:
        return base


def compute_channel_allocator(entries: list[dict], min_samples: int = 3) -> dict[str, float]:
    """Build track allocator multipliers from resolved outcomes."""
    focus_tracks = {"job", "grant", "fellowship"}
    stats = {
        track: {"resolved": 0, "accepted": 0}
        for track in focus_tracks
    }
    overall_resolved = 0
    overall_accepted = 0

    for entry in entries:
        track = entry.get("track")
        if track not in focus_tracks:
            continue
        outcome = entry.get("outcome")
        if outcome not in {"accepted", "rejected", "withdrawn", "expired"}:
            continue
        stats[track]["resolved"] += 1
        overall_resolved += 1
        if outcome == "accepted":
            stats[track]["accepted"] += 1
            overall_accepted += 1

    if overall_resolved < max(1, min_samples):
        return {track: 1.0 for track in focus_tracks}

    overall_rate = overall_accepted / overall_resolved
    allocator: dict[str, float] = {}
    for track in focus_tracks:
        resolved = stats[track]["resolved"]
        if resolved < min_samples:
            allocator[track] = 1.0
            continue
        track_rate = stats[track]["accepted"] / resolved
        # Convert relative conversion advantage into a bounded multiplier.
        raw = 1.0 + ((track_rate - overall_rate) * 2.0)
        # Keep a floor, but preserve enough spread to distinguish weak tracks.
        allocator[track] = round(max(0.65, min(1.25, raw)), 3)
    return allocator


def compute_feedback_adjustment(months: int = 3) -> dict:
    """Compute threshold adjustment from recent conversion and hypothesis accuracy."""
    try:
        from validate_hypotheses import (
            accuracy_stats,
            build_outcome_map,
            load_hypotheses,
            validate,
        )
        from validate_hypotheses import (
            load_conversion_log as load_hypothesis_log,
        )
        from velocity_report import calculate_metrics, filter_by_date_range, load_conversion_log
    except Exception:
        return {
            "delta": 0.0,
            "conversion_rate": None,
            "hypothesis_accuracy": None,
            "resolved_hypotheses": 0,
        }

    # Conversion-based signal (0-1 scale).
    raw_conversion = load_conversion_log()
    recent_conversion = filter_by_date_range(raw_conversion, months=months)
    metrics = calculate_metrics(recent_conversion)
    conversion_rate = float(metrics.get("conversion_rate", 0.0))

    # Hypothesis signal (percentage scale).
    hypotheses = load_hypotheses()
    outcomes = build_outcome_map(load_hypothesis_log())
    validated = validate(hypotheses, outcomes)
    hyp_stats = accuracy_stats(validated)
    hypothesis_accuracy = float(hyp_stats.get("accuracy", 0.0))
    resolved_hypotheses = int(hyp_stats.get("resolved", 0))

    delta = 0.0
    if conversion_rate < 0.10:
        delta += 0.25
    elif conversion_rate > 0.20:
        delta -= 0.15

    if resolved_hypotheses >= ADAPTIVE_MIN_SAMPLES:
        if hypothesis_accuracy < 50.0:
            delta += 0.15
        elif hypothesis_accuracy > 70.0:
            delta -= 0.10

    return {
        "delta": round(max(-0.5, min(0.5, delta)), 2),
        "conversion_rate": round(conversion_rate, 3),
        "hypothesis_accuracy": round(hypothesis_accuracy, 1),
        "resolved_hypotheses": resolved_hypotheses,
    }


class PipelineAgent:
    """Autonomous agent for pipeline state transitions."""

    def __init__(self, dry_run: bool = True, full_cycle: bool = False):
        self.dry_run = dry_run
        self.full_cycle = full_cycle
        self.actions_planned = []
        self.actions_executed = []
        self.errors = []
        self.started_at = datetime.now()
        self.channel_allocator: dict[str, float] = {}
        self.feedback_summary: dict = {
            "delta": 0.0,
            "conversion_rate": None,
            "hypothesis_accuracy": None,
            "resolved_hypotheses": 0,
        }

    def plan_actions(self, entries: list[dict]) -> list[dict]:
        """Analyze pipeline state; return planned actions.

        Rules loaded from strategy/agent-rules.yaml:
        0. Full-cycle: scan for new postings (if --full-cycle)
        1. Research entries: auto-score if no score
        2. Research + score >= threshold: auto-advance to qualified
        3. Qualified + score >= threshold: auto-advance to drafting
        4. Drafting + deadline > min_days: auto-advance to staged
        5. Staged + deadline < max_days: flag for submission
        """
        actions = []

        # Phase 0: Scan for new entries (full-cycle mode only)
        if self.full_cycle and _rule_enabled("daily_scan"):
            actions.append({
                "entry_id": "batch",
                "action": "scan",
                "reason": "full-cycle: discover new postings",
                "severity": "routine",
            })
        if CHANNEL_ALLOCATOR_ENABLED:
            self.channel_allocator = compute_channel_allocator(entries, min_samples=CHANNEL_ALLOCATOR_MIN_SAMPLES)
        else:
            self.channel_allocator = {"job": 1.0, "grant": 1.0, "fellowship": 1.0}
        if ADAPTIVE_ENABLED:
            self.feedback_summary = compute_feedback_adjustment(months=ADAPTIVE_WINDOW_MONTHS)
        else:
            self.feedback_summary = {
                "delta": 0.0,
                "conversion_rate": None,
                "hypothesis_accuracy": None,
                "resolved_hypotheses": 0,
            }

        base_research_threshold = _mode_adjusted_threshold(RESEARCH_QUALIFY_THRESHOLD + self.feedback_summary["delta"])
        base_qualified_threshold = _mode_adjusted_threshold(QUALIFIED_DRAFTING_THRESHOLD + self.feedback_summary["delta"])
        base_drafting_threshold = _mode_adjusted_threshold(DRAFTING_STAGED_MIN_SCORE + self.feedback_summary["delta"])

        for entry in entries:
            if not is_actionable(entry):
                continue

            entry_id = entry.get("id", "?")
            status = entry.get("status", "?")
            track = entry.get("track", "unknown")
            score = entry.get("fit", {}).get("composite") if isinstance(entry.get("fit"), dict) else None
            deadline_date, deadline_type = get_deadline(entry)
            days_left = (deadline_date - datetime.now().date()).days if deadline_date else None
            allocation_multiplier = self.channel_allocator.get(track, 1.0)
            track_bias = (1.0 - allocation_multiplier) * 0.5
            research_threshold = round(base_research_threshold + track_bias, 2)
            qualified_threshold = round(base_qualified_threshold + track_bias, 2)
            drafting_threshold = round(base_drafting_threshold + track_bias, 2)

            # Rule 1: Research entries without scores
            if status == "research" and not score and _rule_enabled("score_unscored_research"):
                actions.append({
                    "entry_id": entry_id,
                    "action": "score",
                    "reason": "research entry lacks score",
                    "severity": "routine",
                })

            # Rule 2: Research + score >= threshold
            elif (status == "research" and score and score >= research_threshold
                  and _rule_enabled("advance_research_to_qualified")):
                can_adv, reason = can_advance(entry, "qualified")
                if can_adv:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "advance",
                        "to_status": "qualified",
                        "reason": f"research with score {score} (threshold {research_threshold}, alloc {allocation_multiplier:.2f})",
                        "severity": "routine",
                    })

            # Rule 3: Qualified, score >= threshold
            elif (status == "qualified" and score and score >= qualified_threshold
                  and _rule_enabled("advance_qualified_to_drafting")):
                can_adv, reason = can_advance(entry, "drafting")
                if can_adv:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "advance",
                        "to_status": "drafting",
                        "reason": f"qualified with score {score} (threshold {qualified_threshold}, alloc {allocation_multiplier:.2f})",
                        "severity": "routine",
                    })

            # Rule 4: Drafting, deadline > min_days AND score >= min_score AND materials ready
            elif status == "drafting" and _rule_enabled("advance_drafting_to_staged"):
                submission = entry.get("submission") or {}
                has_materials = bool(
                    (submission.get("materials_attached") or [])
                    or (submission.get("blocks_used") or {})
                    or (submission.get("variant_ids") or {})
                )
                if not has_materials:
                    pass  # skip — no materials attached yet
                elif (days_left and days_left > DRAFTING_STAGED_MIN_DAYS
                        and score and score >= drafting_threshold):
                    can_adv, reason = can_advance(entry, "staged")
                    if can_adv:
                        actions.append({
                            "entry_id": entry_id,
                            "action": "advance",
                            "to_status": "staged",
                            "reason": (
                                f"drafting with {days_left}d until deadline, score {score} "
                                f"(threshold {drafting_threshold}, alloc {allocation_multiplier:.2f})"
                            ),
                            "severity": "routine",
                        })

            # Rule 5: Staged, deadline within the submission window (excl. expired)
            elif status == "staged" and _rule_enabled("flag_staged_for_submission"):
                if days_left is not None and 0 <= days_left < STAGED_SUBMIT_MAX_DAYS:
                    actions.append({
                        "entry_id": entry_id,
                        "action": "flag_for_submission",
                        "reason": f"staged with {days_left}d until deadline",
                        "severity": "urgent",
                    })

        return actions
    
    def execute_actions(self, actions: list[dict]) -> None:
        """Execute planned actions."""
        for action in actions:
            entry_id = action["entry_id"]
            action_type = action["action"]
            
            try:
                if action_type == "score":
                    result = score_entry(entry_id=entry_id, dry_run=self.dry_run)
                    if result.status in (ResultStatus.SUCCESS, ResultStatus.DRY_RUN):
                        self.actions_executed.append(action)
                    else:
                        self.errors.append((entry_id, f"score failed: {result.error}"))
                
                elif action_type == "advance":
                    target_status = action.get("to_status")
                    result = advance_entry(
                        entry_id=entry_id,
                        to_status=target_status,
                        dry_run=self.dry_run,
                    )
                    if result.status in (ResultStatus.SUCCESS, ResultStatus.DRY_RUN):
                        self.actions_executed.append(action)
                    else:
                        self.errors.append((entry_id, f"advance failed: {result.error}"))
                
                elif action_type == "scan":
                    try:
                        from scan_orchestrator import scan_all
                        result = scan_all(dry_run=self.dry_run)
                        self.actions_executed.append({
                            **action,
                            "result": f"found {result.total_qualified} new entries",
                        })
                    except Exception as e:
                        self.errors.append((entry_id, f"scan: {e}"))
                    continue

                elif action_type == "flag_for_submission":
                    # Don't auto-submit; just flag
                    self.actions_executed.append(action)

            except Exception as e:
                self.errors.append((entry_id, str(e)))
    
    def report(self) -> str:
        """Generate agent report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"PIPELINE AGENT REPORT ({datetime.now().isoformat()})")
        lines.append(f"Mode: {'DRY-RUN' if self.dry_run else 'EXECUTE'}")
        lines.append("=" * 70)
        
        lines.append(f"\n📋 PLANNED ACTIONS: {len(self.actions_planned)}")
        lines.append(
            "   Adaptive feedback: "
            f"delta={self.feedback_summary.get('delta', 0.0):+.2f}, "
            f"conversion={self.feedback_summary.get('conversion_rate')}, "
            f"hyp_acc={self.feedback_summary.get('hypothesis_accuracy')}% "
            f"(resolved={self.feedback_summary.get('resolved_hypotheses')})"
        )
        if self.channel_allocator:
            alloc_bits = ", ".join(f"{k}={v:.2f}" for k, v in sorted(self.channel_allocator.items()))
            lines.append(f"   Channel allocator: {alloc_bits}")
        for action in self.actions_planned:
            severity_marker = "🔴" if action["severity"] == "urgent" else "🟡"
            lines.append(f"  {severity_marker} {action['entry_id']}: {action['action']} "
                        f"({action['reason']})")
        
        lines.append(f"\n✅ EXECUTED ACTIONS: {len(self.actions_executed)}")
        for action in self.actions_executed:
            lines.append(f"  ✓ {action['entry_id']}: {action['action']}")
        
        if self.errors:
            lines.append(f"\n❌ ERRORS: {len(self.errors)}")
            for entry_id, error in self.errors:
                lines.append(f"  ✗ {entry_id}: {error}")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def write_run_log(self) -> None:
        """Persist run summary for standup visibility and automation audits."""
        log_path = SIGNALS_DIR / "agent-actions.yaml"
        SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

        if log_path.exists():
            try:
                with open(log_path) as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                data = {}
        else:
            data = {}

        runs = data.get("runs", [])
        if not isinstance(runs, list):
            runs = []

        run_record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "mode": "execute" if not self.dry_run else "plan",
            "planned": len(self.actions_planned),
            "executed": len(self.actions_executed),
            "errors": len(self.errors),
            "urgent": sum(1 for a in self.actions_planned if a.get("severity") == "urgent"),
            "action_types": sorted({a.get("action", "unknown") for a in self.actions_planned}),
            "duration_seconds": int((datetime.now() - self.started_at).total_seconds()),
        }
        runs.append(run_record)
        data["runs"] = runs[-100:]

        with open(log_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Autonomous pipeline agent")
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show planned actions (dry-run)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute autonomous actions"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation for execute"
    )
    parser.add_argument(
        "--target",
        help="Single entry ID (optional; all if not given)"
    )
    parser.add_argument(
        "--full-cycle",
        action="store_true",
        help="Run scan→match→build before score→advance",
    )
    args = parser.parse_args()

    if not (args.plan or args.execute):
        parser.print_help()
        sys.exit(1)

    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    if args.target:
        entries = [e for e in entries if e.get("id") == args.target]
        if not entries:
            print(f"Entry not found: {args.target}", file=sys.stderr)
            sys.exit(1)

    agent = PipelineAgent(dry_run=not args.execute, full_cycle=args.full_cycle)
    
    # Plan actions
    agent.actions_planned = agent.plan_actions(entries)
    
    # Show plan
    print(agent.report())
    
    # Execute if requested
    if args.execute:
        if not args.yes:
            response = input("\nExecute planned actions? (yes/no): ")
            if response.lower() != "yes":
                print("Cancelled")
                sys.exit(0)
        
        agent.execute_actions(agent.actions_planned)
        print("\n" + agent.report())

        # Dispatch notification
        try:
            from notify import dispatch_event
            results = dispatch_event("agent_action", {
                "summary": f"Agent executed {len(agent.actions_planned)} actions",
                "actions": [a.get("action", "") for a in agent.actions_planned[:10]],
            })
            for r in results:
                status = "OK" if r["success"] else "FAILED"
                print(f"  Notification [{r['channel']}]: {status} — {r['message']}")
        except ImportError:
            pass

    agent.write_run_log()


if __name__ == "__main__":
    main()
