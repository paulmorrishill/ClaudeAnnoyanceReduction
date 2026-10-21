"""Tests for vault.py and pfs.py.  Run:  python -m unittest test_vault -v  (from scripts/)."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pfs  # noqa: E402
import vault  # noqa: E402

PFS = os.path.join(HERE, "pfs.py")
SECRET = "sk_test_51Habc/DEF+ghi==jkl"
MULTI = "$Env:AWS_ACCESS_KEY_ID = 'AKIAEXAMPLE1234'\nAWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG\n"


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = os.path.join(self.tmp.name, "store")
        os.environ["PFS_STORE_DIR"] = self.store
        self.enc = os.path.join(self.tmp.name, "v.enc")

    def tearDown(self):
        os.environ.pop("PFS_STORE_DIR", None)
        self.tmp.cleanup()

    def make(self, value=SECRET, ttl=3600, **kw):
        return vault.create_vault(value, self.enc, ttl, **kw)


class VaultTests(StoreCase):
    def test_roundtrip_arbitrary_text(self):
        for value in [SECRET, MULTI, "Jane Doe, 1 High St, CT1 1AA\nDOB 1980-01-01", "ünïcødé ✓", " x "]:
            _, token, _ = self.make(value)
            self.assertEqual(vault.open_vault(self.enc, token), value)

    def test_no_plaintext_on_disk(self):
        self.make(MULTI)
        blobs = [open(self.enc, "rb").read()] + [
            open(os.path.join(self.store, n), "rb").read() for n in os.listdir(self.store)]
        for b in blobs:
            self.assertNotIn(b"wJalrXUtnFEMI", b)
            self.assertNotIn(b"AKIAEXAMPLE", b)

    def test_wrong_token_fails(self):
        vid, token, _ = self.make()
        bad = "pfs1." + vid + "." + vault._b64e(b"\0" * 32)
        with self.assertRaisesRegex(vault.VaultError, "decrypt failed"):
            vault.open_vault(self.enc, bad)

    def test_token_for_other_vault_fails(self):
        self.make()
        other = os.path.join(self.tmp.name, "o.enc")
        _, token2, _ = vault.create_vault("x" * 10, other, 3600)
        with self.assertRaisesRegex(vault.VaultError, "token is for vault"):
            vault.open_vault(self.enc, token2)

    def test_bad_token_formats(self):
        self.make()
        for t in ["", "nope", "pfs1.a.b.c", "pfs2.x.y", "pfs1.x." + vault._b64e(b"short")]:
            with self.assertRaisesRegex(vault.VaultError, "bad token format"):
                vault.open_vault(self.enc, t)

    def test_token_alone_useless_without_machine_half(self):
        vid, token, _ = self.make()
        os.remove(os.path.join(self.store, vid + ".key"))
        with self.assertRaisesRegex(vault.VaultError, "machine key"):
            vault.open_vault(self.enc, token)

    def test_editing_expiry_breaks_decrypt(self):
        _, token, _ = self.make()
        doc = json.load(open(self.enc))
        doc["expires_at"] += 10 ** 6
        json.dump(doc, open(self.enc, "w"))
        with self.assertRaisesRegex(vault.VaultError, "decrypt failed"):
            vault.open_vault(self.enc, token)

    def test_editing_ciphertext_breaks_decrypt(self):
        _, token, _ = self.make()
        doc = json.load(open(self.enc))
        ct = bytearray(vault._b64d(doc["ct"]))
        ct[0] ^= 1
        doc["ct"] = vault._b64e(bytes(ct))
        json.dump(doc, open(self.enc, "w"))
        with self.assertRaisesRegex(vault.VaultError, "decrypt failed"):
            vault.open_vault(self.enc, token)

    def test_expired_vault_refused_and_shredded(self):
        vid, token, exp = self.make(ttl=60)
        with self.assertRaisesRegex(vault.VaultError, "expired"):
            vault.open_vault(self.enc, token, now=exp)
        self.assertFalse(os.path.exists(self.enc))
        self.assertFalse(os.path.exists(os.path.join(self.store, vid + ".key")))

    def test_revoke_by_id_and_path(self):
        vid, token, _ = self.make()
        self.assertTrue(vault.revoke(vault.read_id(self.enc)))
        self.assertFalse(os.path.exists(self.enc))
        self.assertEqual(os.listdir(self.store), [])
        self.assertFalse(vault.revoke(vid))
        with self.assertRaises(vault.VaultError):
            vault.read_id("not-a-vault")

    def test_sweep_only_expired_and_orphans(self):
        old_id, _, _ = self.make(ttl=60, now=time.time() - 120)
        keep = os.path.join(self.tmp.name, "keep.enc")
        keep_id, keep_tok, _ = vault.create_vault("keep-me", keep, 3600)
        open(os.path.join(self.store, "deadbeefdeadbeef.key"), "wb").write(b"x")
        done = vault.sweep()
        self.assertIn(old_id, done)
        self.assertIn("deadbeefdeadbeef", done)
        self.assertNotIn(keep_id, done)
        self.assertEqual(vault.open_vault(keep, keep_tok), "keep-me")

    def test_label_listed_value_not(self):
        self.make(label="stripe test key")
        rows = vault.list_vaults()
        self.assertEqual(rows[0]["label"], "stripe test key")
        self.assertNotIn(SECRET, json.dumps(rows))

    def test_parse_ttl(self):
        self.assertEqual(vault.parse_ttl("900"), 900)
        self.assertEqual(vault.parse_ttl("30m"), 1800)
        self.assertEqual(vault.parse_ttl("12h"), 43200)
        self.assertEqual(vault.parse_ttl("2d"), 172800)
        for bad in ["", "x", "1w", "-5"]:
            with self.assertRaises(vault.VaultError):
                vault.parse_ttl(bad)

    def test_create_rejects_bad_input(self):
        with self.assertRaises(vault.VaultError):
            vault.create_vault(b"bytes", self.enc, 60)
        with self.assertRaises(vault.VaultError):
            vault.create_vault("x", self.enc, 0)


class MaskerTests(unittest.TestCase):
    def run_stream(self, value, data, chunk):
        m = pfs.Masker(pfs.mask_patterns([value]))
        out = b"".join(m.feed(data[i:i + chunk]) for i in range(0, len(data), chunk))
        return out + m.flush()

    def test_masks_raw_and_encoded_forms_across_chunk_sizes(self):
        b = SECRET.encode()
        forms = [b, base64.b64encode(b), base64.urlsafe_b64encode(b).rstrip(b"="),
                 b"sk_test_51Habc%2FDEF%2Bghi%3D%3Djkl"]
        for form in forms:
            data = b"before " + form + b" after\n"
            for chunk in (1, 3, 7, 64):
                out = self.run_stream(SECRET, data, chunk)
                self.assertEqual(out, b"before *** after\n", (form, chunk))

    def test_masks_each_line_of_multiline_value(self):
        out = self.run_stream(MULTI, b"x AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG y", 5)
        self.assertNotIn(b"wJalrXUtnFEMI", out)

    def test_ordinary_output_untouched_and_not_delayed(self):
        m = pfs.Masker(pfs.mask_patterns([SECRET]))
        self.assertEqual(m.feed(b"hello world\n"), b"hello world\n")
        self.assertEqual(m.flush(), b"")

    def test_holds_only_possible_prefix(self):
        m = pfs.Masker(pfs.mask_patterns([SECRET]))
        self.assertEqual(m.feed(b"abc sk_te"), b"abc ")
        self.assertEqual(m.feed(b"a\n"), b"sk_tea\n")

    def test_short_values_not_masked(self):
        self.assertEqual(pfs.mask_patterns(["abc"]), [])


class ExecTests(StoreCase):
    def run_pfs(self, *args, token=None, stdin=None):
        env = dict(os.environ)
        if token:
            env["PFS_TOKEN"] = token
        return subprocess.run([sys.executable, PFS, *args], env=env, capture_output=True,
                              input=stdin, timeout=60)

    def test_env_mode_value_reaches_child_but_output_masked(self):
        _, token, _ = self.make()
        child = ("import os,sys; v=os.environ['MY_KEY'];"
                 "print('len', len(v)); print('leak', v); sys.stderr.write('err '+v+'\\n');"
                 "print('match', v == %r); print('tok', os.environ.get('PFS_TOKEN'))" % SECRET)
        r = self.run_pfs("exec", "--vault", self.enc, "--env", "MY_KEY", "--",
                         sys.executable, "-c", child, token=token)
        out, err = r.stdout.decode(), r.stderr.decode()
        self.assertEqual(r.returncode, 0, err)
        self.assertIn("len %d" % len(SECRET), out)
        self.assertIn("leak ***", out)
        self.assertIn("err ***", err)
        self.assertIn("match True", out)
        self.assertIn("tok None", out)
        self.assertNotIn(SECRET, out + err)
        self.assertNotIn(token, out + err)

    def test_stdin_mode_and_token_flag_and_exit_code(self):
        _, token, _ = self.make(MULTI)
        child = "import sys; d=sys.stdin.read(); print(d==%r); sys.exit(7)" % MULTI
        r = self.run_pfs("exec", "--vault", self.enc, "--token", token, "--stdin", "--",
                         sys.executable, "-c", child)
        self.assertEqual(r.returncode, 7)
        self.assertEqual(r.stdout.decode().strip(), "True")

    def test_keep_token_passes_it_through_masked(self):
        _, token, _ = self.make()
        child = "import os; print(os.environ['PFS_TOKEN'] == %r)" % token
        r = self.run_pfs("exec", "--vault", self.enc, "--env", "K", "--keep-token", "--",
                         sys.executable, "-c", child, token=token)
        self.assertEqual(r.stdout.decode().strip(), "True")

    def test_exec_usage_errors(self):
        _, token, _ = self.make()
        cases = [
            (["exec", "--vault", self.enc, "--env", "K", "--", sys.executable, "-c", "0"], None, "no token"),
            (["exec", "--vault", self.enc, "--", sys.executable, "-c", "0"], token, "exactly one"),
            (["exec", "--vault", self.enc, "--env", "K", "--stdin", "--", "x"], token, "exactly one"),
            (["exec", "--vault", self.enc, "--env", "1BAD", "--", "x"], token, "not a valid env"),
            (["exec", "--vault", self.enc, "--env", "K"], token, "no command"),
            (["exec", "--vault", self.enc + ".nope", "--env", "K", "--", "x"], token, "not found"),
        ]
        for args, tok, msg in cases:
            r = self.run_pfs(*args, token=tok)
            self.assertEqual(r.returncode, 3, args)
            self.assertIn(msg, r.stderr.decode(), args)

    def test_no_plaintext_reader_command(self):
        r = self.run_pfs("--help")
        for word in ("cat", "show", "read", "get", "decrypt"):
            self.assertNotIn("{%s" % word, r.stdout.decode())
        self.assertNotIn(",cat", r.stdout.decode())

    def test_revoke_list_sweep_cli(self):
        vid, token, _ = self.make(label="lbl")
        self.assertIn(vid, self.run_pfs("list").stdout.decode())
        self.assertIn("revoked", self.run_pfs("revoke", self.enc).stdout.decode())
        r = self.run_pfs("exec", "--vault", self.enc, "--env", "K", "--", "x", token=token)
        self.assertEqual(r.returncode, 3)
        self.assertIn("swept 0", self.run_pfs("sweep").stdout.decode())


class PromptEncryptTests(StoreCase):
    """Runs prompt_for_sensitive.main() with a patched mainloop that types and clicks Save."""

    def run_prompt(self, typed, *extra):
        import contextlib
        import io
        import tkinter as tk
        from tkinter import ttk
        import prompt_for_sensitive as pfs_prompt

        def fake_mainloop(root, n=0):
            def walk(w):
                yield w
                for c in w.winfo_children():
                    yield from walk(c)
            widgets = list(walk(root))
            entry = next(w for w in widgets if isinstance(w, (ttk.Entry, tk.Text)))
            entry.insert("end" if isinstance(entry, tk.Text) else 0, typed)
            next(w for w in widgets if isinstance(w, ttk.Button) and w.cget("text") == "Save").invoke()

        raw = io.BytesIO()
        out = io.TextIOWrapper(raw, encoding="utf-8")
        orig_argv, orig_loop = sys.argv, tk.Tk.mainloop
        sys.argv = ["prompt", "--encrypt", "--out", self.enc, *extra]
        tk.Tk.mainloop = fake_mainloop
        try:
            with contextlib.redirect_stdout(out):
                rc = pfs_prompt.main()
        finally:
            sys.argv, tk.Tk.mainloop = orig_argv, orig_loop
        out.flush()
        return rc, raw.getvalue().decode("utf-8")

    def test_encrypt_prints_token_not_value_and_vault_opens(self):
        rc, out = self.run_prompt(MULTI, "--type", "multiline", "--ttl", "10m", "--label", "aws")
        self.assertEqual(rc, 0)
        self.assertNotIn("wJalrXUtnFEMI", out)
        token = next(l for l in out.splitlines() if l.startswith("PFS_TOKEN="))[len("PFS_TOKEN="):]
        self.assertEqual(vault.open_vault(self.enc, token), MULTI)
        meta = vault.list_vaults()[0]
        self.assertEqual(meta["label"], "aws")
        self.assertAlmostEqual(meta["expires_at"] - meta["created"], 600, delta=1)

    def test_bad_ttl_fails_before_window(self):
        sys.argv, orig = ["prompt", "--encrypt", "--ttl", "1w", "--out", self.enc], sys.argv
        try:
            import prompt_for_sensitive as pfs_prompt
            self.assertEqual(pfs_prompt.main(), 3)
        finally:
            sys.argv = orig
        self.assertFalse(os.path.exists(self.enc))


if __name__ == "__main__":
    unittest.main()
