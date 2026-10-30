"""`ghost` command line: whisper, summon, spirits, doctor, demo, bench, hook."""
import argparse
import statistics
import sys
import time
from pathlib import Path

from . import __version__, ollama, spirits, whisper as whisper_mod

ROOT = Path(__file__).resolve().parent.parent
HOOK_DIR = Path(__file__).resolve().parent / "hooks"

ANSI = {
    "black": 30, "red": 31, "green": 32, "yellow": 33,
    "blue": 34, "magenta": 35, "cyan": 36, "white": 37,
}
RESET, DIM = "\033[0m", "\033[2m"


def paint(text, color="white", dim=False):
    if not sys.stdout.isatty():
        return text
    return f"\033[{ANSI.get(color, 37)}m{DIM if dim else ''}{text}{RESET}"


def model_for(spirit):
    """An explicit `summon --model` wins; else the spirit's own tuned model; else the default."""
    return spirits.read_state().get("model") or spirit.get("model") or ollama.DEFAULT_MODEL


def print_face(spirit):
    for line in spirit.get("face", []):
        print(paint(line, spirit.get("color", "white")))


# ---------------------------------------------------------------- commands

def cmd_whisper(args):
    cmd = " ".join(args.command)
    if not whisper_mod.should_haunt(cmd, args.exit, force=args.force):
        return 0
    spirit = spirits.current()
    try:
        text = whisper_mod.whisper(spirit, cmd, args.exit, model_for(spirit),
                                   timeout=args.timeout, attempts=args.attempts,
                                   budget=args.budget)
    except ollama.OllamaError as e:
        if args.verbose:
            print(f"revenant: {e}", file=sys.stderr)
        return 0  # never break the user's prompt
    if text:  # no text = every attempt failed the validators: the ghost stays silent
        glyph = spirit.get("glyph", "☠")
        print(paint(f"  {glyph} {spirit['display_short']} › ", spirit.get("color", "white"))
              + paint(text, spirit.get("color", "white"), dim=True))
    return 0


def cmd_summon(args):
    try:
        spirit = spirits.load(args.name)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 1
    spirits.write_state(spirit=args.name, model=args.model)  # no --model clears any old override
    model = model_for(spirit)
    print()
    print_face(spirit)
    print(paint(f"\n  {spirit['display']}", spirit.get("color", "white")))
    print(paint(f"  born {spirit.get('born', '?')} · {spirit.get('cause_of_death', 'unknown causes')}",
                spirit.get("color", "white"), dim=True))
    print(paint(f"  « {spirit.get('greeting', '...')} »\n", spirit.get("color", "white")))
    print(paint(f"  waking the spirit (loading {model}) …", "white", dim=True), flush=True)
    try:  # pre-load the model so the first whisper is instant
        ollama.chat([{"role": "user", "content": "hi"}], model, num_predict=1, timeout=180)
    except ollama.OllamaError as e:
        print(f"  could not load {model}: {e}", file=sys.stderr)
    return 0


def cmd_spirits(_args):
    now = spirits.current()["name"]
    for n in spirits.names():
        s = spirits.load(n)
        mark = "●" if n == now else "○"
        print(paint(f" {mark} {n:<8} {s['display']}  ({s.get('born', '?')})", s.get("color", "white")))
    return 0


def cmd_doctor(_args):
    print(f"revenant {__version__}")
    up = ollama.is_up()
    print(f"  ollama @ {ollama.HOST}: {'up' if up else 'DOWN'}")
    if not up:
        print("  → start it (WSL: `sudo systemctl start ollama` or `ollama serve`)")
        return 1
    models = ollama.list_models()
    print(f"  models installed: {', '.join(models) or 'none'}")
    need = {}  # model -> spirits that use it (each spirit has its own tuned model)
    for n in spirits.names():
        need.setdefault(model_for(spirits.load(n)), []).append(n)
    missing = 0
    for m, who in sorted(need.items()):
        ok = m in models
        missing += not ok
        print(f"  {m} (for {', '.join(who)}): {'present' if ok else 'MISSING → ollama pull ' + m}")
    print(f"  spirit: {spirits.current()['name']}")
    return 1 if missing else 0


