#!/usr/bin/env python3
"""pfs - use an encrypted prompt-for-sensitive vault without ever printing it.

    pfs.py exec  --vault V.enc [--token T] (--env NAME | --stdin) [--keep-token] -- cmd args...
    pfs.py revoke <vault id | V.enc>
    pfs.py sweep
    pfs.py list
    pfs.py install-sweeper            (Windows: hourly scheduled task running `sweep`)

The token comes from --token or the PFS_TOKEN env var. There is deliberately NO
command that prints the plaintext: `exec` is the only way to use a vault.

`exec` masks the value in the child's stdout and stderr (GitHub Actions style):
the raw value, its base64 / URL / JSON-escaped forms, and each line of a
multi-line value are replaced with `***`. The token is masked too. Masking stops
accidental leaks (a script that logs its env, an error that echoes a header). It
cannot stop a child that transforms the value on purpose before printing it.

Exit codes: the child's exit code for `exec`; 0 ok; 3 vault/usage error.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vault  # noqa: E402

MASK = b"***"
MIN_MASK_LEN = 4      # shorter values would mask ordinary output; warn instead
MIN_LINE_MASK_LEN = 8  # lines of a multi-line value


# --------------------------------------------------------------------------- masking

def mask_patterns(secrets_):
    """Return the byte strings to mask, longest first."""
    pats = set()
    for s in secrets_:
        if not s:
            continue
        forms = {s, s.strip()}
        lines = [ln.strip() for ln in s.splitlines()]
        forms.update(ln for ln in lines if len(ln) >= MIN_LINE_MASK_LEN)
        for f in list(forms):
            if len(f) < MIN_MASK_LEN:
                continue
            b = f.encode("utf-8")
            pats.add(b)
            pats.add(base64.b64encode(b))
            pats.add(base64.b64encode(b).rstrip(b"="))
            pats.add(base64.urlsafe_b64encode(b).rstrip(b"="))
            pats.add(urllib.parse.quote(f, safe="").encode())
            pats.add(urllib.parse.quote_plus(f, safe="").encode())
            pats.add(json.dumps(f)[1:-1].encode())
            pats.add(json.dumps(f, ensure_ascii=False)[1:-1].encode("utf-8"))
            if b"\n" in b:
                pats.add(b.replace(b"\n", b"\r\n"))
    return sorted((p for p in pats if len(p) >= MIN_MASK_LEN), key=len, reverse=True)


class Masker:
    """Streaming replace. Holds back only a tail that could start a secret."""

    def __init__(self, patterns):
        self.patterns = patterns
        self.regex = re.compile(b"|".join(re.escape(p) for p in patterns)) if patterns else None
        self.hold = max((len(p) for p in patterns), default=1) - 1
        self.buf = b""

    def _unsafe_tail(self, buf):
        for k in range(min(self.hold, len(buf)), 0, -1):
            tail = buf[-k:]
            if any(p.startswith(tail) for p in self.patterns):
                return k
        return 0

    def feed(self, chunk: bytes) -> bytes:
        if not self.regex:
            return chunk
        self.buf = self.regex.sub(MASK, self.buf + chunk)
        k = self._unsafe_tail(self.buf)
        out, self.buf = (self.buf[:-k], self.buf[-k:]) if k else (self.buf, b"")
        return out

    def flush(self) -> bytes:
        out = self.regex.sub(MASK, self.buf) if self.regex else self.buf
        self.buf = b""
        return out


def _pump(src, dst, masker):
    while True:
        chunk = src.read1(65536) if hasattr(src, "read1") else src.read(65536)
        if not chunk:
            break
        out = masker.feed(chunk)
        if out:
            dst.write(out)
            dst.flush()
    out = masker.flush()
    if out:
        dst.write(out)
        dst.flush()


# --------------------------------------------------------------------------- commands

def _token(args):
    tok = args.token or os.environ.get("PFS_TOKEN")
    if not tok:
        raise vault.VaultError("no token: pass --token or set PFS_TOKEN")
    return tok


def cmd_exec(args):
    if not args.cmd:
        raise vault.VaultError("no command given after --")
    if bool(args.env) == bool(args.stdin):
        raise vault.VaultError("give exactly one of --env NAME or --stdin")
    if args.env and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.env):
        raise vault.VaultError(f"--env {args.env!r} is not a valid env var name")
    vault.sweep()
    token = _token(args)
    value = vault.open_vault(args.vault, token)

    env = dict(os.environ)
    if not args.keep_token:
        env.pop("PFS_TOKEN", None)
    if args.env:
        env[args.env] = value

    patterns = mask_patterns([value, token])
    if len(value.strip()) < MIN_MASK_LEN:
        sys.stderr.write(f"pfs: WARNING value is shorter than {MIN_MASK_LEN} chars, "
                         f"so output masking is off for it\n")

    cmd = list(args.cmd)
    exe = shutil.which(cmd[0])
    if exe:
        cmd[0] = exe
    proc = subprocess.Popen(cmd, env=env,
                            stdin=subprocess.PIPE if args.stdin else None,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    threads = [threading.Thread(target=_pump, args=(proc.stdout, sys.stdout.buffer, Masker(patterns))),
               threading.Thread(target=_pump, args=(proc.stderr, sys.stderr.buffer, Masker(patterns)))]
    for t in threads:
        t.daemon = True
        t.start()
    if args.stdin:
        try:
            proc.stdin.write(value.encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
    try:
        rc = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        rc = proc.wait()
    for t in threads:
        t.join()
    return rc


def cmd_revoke(args):
    vid = vault.read_id(args.target)
    found = vault.revoke(vid)
    print(f"{'revoked' if found else 'nothing to revoke for'} vault {vid}")
    return 0


def cmd_sweep(args):
    done = vault.sweep()
    print(f"swept {len(done)} vault(s)" + (": " + ", ".join(done) if done else ""))
    return 0


def cmd_list(args):
    vault.sweep()
    rows = vault.list_vaults()
    if not rows:
        print("no vaults")
    for m in rows:
        print(f"{m['id']}  expires {vault._iso(m['expires_at'])}  {m.get('label') or '-'}  {m['path']}")
    return 0


def cmd_install_sweeper(args):
    if os.name != "nt":
        raise vault.VaultError("install-sweeper is Windows only; use cron: `pfs.py sweep` hourly")
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
    if os.path.exists(pyw):
        py = pyw
    action = f'"{py}" "{os.path.abspath(__file__)}" sweep'
    r = subprocess.run(["schtasks", "/Create", "/F", "/SC", "HOURLY", "/TN", "pfs-vault-sweep",
                        "/TR", action], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return 0 if r.returncode == 0 else 3


def build_parser():
    p = argparse.ArgumentParser(prog="pfs", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("exec", help="run a command with the value in an env var or on stdin")
    e.add_argument("--vault", required=True, help="path to the .enc vault file")
    e.add_argument("--token", help="vault token (default: $PFS_TOKEN)")
    e.add_argument("--env", metavar="NAME", help="put the value in this env var of the child")
    e.add_argument("--stdin", action="store_true", help="write the value to the child's stdin")
    e.add_argument("--keep-token", action="store_true",
                   help="pass PFS_TOKEN on to the child (default: removed)")
    e.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command and args")
    e.set_defaults(fn=cmd_exec)

    r = sub.add_parser("revoke", help="shred a vault and its machine key")
    r.add_argument("target", help="vault id or .enc path")
    r.set_defaults(fn=cmd_revoke)

    sub.add_parser("sweep", help="shred every expired vault").set_defaults(fn=cmd_sweep)
    sub.add_parser("list", help="list vaults (ids, expiry, labels; never values)").set_defaults(fn=cmd_list)
    sub.add_parser("install-sweeper", help="Windows: hourly scheduled `sweep`").set_defaults(
        fn=cmd_install_sweeper)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "cmd", None) and args.cmd[:1] == ["--"]:
        args.cmd = args.cmd[1:]
    try:
        return args.fn(args)
    except vault.VaultError as e:
        sys.stderr.write(f"pfs: {e}\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
