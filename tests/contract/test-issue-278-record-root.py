#!/usr/bin/env python3
"""#278: live old/new holders across caller TMPDIRs through production CLIs."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / 'scripts/kaola-acp.py'
LOCATOR = PROJECT / 'scripts/kaola-locate.py'
MOCK = PROJECT / 'tests/contract/mock-acp-agent.py'
spec = importlib.util.spec_from_file_location('paths278', PROJECT / 'scripts/kaola-acp-paths.py')
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)


class AcrossCallerRoots(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='i278-', dir='/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.repo = self.repo.resolve()
        self.a, self.b = self.base / 'a', self.base / 'b'
        self.a.mkdir(); self.b.mkdir()
        self.session = f'codex-I278{os.getpid()}-orchestrator-main'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('KAOLA_')}
        self.env.update(KAOLA_LAUNCH_BACKEND='direct')
        self.env.pop('XDG_RUNTIME_DIR', None)
        self.command = shlex.join([sys.executable, str(MOCK)])
        self.addCleanup(self.cleanup_partial_start)

    def cleanup_partial_start(self):
        # Registered before any start, including a start that fails mid-handshake.
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        for root in (paths.default_root(), self.a / f'kaola-{os.getuid()}'):
            directory = root / 'codex' / self.session / digest
            record = paths.read_record(directory)
            if record and record.get('holder_instance_id'):
                self.cleanup_holder(record, directory)

    def cli(self, verb, *, env=None, session=None, platform='codex', script=CLI, extra=()):
        run = subprocess.run([sys.executable, str(script), platform, verb,
                              '--repo', str(self.repo), '--session', session or self.session,
                              '--command', self.command, *extra],
                             capture_output=True, text=True,
                             env={**self.env, 'TMPDIR': str(self.b), **(env or {})}, timeout=45)
        self.assertTrue(run.stdout.strip(), run.stderr)
        return run.returncode, json.loads(run.stdout)

    def cleanup_holder(self, started, directory):
        # Exact-stop only this fixture; never an installed or consumer Host.
        _, stop = self.cli('stop', extra=('--force', '--expected-holder-instance-id',
                                         started['holder_instance_id']),
                           env={'KAOLA_ACP_RECORD_ROOT': str(directory.parent.parent.parent)})
        self.assertEqual(stop.get('residual_pids', []), [], stop)
        sock = paths.socket_path(directory)
        if sock.exists():
            sock.unlink()
        shutil.rmtree(directory)
        if not any(directory.parent.iterdir()):
            directory.parent.rmdir()

    def assert_discovery(self, started, directory):
        _, status = self.cli('status')
        self.assertNotIn('error', status, status)
        self.assertEqual(status['holder_instance_id'], started['holder_instance_id'])
        self.assertTrue(status['agent_alive'])
        listing = subprocess.run([sys.executable, str(CLI), 'list', '--repo', str(self.repo)],
                                 capture_output=True, text=True,
                                 env={**self.env, 'TMPDIR': str(self.b)}, timeout=15)
        self.assertEqual(listing.returncode, 0, listing.stderr + listing.stdout)
        rows = json.loads(listing.stdout)['rows']
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]['identity'], 'verified')
        self.assertTrue(rows[0]['socket_ok'])
        self.assertEqual(rows[0]['holder_instance_id'], started['holder_instance_id'])
        # Locator may refuse this unregistered dirty development checkout; session facts
        # must still be correct and come from its real receipt command.
        receipt = subprocess.run([sys.executable, str(LOCATOR), '--project', str(self.repo),
                                  '--worker', 'codex', '--session', self.session],
                                 capture_output=True, text=True,
                                 env={**self.env, 'TMPDIR': str(self.b)}, timeout=15)
        located = json.loads(receipt.stdout)
        self.assertTrue(located['session']['present'], located)
        self.assertTrue(located['session']['acp_holder_alive'], located)
        self.assertTrue((directory / 'record.json').is_file())
        # Another platform and another explicit record root cannot open a second Host.
        for override in ({}, {'KAOLA_ACP_RECORD_ROOT': str(self.base / 'other-records')}):
            code, refused = self.cli('start', platform='claude-code',
                                      session=f'claude-code-I278{os.getpid()}-orchestrator-other',
                                      env=override)
            self.assertEqual(code, 1, refused)
            self.assertEqual(refused.get('reason'), 'host-exists', refused)
            self.assertFalse(refused['mutation_performed'])
            self.assertEqual(refused['existing_host']['holder_instance_id'], started['holder_instance_id'])
        # Same name is occupied too; no duplicate hidden behind a different root.
        code, same_other_root = self.cli('start', env={'KAOLA_ACP_RECORD_ROOT': str(self.base / 'other-records')})
        self.assertEqual(code, 1, same_other_root)
        self.assertEqual(same_other_root.get('reason'), 'host-exists', same_other_root)
        _, occupied = self.cli('start')
        self.assertEqual(occupied.get('error', {}).get('code'), 'session-exists', occupied)
        _, sent = self.cli('send', extra=('--text', 'path regression smoke', '--wait'))
        self.assertNotIn('error', sent, sent)
        _, captured = self.cli('capture')
        self.assertNotIn('error', captured, captured)

    def test_new_holder_ignores_tmpdir_and_xdg(self):
        code, started = self.cli('start', env={'TMPDIR': str(self.a),
                                              'XDG_RUNTIME_DIR': str(self.a / 'xdg')})
        self.assertEqual(code, 0, started)
        self.assertNotIn('error', started, started)
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = paths.default_root() / 'codex' / self.session / digest
        self.addCleanup(self.cleanup_holder, started, directory)
        self.assert_discovery(started, directory)
        self.assertEqual(paths.socket_path(directory).parent.resolve(), (Path('/tmp') / f'kaola-{os.getuid()}-acp').resolve())

    def test_running_v091_holder_in_custom_legacy_tmpdir(self):
        # Real v0.9.1 sources, not a simulation of the defective path expression.
        legacy = self.base / 'legacy'
        shutil.copytree(PROJECT / 'scripts', legacy / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(PROJECT / 'platforms', legacy / 'platforms')
        for name in ('kaola-acp.py', 'kaola-acp-holder.py'):
            content = subprocess.run(['git', '-C', str(PROJECT), 'show', f'v0.9.1:scripts/{name}'],
                                     capture_output=True, check=True).stdout
            (legacy / 'scripts' / name).write_bytes(content)
        code, started = self.cli('start', script=legacy / 'scripts/kaola-acp.py',
                                env={'TMPDIR': str(self.a)})
        self.assertEqual(code, 0, started)
        self.assertNotIn('error', started, started)
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.a / f'kaola-{os.getuid()}' / 'codex' / self.session / digest
        self.addCleanup(self.cleanup_holder, started, directory)
        _, baseline = self.cli('status', script=legacy / 'scripts/kaola-acp.py')
        self.assertEqual(baseline.get('error', {}).get('code'), 'no-session',
                         'v0.9.1 must reproduce the cross-TMPDIR false absence')
        # A dead canonical shadow must not hide the live legacy record.
        shadow = paths.default_root() / 'codex' / self.session / digest
        shadow.mkdir(parents=True, exist_ok=True)
        (shadow / 'record.json').write_text(json.dumps({'holder_pid': None, 'repo': str(self.repo)}))
        self.addCleanup(shutil.rmtree, shadow, ignore_errors=True)
        self.assert_discovery(started, directory)
        self.assertEqual(paths.socket_path(directory).parent.resolve(), (self.a / f'kaola-{os.getuid()}-acp').resolve())

    def test_unavailable_legacy_lookup_emits_typed_refusal(self):
        fakebin = self.base / 'bin'; fakebin.mkdir()
        fakeps = fakebin / 'ps'
        fakeps.write_text('#!/bin/sh\nexit 1\n'); fakeps.chmod(0o755)
        env = {**self.env, 'TMPDIR': str(self.b),
               'PATH': str(fakebin) + os.pathsep + os.environ.get('PATH', '')}
        code, status = self.cli('status', env=env)
        self.assertEqual(code, 1, status)
        self.assertEqual(status['error']['code'], 'record-root-mismatch')
        # A capability probe has no record target and must not gain a discovery gate.
        code, preflight = self.cli('preflight', env=env)
        self.assertEqual(code, 0, preflight)
        self.assertNotIn('error', preflight, preflight)
        self.assertIs(preflight['login_required'], False)
        for argv in ([sys.executable, str(CLI), 'list', '--repo', str(self.repo)],
                     [sys.executable, str(LOCATOR), '--project', str(self.repo),
                      '--worker', 'codex', '--session', self.session]):
            run = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            receipt = json.loads(run.stdout)
            self.assertEqual(receipt.get('reason') or receipt['reasons'][0], 'record-root-mismatch')

    def test_aliases_and_unreadable_discovery_are_not_false_absence(self):
        root = self.base / 'records'; root.mkdir()
        alias = self.base / 'alias'; alias.symlink_to(root)
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.a), 'KAOLA_ACP_RECORD_ROOT': ''}), \
             patch.object(paths.subprocess, 'run', side_effect=OSError('process table unavailable')):
            with self.assertRaises(paths.RecordRootMismatch):
                paths.find_directory('codex', self.session, str(self.repo))
            self.assertEqual(paths.roots(root)[0], [root])
            self.assertEqual(paths.record_root(alias), alias)


if __name__ == '__main__':
    unittest.main()