# Deliberately disjoint from every few-shot example command in spirits/*.toml,
# so demo + bench measure the spirit, not memorisation.
SAMPLE_COMMANDS = [
    ("git reset --hard HEAD~3", 0),
    ("make", 2),
    ("chmod -R 777 .", 0),
    ("docker build .", 1),
    ("curl https://example.com", 6),
    ("cd ..", 0),
]
DEMO_COUNT = 3


def cmd_demo(args):
    spirit = spirits.current()
    print_face(spirit)
    print(paint(f"  {spirit['display']} — model {model_for(spirit)}\n", spirit.get("color", "white")))
    for cmd, code in SAMPLE_COMMANDS[:DEMO_COUNT]:
        print(paint(f"$ {cmd}", "white", dim=True) + (f"   [exit {code}]" if code else ""))
        t0 = time.perf_counter()
        try:
            r = whisper_mod.whisper_detailed(spirit, cmd, code, model_for(spirit),
                                             timeout=args.timeout, attempts=args.attempts)
        except ollama.OllamaError as e:
            print(f"  (the spirit is silent: {e})")
            return 1
        dt = time.perf_counter() - t0
        text = r["text"] or "…(stays silent: no attempt passed the validators)"
        print(paint(f"  {spirit.get('glyph', '☠')} {text}", spirit.get("color", "white"))
              + paint(f"   [{dt:.2f}s, {r['tries']} {'try' if r['tries'] == 1 else 'tries'}]", "white", dim=True))
    return 0


def cmd_bench(args):
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    names = [n.strip() for n in args.spirits.split(",")] if args.spirits else spirits.names()
    pct = lambda x, n: 100 * x / n if n else 0.0
    rows, samples = [], []
    for model in models:
        print(f"warming {model} …", file=sys.stderr)
        try:
            ollama.chat([{"role": "user", "content": "hi"}], model, num_predict=1, timeout=300)
        except ollama.OllamaError as e:
            print(f"  skipping {model}: {e}", file=sys.stderr)
            continue
        for name in names:
            sp = spirits.load(name)
            times = []
            n = ic = af = cp = raw = fin = tries = 0
            for cmd, code in SAMPLE_COMMANDS:
                for _ in range(args.runs):
                    t0 = time.perf_counter()
                    try:
                        r = whisper_mod.whisper_detailed(sp, cmd, code, model, timeout=120,
                                                         attempts=args.attempts)
                    except ollama.OllamaError:
                        continue
                    times.append(time.perf_counter() - t0)
                    n += 1
                    f = r["first"]
                    ic += f["in_character"]
                    af += f["advice_free"]
                    cp += f["copied"]
                    raw += f["ok"]
                    fin += r["text"] is not None
                    tries += r["tries"]
                    if r["text"]:
                        samples.append((model, name, cmd, r["text"]))
            if not n:
                continue
            rows.append((model, name, statistics.median(times), pct(ic, n), pct(af, n), cp,
                         pct(raw, n), pct(fin, n), tries / n))
            print(f"  {model} / {name}: median {rows[-1][2]:.2f}s, first-try pass "
                  f"{rows[-1][6]:.0f}%, pass ≤{args.attempts} tries {rows[-1][7]:.0f}%", file=sys.stderr)

    head = ["| model | spirit | median s (all tries) | in-character % | advice-free % | copied | "
            f"1st-try pass % | pass ≤{args.attempts} tries % | avg tries |",
            "|---|---|---|---|---|---|---|---|---|"]
    body = [f"| {m} | {n} | {med:.2f} | {i:.0f} | {a:.0f} | {c} | {r:.0f} | {f:.0f} | {t:.2f} |"
            for m, n, med, i, a, c, r, f, t in rows]
    table = head + body
    report = table + ["", "## Samples (accepted lines only)", ""] + \
        [f"- `{m}` · **{n}** · `{cmd}` → {text}" for m, n, cmd, text in samples]
    Path(args.out).write_text("\n".join(report) + "\n")
    print("\n" + "\n".join(table))
    print(f"\nfull report with samples: {args.out}")
    return 0


def cmd_seance(args):
    try:
        from . import server
    except ImportError:
        print("the Séance Room has not been built yet (coming in the next release)", file=sys.stderr)
        return 1
    return server.serve(args.host, args.port)


