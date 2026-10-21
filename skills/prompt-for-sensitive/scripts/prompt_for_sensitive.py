#!/usr/bin/env python3
"""Pop a GUI window that asks a human for a sensitive value, then write it to disk.

The whole point: the secret is typed by the human into a native window and lands
ONLY on disk at the path the caller chose. It is NEVER printed to stdout/stderr,
so it never enters the calling agent's transcript/context. The agent gets back
just the path + a status line and can then feed the file to whatever needs it
(env var, `dotnet user-secrets`, a config write, etc.) without ever reading it.

No timeout: the window blocks in the tk mainloop until the human submits or
cancels. That is deliberate — a human may take a while to fetch a credential.

Usage:
    python prompt_for_sensitive.py --out C:\\path\\to\\secret.txt \\
        --prompt "Paste the Stripe live secret key" \\
        --title "Stripe key" \\
        --type password

The window also has an optional, visible "Message to the AI" box. Whatever the
human typed there is printed to stdout on Save or Cancel, so the caller gets
their note (e.g. "this is the staging key", "use the other account instead"). That box is NOT for secrets.

Encrypted mode (--encrypt): --out becomes an AES-GCM vault file (see vault.py),
nothing is written in plaintext, and stdout carries one line
`PFS_TOKEN=pfs1.<id>.<key>`. Use the vault only through `pfs.py exec`.

Exit codes:
    0  value written to --out
    2  human cancelled / closed the window (nothing written; any message on stdout)
    3  bad arguments / could not write the file
"""
import argparse
import os
import sys


def build_parser():
    p = argparse.ArgumentParser(
        description="Prompt a human for a sensitive value and write it to disk (never to stdout)."
    )
    p.add_argument("--out", required=True,
                   help="File path to write the entered value to. Parent dirs are created.")
    p.add_argument("--prompt", default="Enter the sensitive value:",
                   help="Instruction shown above the input box. Say exactly what you want.")
    p.add_argument("--title", default="Sensitive input required",
                   help="Window title bar text.")
    p.add_argument("--type", choices=["password", "text", "multiline"], default="password",
                   help="password = masked single line (default); text = visible single line; "
                        "multiline = visible text area (for keys/certs/JSON blobs).")
    p.add_argument("--allow-empty", action="store_true",
                   help="Permit submitting an empty value. Off by default so you don't get a blank secret.")
    p.add_argument("--newline", action="store_true",
                   help="Append a trailing newline to the file. Off by default — secrets usually must not have one.")
    p.add_argument("--encrypt", action="store_true",
                   help="Write an encrypted vault to --out and print PFS_TOKEN=... (see pfs.py).")
    p.add_argument("--ttl", default="12h",
                   help="With --encrypt: vault lifetime, e.g. 900, 30m, 12h, 2d. Default 12h.")
    p.add_argument("--label", default="",
                   help="With --encrypt: NON-secret description shown by `pfs.py list`.")
    return p


def write_secret(path, value, add_newline):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(value + ("\n" if add_newline else ""))


def main():
    args = build_parser().parse_args()

    if args.encrypt:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import vault
        try:
            ttl_seconds = vault.parse_ttl(args.ttl)
            vault._crypto()  # fail before the human types anything
            vault.sweep()
        except vault.VaultError as e:
            sys.stderr.write(f"{e}\n")
            return 3

    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as e:  # pragma: no cover - tkinter missing
        sys.stderr.write(f"tkinter unavailable: {e}\n")
        return 3

    result = {"value": None, "submitted": False}

    root = tk.Tk()
    root.title(args.title)
    root.minsize(460, 0)
    # Pull the window to the front so the human actually notices it.
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.lift()
    root.focus_force()

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=args.prompt, wraplength=440, justify="left").pack(
        anchor="w", pady=(0, 10))

    error_var = tk.StringVar(value="")
    error_lbl = ttk.Label(frame, textvariable=error_var, foreground="#b00020")

    if args.type == "multiline":
        entry = tk.Text(frame, width=54, height=8)
        entry.pack(fill="both", expand=True)

        def get_value():
            return entry.get("1.0", "end-1c")
    else:
        show = "*" if args.type == "password" else ""
        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var, show=show, width=54)
        entry.pack(fill="x")

        def get_value():
            return var.get()

    entry.focus_set()

    ttk.Label(frame, text="Message to the AI (optional, sent on Save or Cancel; NOT for secrets):",
              wraplength=440, justify="left").pack(anchor="w", pady=(12, 4))
    feedback = tk.Text(frame, width=54, height=3)
    feedback.pack(fill="x")

    def submit(event=None):
        value = get_value()
        if not value and not args.allow_empty:
            error_var.set("Value is empty — type something, or the caller passed --allow-empty to permit blank.")
            error_lbl.pack(anchor="w", pady=(8, 0))
            return
        result["value"] = value
        result["submitted"] = True
        result["message"] = feedback.get("1.0", "end-1c").strip()
        root.destroy()

    def cancel(event=None):
        result["submitted"] = False
        result["message"] = feedback.get("1.0", "end-1c").strip()
        root.destroy()

    btns = ttk.Frame(frame)
    btns.pack(fill="x", pady=(12, 0))
    ttk.Button(btns, text="Cancel", command=cancel).pack(side="right")
    ttk.Button(btns, text="Save", command=submit).pack(side="right", padx=(0, 8))

    # Enter submits for single-line; Ctrl+Enter for multiline (Enter = newline there).
    # Bound on the value widget only, so Enter in the message box adds a newline.
    if args.type == "multiline":
        entry.bind("<Control-Return>", lambda e: (submit(), "break")[1])
    else:
        entry.bind("<Return>", submit)
    root.bind("<Escape>", cancel)
    root.protocol("WM_DELETE_WINDOW", cancel)

    root.mainloop()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    def emit_message():
        message = result.get("message")
        if message:
            sys.stdout.write(f"MESSAGE FROM USER: {message}\n")

    if not result["submitted"]:
        sys.stderr.write("Cancelled — no value written.\n")
        emit_message()
        return 2

    if args.encrypt:
        value = result["value"] + ("\n" if args.newline else "")
        try:
            vid, token, expires_at = vault.create_vault(value, args.out, ttl_seconds, args.label)
        except Exception as e:
            sys.stderr.write(f"Failed to write vault {args.out}: {e}\n")
            emit_message()
            return 3
        sys.stdout.write(f"OK: vault {vid} ({len(value)} chars) at {os.path.abspath(args.out)}, "
                         f"expires {vault._iso(expires_at)}\n")
        sys.stdout.write(f"PFS_TOKEN={token}\n")
        emit_message()
        return 0

    try:
        write_secret(args.out, result["value"], args.newline)
    except Exception as e:
        sys.stderr.write(f"Failed to write {args.out}: {e}\n")
        emit_message()
        return 3

    # Confirmation ONLY — never echo the value.
    length = len(result["value"])
    sys.stdout.write(f"OK: wrote {length} chars to {os.path.abspath(args.out)}\n")
    emit_message()
    return 0


if __name__ == "__main__":
    sys.exit(main())
