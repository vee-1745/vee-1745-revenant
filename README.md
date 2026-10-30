# 👻 Revenant

Dead programming languages haunt your terminal. Everything runs locally on open-weight models via [Ollama](https://ollama.com). No API keys, no network, no command history leaving your machine.

## Quick start (WSL / Linux)

```bash
git clone https://github.com/vee-1745/vee-1745-revenant && cd vee-1745-revenant

# 1. a local model
ollama pull qwen2.5:3b   # COBOL, Lisp
ollama pull qwen2.5:7b   # Fortran, Perl (they need the bigger model)

# 2. check the plumbing
python3 ghost.py doctor

# 3. meet a spirit
python3 ghost.py summon cobol
python3 ghost.py demo

# 4. let it haunt your shell (add to ~/.bashrc, then open a new terminal)
echo "eval \"\$(python3 $PWD/ghost.py hook bash)\"" >> ~/.bashrc   # run from this folder
```

After the hook is loaded, `ghost` is available as a command:

```bash
ghost spirits               # list the dead
ghost summon lisp           # swap the spirit
ghost summon perl --model llama3.2:3b   # swap spirit and model
ghost whisper --force -- "git push --force"
```

It whispers on every failed command and every dangerous one (`rm -rf`, `--force`, `sudo`, ...), plus an occasional random one.

Requires Python 3.11+ (3.12 on Ubuntu 24.04). Zero pip dependencies.

## Layout

```
ghost.py                 entry point
revenant/cli.py          commands
revenant/whisper.py      when to haunt, prompt building, reply cleanup
revenant/ollama.py       stdlib Ollama client
revenant/spirits/*.toml  one persona per dead language (system prompt + few-shot examples)
revenant/hooks/          bash / zsh shell hooks
revenant/server.py       the Séance Room's local server (stdlib, streams over SSE)
revenant/ofrenda.py       scans git repos, writes epitaphs, builds the altar page
revenant/web/            the Séance Room UI: SVG spirits, altar, chat (no build step, fonts bundled)
```

Adding a spirit is one TOML file: copy `cobol.toml`, change the voice, done.

## How it picks a model

Each spirit names its own model in its `.toml`, chosen from `ghost bench` data: COBOL and Lisp pass the persona validators on the 3B model (~0.3-0.4s per whisper), while Fortran and Perl need the 7B model. `ghost summon <name> --model <m>` overrides it until the next plain `summon`. `ghost doctor` checks that every model the spirits need is installed.

## Never blocks your prompt

The hook caps the *total* time a whisper may hold the prompt (`--budget`, default 4s, retries included). A model that is still cold-loading, or a reply that keeps failing the validators, just means the ghost stays silent. The hook also preloads the model in the background when your shell starts.

## The Séance Room

```bash
python3 ghost.py seance        # then open http://localhost:8666
```

Pick a spirit, ask it anything, and watch it talk: its mouth moves with every token streamed from your local model. The page loads nothing from the internet (fonts are bundled, CSP is `default-src 'self'`), so it works with the Wi-Fi off, and the status bar says so. The server binds to loopback only and rejects foreign Host and Origin headers.

## The Ofrenda

On Día de los Muertos families build an *ofrenda*, an altar for the people they remember. This one is for the projects you stopped working on.

```bash
python3 ghost.py ofrenda ~/projects --dry-run      # list what would be included, write nothing
python3 ghost.py ofrenda ~/projects                # -> ofrenda-out/index.html
python3 ghost.py ofrenda --demo --out site         # fictional samples, safe to publish
```

It finds git repositories that have been quiet for 6+ months (`--months 0` for all), reads their history, and asks a local model (`qwen2.5:7b`) for a short epitaph and an offering. The *cause of death* ("Died mid-refactor", "Died with 2 unsaved changes") comes from plain heuristics on the real git facts, never from the model. Every epitaph is fact-checked: a digit that is not in the repo's facts rejects the draft, and after three rejected drafts the page uses a plain template and says so in its footer.

The output is one HTML file with the fonts, art and scripts inside. It loads nothing from the internet, renders all repo text as plain text (a hostile commit message cannot inject anything), and contains no file paths. You light a candle for each project by clicking it.

Safe by default: repositories are read, never modified (`GIT_OPTIONAL_LOCKS=0`); repos git does not trust (common on `/mnt/c`) are skipped unless you pass `--trust-owners`; `--exclude NAME` and `--no-last-words` keep things off the page. Review the page before you publish it, since it holds project names and last commit messages.