def cmd_warm(_args):
    """Preload the current spirit's model so the first real whisper isn't a cold start."""
    try:
        ollama.chat([{"role": "user", "content": "hi"}], model_for(spirits.current()),
                    num_predict=1, timeout=120)
    except ollama.OllamaError:
        pass
    return 0


def cmd_ofrenda(args):
    import collections
    import fnmatch
    import subprocess
    from . import ofrenda

    now = time.time()
    found, unsafe = [], []
    repos = [] if args.demo else ofrenda.find_repos(args.paths or ["~"], args.depth)
    if args.demo:
        found = ofrenda.demo_projects(now)
    for r in repos:
        try:
            p = ofrenda.inspect(r, trust=args.trust_owners, now=now)
        except ofrenda.Unsafe:
            unsafe.append(r)
            continue
        if p is None or p["quietDays"] < args.months * 30.44:
            continue
        if any(fnmatch.fnmatch(p["name"].lower(), pat.lower()) for pat in args.exclude):
            continue
        found.append(p)
    found.sort(key=lambda p: p["died"], reverse=True)
    found = found[: args.max]
    if args.demo:
        print(f"  demo: {len(found)} fictional projects, no repositories were read")
    else:
        print(f"  looked at {len(repos)} repositories, {len(found)} gone quiet for {args.months:g}+ months")
    if unsafe:
        print(f"  skipped {len(unsafe)} that git does not trust (typical on /mnt/c). "
              "If they are yours, add --trust-owners.")
    if not found:
        print("  nothing to remember. Try another folder, or a lower --months.")
        return 1
    for p in found:
        print(f"    {p['name']:<28} last commit {p['died']}  ({p['commits']} commits)  {p['path']}")
    if args.dry_run:
        print("  dry run: nothing was written. The page will hold names, dates, counts and last commit "
              "messages, never file paths.")
        return 0

    use_model = not args.no_model and not args.demo
    if use_model:
        if not ollama.is_up():
            print("  Ollama is not running. Start it, or use --no-model for plain templates.", file=sys.stderr)
            return 1
        if args.model not in ollama.list_models():
            print(f"  {args.model} is not installed: ollama pull {args.model}  (or pass --model)", file=sys.stderr)
            return 1
    rejects = collections.Counter()
    for p in ([] if args.demo else found):
        if args.no_last_words:
            p["lastWords"], p["earlier"] = None, []
        try:
            r = ofrenda.remember(p, args.model, args.attempts, use_model, True, rejects)
        except ollama.OllamaError as e:
            print(f"  the model stopped answering ({e}); finishing with templates")
            use_model = False
            r = ofrenda.remember(p, args.model, args.attempts, False, True, rejects)
        p.update(r)
        mark = "✓" if r["by"] == "model" else "~"
        print(f"  {mark} {p['name']}  ({r['by']}, {r['tries']} {'try' if r['tries'] == 1 else 'tries'})")

    keep = ("name", "seed", "born", "died", "commits", "langs", "lastWords", "cause", "epitaph",
            "offering", "lived", "quiet")
    stats = {"model_written": sum(p["by"] == "model" for p in found),
             "template": sum(p["by"] == "template" for p in found),
             "tries": sum(p["tries"] for p in found), "rejected": dict(rejects)}
    data = {"generated": time.strftime("%Y-%m-%d"), "model": args.model if use_model or stats["model_written"] else None,
            "demo": args.demo, "projects": [{k: p[k] for k in keep} for p in found], "elders": ofrenda.elders(), "stats": stats}
    target = ofrenda.build_site(data, args.out)
    if args.demo:
        print(f"\n  {len(found)} fictional sample remembrances")
    else:
        print(f"\n  {len(found)} remembrances: {stats['model_written']} written by {args.model}, "
              f"{stats['template']} from the template. Rejected drafts: {dict(rejects) or 'none'}")
    print(f"  built {target} ({target.stat().st_size // 1024} KB, one file, no internet needed)")
    try:
        win = subprocess.run(["wslpath", "-w", str(target.resolve())], capture_output=True, text=True, timeout=5).stdout.strip()
        if win:
            print(f"  open in Windows: {win}")
    except (OSError, subprocess.SubprocessError):
        pass
    print("  Review it before you publish it: it contains project names and last commit messages.")
    return 0


