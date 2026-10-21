---
name: prompt-for-sensitive
description: Use whenever you need a secret, credential, token, password, API key, connection string, PAT, certificate, or any sensitive value FROM THE HUMAN and you must NOT have that value pass through the chat/transcript. Pops a native desktop input window (Python/tkinter, no timeout) where the human types the value; the value is written ONLY to a disk path you choose and is never printed back to you, so you can then feed that file into a secret store, env var, `dotnet user-secrets`, config write, etc. without ever reading it. For long or multi-step jobs, `--encrypt` writes an AES-GCM vault instead and prints a PFS_TOKEN; scripts then use the value through `pfs.py exec` (env var or stdin, output masked). Triggers include "ask me for the secret securely", "prompt me for my API key", "I don't want to paste my password in chat", "get the credential from me without seeing it", "set this secret but ask me for the value", "/prompt-for-sensitive", or any time a task needs a real secret and typing it into the conversation would leak it.
---

# Prompt for sensitive input

Job: get a secret from the human **without it ever entering your context**. A native
window opens, the human types the value, it lands on disk at a path you pick. You get
back only a "wrote N chars to <path>" confirmation — never the value itself. Then use
the file for whatever needed the secret.

## Why this exists

If you ask for a secret in chat, the human pastes it and now it is in the transcript
forever. This skill routes the value straight from a GUI keystroke to a file on disk,
skipping the conversation entirely. You operate on the *path*, not the *value*.

## Encrypted mode (use this for long or multi-step jobs)

With `--encrypt`, nothing is written in plaintext. `--out` becomes an encrypted vault
file, and stdout gives you a token:

```
OK: vault 3f9c0a1b2c3d4e5f (412 chars) at C:\...\aws.enc, expires 2026-10-22T03:00:00+0100
PFS_TOKEN=pfs1.3f9c0a1b2c3d4e5f.<key>
```

The value is opaque text: an API key, env lines, a PEM, a block of PII. The vault never
parses it. Any parsing is the job of the script that receives it.

```bash
SKILL=~/.claude/skills/prompt-for-sensitive
python "$SKILL/scripts/prompt_for_sensitive.py" --encrypt --type multiline \
    --ttl 12h --label "prod AWS creds" --out "<scratchpad>/aws.enc" \
    --prompt "Paste the production AWS credential lines"
```

Use the vault ONLY through `pfs.py exec`. The value goes to the child process in an env
var (`--env NAME`) or on stdin (`--stdin`), never to disk, never to your stdout:

```bash
export PFS_TOKEN=pfs1....        # or pass --token
python "$SKILL/scripts/pfs.py" exec --vault "<scratchpad>/aws.enc" --env CREDS -- bash my-step.sh
python "$SKILL/scripts/pfs.py" exec --vault "<scratchpad>/key.enc" --stdin -- some-tool --key-from-stdin
```

Rules:
- Keep the token and the vault path for the whole job. Every step calls `pfs.py exec` again.
- `exec` removes `PFS_TOKEN` from the child env. Pass `--keep-token` only when the child
  itself calls `pfs.py exec`.
- `exec` masks the value in the child's stdout and stderr (raw, base64, URL and JSON forms,
  and each line of a multi-line value become `***`). The token is masked too. Values
  shorter than 4 chars are not masked; `exec` writes a warning.
- WARNING: masking stops accidental leaks only. Do not write a child that transforms the
  value (reverses it, hex-encodes it, slices it) and prints the result.
- There is no command that prints the plaintext. Do not write one, and do not decrypt
  the vault with your own code.
- The child exit code is the `exec` exit code. Exit code `3` is a vault or usage error;
  the message never contains the value.
- When the job is done: `python "$SKILL/scripts/pfs.py" revoke <vault path or id>`.

