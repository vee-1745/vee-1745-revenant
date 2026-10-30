"""Spirit loading + persistent state (which spirit/model is currently summoned)."""
import json
import os
import tomllib
from pathlib import Path

SPIRIT_DIR = Path(__file__).resolve().parent / "spirits"
STATE_DIR = Path(os.environ.get("REVENANT_STATE_DIR", Path.home() / ".revenant"))
STATE_FILE = STATE_DIR / "state.json"
DEFAULT_SPIRIT = "cobol"


def names():
    return sorted(p.stem for p in SPIRIT_DIR.glob("*.toml"))


def load(name):
    path = SPIRIT_DIR / f"{name}.toml"
    if not path.exists():
        raise KeyError(f"no such spirit: {name} (known: {', '.join(names())})")
    with path.open("rb") as f:
        data = tomllib.load(f)
    data.setdefault("name", name)
    data.setdefault("examples", [])
    return data


def read_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def write_state(**updates):
    state = read_state()
    for key, value in updates.items():
        if value is None:
            state.pop(key, None)  # None clears a stored setting
        else:
            state[key] = value
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))
    return state


def current():
    name = read_state().get("spirit", DEFAULT_SPIRIT)
    if name not in names():
        name = DEFAULT_SPIRIT
    return load(name)
