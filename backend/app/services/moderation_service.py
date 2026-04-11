# app/services/moderation_service.py
# Phase 2 — Multi-layer content moderation
#
# Layer 1: Hard-block list  (instant reject, no mercy)
# Layer 2: Soft-flag list   (score += weight, human review if total >= threshold)
# Layer 3: Regex patterns   (phone numbers, URLs, personal info, threats)
# Layer 4: Heuristics       (ALL CAPS, repeated chars, suspiciously short)
#
# Returns a ModerationResult dataclass.
# Future: swap Layer 4 with an ML model (e.g. Perspective API / TensorFlow)

import re
from dataclasses import dataclass, field
from app.models.confession import ModerationStatus


# ── Word lists ────────────────────────────────────────────────────────────────

# Hard-block: instant rejection regardless of context
_HARD_BLOCK: set[str] = {
    # severe abuse / slurs — add your full list here
    "kill yourself", "kys", "rape", "child abuse",
    "cp", "csam", "bomb threat", "terrorist",
}

# Soft-flag: adds to toxicity score, triggers human review above threshold
_SOFT_FLAG: dict[str, float] = {
    # harassment
    "idiot":       0.2,
    "stupid":      0.2,
    "loser":       0.2,
    "worthless":   0.3,
    "ugly":        0.2,
    "fat":         0.15,
    "retard":      0.4,
    "moron":       0.25,
    # hate speech lite
    "hate":        0.1,
    "disgusting":  0.15,
    # drug references
    "weed":        0.1,
    "drugs":       0.1,
    "cocaine":     0.35,
    # explicit
    "sex":         0.1,
    "porn":        0.35,
    "naked":       0.2,
    "nudes":       0.4,
}

# Regex patterns
_PHONE_RE    = re.compile(r"(\+91|0)?[6-9]\d{9}")
_URL_RE      = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE    = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_THREAT_RE   = re.compile(
    r"\b(i will (kill|hurt|find|destroy)|i know where you|watch your back)\b",
    re.IGNORECASE,
)
_REPEAT_RE   = re.compile(r"(.)\1{5,}")   # "aaaaaa" or "!!!!!!!"


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ModerationResult:
    status:      ModerationStatus
    score:       float                  # 0.0 (clean) → 1.0 (very toxic)
    reasons:     list[str] = field(default_factory=list)
    is_approved: bool = False

    @property
    def should_reject(self) -> bool:
        return self.status == ModerationStatus.rejected

    @property
    def should_flag(self) -> bool:
        return self.status == ModerationStatus.flagged


# ── Main moderation function ──────────────────────────────────────────────────

def moderate(text: str) -> ModerationResult:
    """
    Run all moderation layers on the given text.
    Returns a ModerationResult with status, score, and reasons list.
    """
    reasons: list[str] = []
    score:   float     = 0.0
    lower_text = text.lower()

    # ── Layer 1: Hard-block ───────────────────────────────────────────────────
    for phrase in _HARD_BLOCK:
        if phrase in lower_text:
            return ModerationResult(
                status=ModerationStatus.rejected,
                score=1.0,
                reasons=[f"Hard-blocked phrase detected: '{phrase}'"],
                is_approved=False,
            )

    # ── Layer 2: Soft-flag words ──────────────────────────────────────────────
    for word, weight in _SOFT_FLAG.items():
        if word in lower_text:
            score += weight
            reasons.append(f"Flagged word: '{word}' (+{weight})")

    # ── Layer 3: Regex patterns ───────────────────────────────────────────────
    if _PHONE_RE.search(text):
        score += 0.3
        reasons.append("Contains phone number (+0.3)")

    if _URL_RE.search(text):
        score += 0.2
        reasons.append("Contains URL (+0.2)")

    if _EMAIL_RE.search(text):
        score += 0.2
        reasons.append("Contains email address (+0.2)")

    if _THREAT_RE.search(text):
        score += 0.6
        reasons.append("Contains threatening language (+0.6)")

    if _REPEAT_RE.search(text):
        score += 0.1
        reasons.append("Excessive character repetition (+0.1)")

    # ── Layer 4: Heuristics ───────────────────────────────────────────────────
    words = text.split()

    # ALL CAPS yelling (>70% of words are all caps and text is not tiny)
    if len(words) > 4:
        caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / len(words)
        if caps_ratio > 0.70:
            score += 0.15
            reasons.append(f"Excessive all-caps ({caps_ratio:.0%} of words) (+0.15)")

    # Suspiciously short — not necessarily bad, just reduce trust
    if len(text.strip()) < 15:
        score += 0.05
        reasons.append("Very short content (+0.05)")

    # ── Cap score at 1.0 ──────────────────────────────────────────────────────
    score = min(round(score, 3), 1.0)

    # ── Decide final status ───────────────────────────────────────────────────
    if score >= 0.7:
        status = ModerationStatus.rejected
    elif score >= 0.35:
        status = ModerationStatus.flagged   # human review queue
    else:
        status = ModerationStatus.approved

    return ModerationResult(
        status=status,
        score=score,
        reasons=reasons,
        is_approved=(status == ModerationStatus.approved),
    )


# ── Comment moderation (lighter check) ────────────────────────────────────────

def moderate_comment(text: str) -> ModerationResult:
    """Comments use the same moderation thresholds as confessions in Phase 3."""
    return moderate(text)