Security model:
- Key = HKDF(token + machine half). The machine half is DPAPI-protected (bound to this
  Windows user) in `%LOCALAPPDATA%\pfs\keys\`. The token in the transcript is useless on
  another machine or account. The `.enc` file is useless without the token.
- The expiry is in the authenticated header. An edited expiry fails the decrypt.
- On expiry, `revoke`, or `sweep`, the machine half is shredded, so every copy of the
  `.enc` file is dead. The scheduled task `pfs-vault-sweep` runs `pfs.py sweep` every
  hour (`pfs.py install-sweeper` creates it). Every `exec` and every `--encrypt` also
  sweeps first.
- `pfs.py list` shows ids, expiry, labels and paths. It never shows values.
- WARNING: DPAPI and `install-sweeper` are Windows only. On other systems the machine half
  is a plain `0600` file under `~/.local/share/pfs/keys/` (or `$PFS_STORE_DIR`), and the
  hourly sweep must be a cron entry running `pfs.py sweep`.
- Needs the `cryptography` package for the Python that runs the scripts.
- Tests: `python -m unittest test_vault` in `scripts/`.

## How to use it (plaintext file mode)

Run the script and **wait** — it blocks until the human clicks Save (or Cancel). There
is no timeout; a human may take a while to go fetch a credential.

```bash
python ".claude/skills/prompt-for-sensitive/scripts/prompt_for_sensitive.py" \
    --out "<path to write the value to>" \
    --prompt "<exactly what you want them to enter>" \
    --title "<window title>" \
    --type password
```

On Windows the same call works from PowerShell (`python ...`). Use `pythonw` only if you
want no console window; plain `python` is fine.

### Arguments

- `--out` (required) — file path the value is written to. **You choose this.** Parent
  dirs are created. Prefer a scratch/temp path you control, e.g. the session scratchpad,
  not somewhere it'll get committed.
- `--prompt` — the instruction shown above the box. Be specific ("Paste the Stripe LIVE
  secret key (sk_live_…)"), so the human enters the right thing.
- `--title` — window title bar text.
- `--type` — input widget:
  - `password` (default) — masked single-line box. Use for passwords/keys/tokens.
  - `text` — visible single-line box. Use when masking hurts (e.g. a username, a URL).
  - `multiline` — visible text area. Use for multi-line blobs: PEM certs, JSON key files,
    private keys. (Enter inserts a newline; Ctrl+Enter or the Save button submits.)
- `--allow-empty` — permit an empty submission. Off by default so a blank secret can't
  slip through.
- `--newline` — append a trailing newline to the file. Off by default — most secrets must
  NOT have a trailing newline or they break (env vars, header values). Turn on only if the
  consumer expects one.

### Exit codes

- `0` — value written to `--out`. Proceed.
- `2` — human cancelled / closed the window. Nothing was written. Do not proceed. If no
  message came back (see below), ask what they want to do.

### Message from the user

The window has an optional, visible "Message to the AI" box. If the human typed in it,
stdout carries an extra line `MESSAGE FROM USER: <text>` — on Save **and** on Cancel.
Always check for it and act on it (e.g. "this is the staging key, not prod", "wrong
account, use the other one", "I'll set this myself"). The box is not for secrets, so it's
fine to read.
- `3` — bad args or the file couldn't be written (also: tkinter unavailable). Report it.

## After it returns

The value is now at `--out`. Consume it **without printing it**. Good patterns:

- Pipe/redirect the file into the tool that needs it.
- Read it into an env var inside the same command that uses it, e.g.
  `dotnet user-secrets set "Key" "$(cat <path>)"` — the secret goes tool→tool, not through you.
- Once consumed, delete the file if it was a scratch path: `rm <path>`.

**Never** `cat`/`Read` the file just to look at it, and never echo it into chat, a commit,
a log, or a PR — that defeats the entire purpose. If a downstream command fails, debug from
the exit code and error text, not by dumping the secret.

## Notes

- Requires Python 3 with tkinter (bundled with standard Windows/macOS Python installs).
- Single value per invocation. Need several secrets? Call it once per value with distinct
  `--out` paths and clear `--prompt` text.
