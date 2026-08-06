"""Reputation math + faction inference. Per meta/community.md.

Reputation events:
  submission_accepted_t1:  +5
  submission_accepted_t2:  +20
  submission_accepted_t3:  +100
  submission_rejected_spam: -10
  submission_rejected_vote: 0
  vote_with_majority:       +1
  vote_against_majority:    -1
  comment_helpful:          +3
  comment_spam:             -5

Faction inference:
  ai_truster:  > 70% of votes are 'disagree' on submissions challenging AI verdicts
  ai_skeptic:  > 70% of votes are 'agree' on those submissions
  neutral:     30%-70%
  unknown:     < 10 votes
"""
from __future__ import annotations

import math
from typing import Iterable


REPUTATION_EVENTS = {
    "submission_accepted_t1": 5,
    "submission_accepted_t2": 20,
    "submission_accepted_t3": 100,
    "submission_rejected_spam": -10,
    "submission_rejected_vote": 0,
    "vote_with_majority": 1,
    "vote_against_majority": -1,
    "comment_helpful": 3,
    "comment_spam": -5,
}

THRESHOLDS = {
    "vote": 50,         # min rep to vote
    "submission": 0,    # anyone may submit (gates filter)
    "moderator": 1000,  # min rep to moderate
}

VOTE_WEIGHT_CAP = 10.0


def vote_weight(reputation: int) -> float:
    """Weight = sqrt(rep), capped."""
    return min(math.sqrt(max(reputation, 0)), VOTE_WEIGHT_CAP)


def apply_event(rep: int, event: str) -> int:
    """Pure function, returns new rep after event."""
    delta = REPUTATION_EVENTS.get(event, 0)
    return max(0, rep + delta)


def infer_faction(votes: Iterable[dict]) -> str:
    """Given user's vote history (list of {submission_type, vote}), classify faction.

    Heuristic: look at votes on submissions of type 'challenge'.
    - 'agree' = challenges AI verdict (skeptic-leaning)
    - 'disagree' = supports AI verdict (truster-leaning)
    """
    challenge_votes = [v for v in votes if v.get("submission_type") == "challenge"]
    if len(challenge_votes) < 10:
        return "unknown"
    n_agree = sum(1 for v in challenge_votes if v["vote"] == "agree")
    pct_agree = n_agree / len(challenge_votes)
    if pct_agree > 0.7:
        return "ai_skeptic"
    if pct_agree < 0.3:
        return "ai_truster"
    return "neutral"
