#!/usr/bin/env python3
"""Handoff Seed Generator — Protocol SOP-SYS-003.

Aggregates system state into a persistent "soul" for the next session ignition.
"""

import subprocess

import yaml


def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception:
        return "N/A"

def main():
    sha = run("git rev-parse HEAD")
    session_id = "S48" # Contextually known, should ideally be tracked in a file

    # Determine momentum (next logical step)
    # If there are overdue followups, the next step is to log them or generate them.
    followups = run("uv run scripts/followup.py")
    overdue_count = followups.count("[OVERDUE")
    
    momentum = "uv run scripts/followup.py --overdue"
    if overdue_count > 0:
        momentum = f"uv run scripts/followup.py --overdue # {overdue_count} actions awaiting log/execution"

    seed = {
        "session_id": session_id,
        "status": "IGNITION",
        "head": "IRF-APP-072", # Fix location vacuums
        "momentum": momentum,
        "context": "S48: Sync'd inbox (2 interviews, 2 rejections), triaged pipeline (deferred 5 for org-cap), updated universal IRF registry. Git parity 1:1.",
        "vacuums": [
            "location: N/A in 16 entries",
            "Interview prep for Snorkel AI and Grafana Labs"
        ],
        "checksum": sha
    }

    print("<avalanche_seed>")
    print(yaml.dump(seed, sort_keys=False))
    print("</avalanche_seed>")

if __name__ == "__main__":
    main()
