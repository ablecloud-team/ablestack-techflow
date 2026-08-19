#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib


EMPTY_FINGERPRINT = hashlib.sha256(b"").hexdigest()


def decide_notification(
    *,
    current_count: int,
    current_fingerprint: str,
    previous_fingerprint: str,
    last_sent_epoch: int,
    current_epoch: int,
    cooldown_seconds: int,
) -> str:
    """Return alert, recovery, or none for the observed state transition."""
    state_changed = current_fingerprint != previous_fingerprint
    previous_alerting = bool(previous_fingerprint) and previous_fingerprint != EMPTY_FINGERPRINT

    if current_count > 0:
        if state_changed or current_epoch - last_sent_epoch >= cooldown_seconds:
            return "alert"
        return "none"

    if previous_alerting and state_changed:
        return "recovery"
    return "none"


def main() -> int:
    parser = argparse.ArgumentParser(description="Community alert transition policy")
    parser.add_argument("--current-count", required=True, type=int)
    parser.add_argument("--current-fingerprint", required=True)
    parser.add_argument("--previous-fingerprint", default="")
    parser.add_argument("--last-sent-epoch", default=0, type=int)
    parser.add_argument("--current-epoch", required=True, type=int)
    parser.add_argument("--cooldown-seconds", required=True, type=int)
    args = parser.parse_args()
    print(
        decide_notification(
            current_count=args.current_count,
            current_fingerprint=args.current_fingerprint,
            previous_fingerprint=args.previous_fingerprint,
            last_sent_epoch=args.last_sent_epoch,
            current_epoch=args.current_epoch,
            cooldown_seconds=args.cooldown_seconds,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
