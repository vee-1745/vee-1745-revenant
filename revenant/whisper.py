"""Decide when to haunt, build the prompt, and clean up the model's reply."""
import random
import re
import time

from . import ollama

DANGEROUS = [
    r"\brm\s+-[a-z]*r[a-z]*f", r"\brm\s+-[a-z]*f[a-z]*r", r"--force\b", r"\bpush\s+-f\b",
    r"\breset\s+--hard", r"\bchmod\s+-R\s+777", r"\bdrop\s+(table|database)\b",
    r"\bmkfs\b", r"\bdd\s+if=", r">\s*/dev/sd", r"\bsudo\b", r"\bkill\s+-9\b", r":\(\)\s*\{",
]
_DANGER_RE = re.compile("|".join(DANGEROUS), re.IGNORECASE)

_REFUSALS = ("as an ai", "i'm sorry", "i am sorry", "i can't", "i cannot", "language model")


def should_haunt(cmd, exit_code, chance=0.15, force=False):
    """Haunt every failure and dangerous command; sprinkle in some random ones."""
    if force:
        return True
    if not cmd.strip():
        return False
    if exit_code != 0 or _DANGER_RE.search(cmd):
        return True
    return random.random() < chance


def describe(cmd, exit_code):
    status = "it succeeded" if exit_code == 0 else f"it FAILED with exit code {exit_code}"
    return f"The user just ran: {cmd}\n({status})"


def copied_from_example(spirit, text):
    """True if the reply is (near-)verbatim one of the few-shot lines: the model parroted."""
    norm = lambda s: re.sub(r"\W+", " ", s.lower()).strip()
    t = norm(text)
    return any(norm(ex["ghost"]) == t for ex in spirit["examples"])


def build_messages(spirit, cmd, exit_code, k=4):
    """System prompt + k RANDOM few-shot turns (random so the model can't memorise one set)."""
    msgs = [{"role": "system", "content": spirit["system"]}]
    examples = [e for e in spirit["examples"] if e["cmd"] != cmd]
    for ex in random.sample(examples, min(k, len(examples))):
        msgs.append({"role": "user", "content": describe(ex["cmd"], ex.get("exit", 0))})
        msgs.append({"role": "assistant", "content": ex["ghost"]})
    msgs.append({"role": "user", "content": describe(cmd, exit_code)})
    return msgs


def clean(text, limit=170):
    """First non-empty line, no wrapper quotes or role prefixes, trimmed at a word boundary."""
    for line in text.splitlines():
        line = line.strip().strip("`").strip()
        if line:
            break
    else:
        return None
    line = re.sub(r"^(ghost|spirit|assistant)\s*:\s*", "", line, flags=re.IGNORECASE)
    line = line.strip("\"'“”")
    if not line or any(r in line.lower() for r in _REFUSALS):
        return None
    if len(line) > limit:
        line = line[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return line


MAX_WORDS = 25

# Advice-shaped phrasing: a ghost never helps. (Scorn like "you should have used a macro" is fine.)
ADVICE_RE = re.compile(
    r"\b(check (your|the|for)|ensure|make sure|be careful|careful|beware|be cautious|cautious|"
    r"consider|try (again|a|using|to)|perhaps (a|use|review|try)|maybe (use|try)|"
    r"remember to|double[- ]check)\b",
    re.IGNORECASE,
)


def grade(spirit, text):
    """(in_character, advice_free) using the spirit's [checks] table plus the global advice ban."""
    checks = spirit.get("checks", {})
    in_char = True
    if "min_upper_ratio" in checks:
        letters = [c for c in text if c.isalpha()]
        in_char = bool(letters) and sum(c.isupper() for c in letters) / len(letters) >= checks["min_upper_ratio"]
    if in_char and "must_match" in checks:
        in_char = re.search(checks["must_match"], text, re.IGNORECASE) is not None
    return in_char, ADVICE_RE.search(text) is None


def whisper_detailed(spirit, cmd, exit_code, model=None, timeout=20, attempts=2, budget=None):
    """Generate up to `attempts` times and return the first reply that passes every check.

    Returns {"text": str|None, "tries": int, "first": {...flags for the first attempt...}}.
    text is None when no attempt passed: the ghost stays silent rather than say something generic.
    """
    first = {"ok": False, "in_character": False, "advice_free": False, "copied": False}
    tries = 0
    # `budget` caps the TOTAL wall time (all retries) so the shell prompt is never held hostage.
    deadline = time.monotonic() + budget if budget else None
    for i in range(max(1, attempts)):
        t = timeout
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if i > 0 and remaining <= 0.3:
                break
            t = max(0.3, min(timeout, remaining))
        reply = ollama.chat(build_messages(spirit, cmd, exit_code), model,
                            num_predict=60, temperature=0.9, timeout=t)
        tries += 1
        text = clean(reply)
        flags = {"ok": False, "in_character": False, "advice_free": False, "copied": False}
        if text:
            in_char, advice_free = grade(spirit, text)
            copied = copied_from_example(spirit, text)
            flags = {"in_character": in_char, "advice_free": advice_free, "copied": copied,
                     "ok": in_char and advice_free and not copied and len(text.split()) <= MAX_WORDS}
        if i == 0:
            first = flags
        if text and flags["ok"]:
            return {"text": text, "tries": tries, "first": first}
    return {"text": None, "tries": tries, "first": first}


def whisper(spirit, cmd, exit_code, model=None, timeout=20, attempts=2, budget=None):
    return whisper_detailed(spirit, cmd, exit_code, model, timeout, attempts, budget)["text"]