def cmd_hook(args):
    path = HOOK_DIR / f"hook.{args.shell}"
    print(path.read_text().replace("__REVENANT_ROOT__", str(ROOT)))
    return 0


# ---------------------------------------------------------------- parser

def build_parser():
    p = argparse.ArgumentParser(prog="ghost", description="Revenant: dead languages haunt your terminal.")
    p.add_argument("--version", action="version", version=f"revenant {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("whisper", help="whisper about a command (used by the shell hook)")
    w.add_argument("--exit", type=int, default=0, help="the command's exit code")
    w.add_argument("--force", action="store_true", help="always whisper")
    w.add_argument("--timeout", type=float, default=8.0)
    w.add_argument("--attempts", type=int, default=2, help="max generations before the ghost stays silent")
    w.add_argument("--budget", type=float, default=4.0,
                   help="max total seconds (all retries) the prompt may be held; then the ghost stays silent")
    w.add_argument("--verbose", action="store_true")
    w.add_argument("command", nargs="+")
    w.set_defaults(fn=cmd_whisper)

    s = sub.add_parser("summon", help="switch spirit")
    s.add_argument("name")
    s.add_argument("--model", help="also switch the Ollama model")
    s.set_defaults(fn=cmd_summon)

    sub.add_parser("warm", help="preload the current spirit's model").set_defaults(fn=cmd_warm)
    sub.add_parser("spirits", help="list spirits").set_defaults(fn=cmd_spirits)
    sub.add_parser("doctor", help="check Ollama + model").set_defaults(fn=cmd_doctor)

    d = sub.add_parser("demo", help="run sample commands through the current spirit")
    d.add_argument("--timeout", type=float, default=30.0)
    d.add_argument("--attempts", type=int, default=3)
    d.set_defaults(fn=cmd_demo)

    b = sub.add_parser("bench", help="latency + persona-quality table across models/spirits")
    b.add_argument("--models", default=ollama.DEFAULT_MODEL, help="comma-separated, e.g. qwen2.5:3b,qwen2.5:7b")
    b.add_argument("--spirits", help="comma-separated; default all")
    b.add_argument("--runs", type=int, default=2, help="repeats per command")
    b.add_argument("--attempts", type=int, default=3, help="max generations per whisper")
    b.add_argument("--out", default="bench_results.md")
    b.set_defaults(fn=cmd_bench)

    sc = sub.add_parser("seance", help="open the Séance Room (browser UI on localhost)")
    sc.add_argument("--host", default="127.0.0.1", help="bind address (keep it loopback)")
    sc.add_argument("--port", type=int, default=8666)
    sc.set_defaults(fn=cmd_seance)

    o = sub.add_parser("ofrenda", help="build an altar page for your abandoned git projects")
    o.add_argument("paths", nargs="*", help="folders to scan (default: your home folder)")
    o.add_argument("--months", type=float, default=6, help="quiet for at least this long (0 = every repo)")
    o.add_argument("--depth", type=int, default=4, help="how deep to look for repositories")
    o.add_argument("--out", default="ofrenda-out", help="output folder; the page is <out>/index.html")
    o.add_argument("--model", default="qwen2.5:7b")
    o.add_argument("--attempts", type=int, default=3)
    o.add_argument("--max", type=int, default=48, help="most projects on the altar")
    o.add_argument("--exclude", action="append", default=[], metavar="NAME", help="skip repos by name (wildcards ok)")
    o.add_argument("--no-last-words", action="store_true", help="leave commit messages off the page")
    o.add_argument("--no-model", action="store_true", help="plain templates, no Ollama needed")
    o.add_argument("--trust-owners", action="store_true", help="read repos git thinks are owned by someone else")
    o.add_argument("--dry-run", action="store_true", help="list what would be included and stop")
    o.add_argument("--demo", action="store_true", help="fictional sample projects instead of your repos (safe to publish)")
    o.set_defaults(fn=cmd_ofrenda)

    h = sub.add_parser("hook", help="print the shell hook (eval it in your rc file)")
    h.add_argument("shell", choices=["bash", "zsh"])
    h.set_defaults(fn=cmd_hook)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    sys.exit(args.fn(args) or 0)
