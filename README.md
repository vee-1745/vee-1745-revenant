# 👻 Revenant

Dead programming languages haunt your terminal. Everything runs locally on open-weight models via [Ollama](https://ollama.com). No API keys, no network, no command history leaving your machine.

## Quick start (WSL / Linux)

```bash
# 1. a local model
ollama pull qwen2.5:3b   # COBOL, Lisp
ollama pull qwen2.5:7b   # Fortran, Perl (they need the bigger model)

# 2. check the plumbing
python3 ghost.py doctor

# 3. meet a spirit
python3 ghost.py summon cobol
python3 ghost.py demo

# 4. let it haunt your shell (add to ~/.bashrc, then open a new terminal)
eval "$(python3 /full/path/to/revenant/ghost.py hook bash)"
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
