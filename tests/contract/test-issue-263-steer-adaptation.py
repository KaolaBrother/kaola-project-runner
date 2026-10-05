#!/usr/bin/env python3
"""Noninterrupting request mapping, separate replies and OpenCode adapter guards."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

race = module('race263', ROOT / 'tests/contract/test-issue-65-steer-race.py')
bridge = module('oc263', ROOT / 'scripts/kaola-opencode-acp.py')
cli = module('cli263', ROOT / 'scripts/kaola-acp.py')

class Mapping(unittest.TestCase):
    def setUp(self):
        race.SteerRaceContract.setUp(self)
        self.holder._await_prompt = lambda request: None
    tearDown = race.SteerRaceContract.tearDown
    start_turn = race.SteerRaceContract.start_turn
    settle = race.SteerRaceContract.settle

    def response(self, response, platform='grok', method='_x.ai/interject'):
        self.holder.args.platform = platform
        first, turn = self.start_turn('original')
        self.agent.wait_response = lambda request, timeout: response
        result = self.holder.op_steer({'method': method, 'text': 'ADOPT263'})
        self.assertEqual(result['turn_request_id'], first['turn_request_id'])
        self.assertTrue(result['turn_request_id_preserved'])
        self.assertTrue(turn['active'])
        self.assertEqual(len(self.agent.prompts_sent()), 2 if method == 'session/prompt' else 1)
        self.assertFalse(self.agent.cancels_sent())
        return result, self.agent.sent[-1]['params']

    def test_grok_top_level_text_and_queued_ack_are_not_adoption(self):
        native = {'result': {'result': {'status': 'queued'}}}
        result, params = self.response(native)
        self.assertEqual(params, {'sessionId': 'ses-race', 'text': 'ADOPT263'})
        self.assertEqual(result['steer_response'], native)
        self.assertEqual(result['steer_native_status'], 'queued')
        self.assertEqual(result['steer_outcome'], 'written')
        self.assertEqual(result['steer_confirmation'], 'native-queued')
        self.assertIsNone(result['steer_consumed'])
        self.assertTrue(result['mutation_performed'])

    def test_grok_error_and_malformed_reply_do_not_claim_admission(self):
        for native in ({'result': {'error': 'bad'}}, {'result': []}, {'result': 'bad'}):
            self.agent.wait_response = lambda request, timeout, n=native: n
            if not self.holder.turn['active']:
                self.start_turn('original')
            result = self.holder.op_steer({'method': '_x.ai/interject', 'text': 'ADOPT263'})
            self.assertEqual(result['steer_outcome'], 'unknown')
            self.assertIsNone(result['mutation_performed'])

    def test_grok_timeout_does_not_resend(self):
        result, _ = self.response(None)
        self.assertEqual(result['steer_outcome'], 'unknown')
        self.assertEqual(len(self.agent.sent), 2)

    def test_grok_refusal_keeps_original_error(self):
        native = {'error': {'code': -32602, 'data': 'invalid text', 'message': 'bad params'}}
        result, _ = self.response(native)
        self.assertEqual(result['steer_outcome'], 'rejected')
        self.assertFalse(result['mutation_performed'])
        self.assertEqual(result['steer_response'], native)

    def test_idle_never_writes(self):
        result = self.holder.op_steer({'method': '_x.ai/interject', 'text': 'ADOPT263'})
        self.assertEqual(result['steer_reason'], 'no-active-turn')
        self.assertEqual(self.agent.sent, [])

    def test_opencode_guard_and_admission_remain_distinct(self):
        result, params = self.response({'result': {'outcome': 'written',
            'confirmation': 'native-admitted'}}, 'opencode', '_session/steering')
        self.assertEqual(params['_meta']['steering']['expectedTurnId'], result['turn_request_id'])
        self.assertIsNone(result['steer_consumed'])
        self.assertEqual(result['steer_confirmation'], 'native-admitted')

    def test_standard_prompt_completion_is_not_model_adoption(self):
        for platform in ('devin', 'droid'):
            self.holder.args.platform = platform
            self.agent.wait_response = lambda request, timeout: {'result': {'stopReason': 'end_turn'}}
            if not self.holder.turn['active']:
                self.start_turn('original')
            original = self.holder.turn.copy()
            result = self.holder.op_steer({'method': 'session/prompt', 'text': 'new'})
            self.assertEqual(self.agent.sent[-1]['params'], {'sessionId': 'ses-race',
                'prompt': [{'type': 'text', 'text': 'new'}]})
            self.assertEqual(result['steer_outcome'], 'written')
            self.assertIsNone(result['steer_consumed'])
            self.assertEqual(result['steer_confirmation'], 'prompt-completed')
            self.assertEqual(result['steer_stop_reason'], 'end_turn')
            self.assertEqual(self.holder.turn, original)
            self.assertFalse(self.agent.cancels_sent())

    def test_standard_prompt_late_reply_survives_timeout_and_later_turn(self):
        self.holder.args.platform = 'devin'
        first, _ = self.start_turn('original')
        release, logged = threading.Event(), threading.Event()
        raw = {'id': 2, 'result': {'stopReason': 'end_turn', '_meta': {'userMessageId': 'owned'}}}
        def late(request, timeout):
            release.wait(3)
            return raw
        self.agent.wait_response = late
        append = self.holder.events.append
        def record(event, **kwargs):
            cursor = append(event, **kwargs)
            if event['kind'] == 'steer_reply': logged.set()
            return cursor
        self.holder.events.append = record
        result = self.holder.op_steer({'method': 'session/prompt', 'text': 'new', 'timeout': .01})
        self.assertEqual(result['steer_outcome'], 'written')
        self.assertEqual(result['steer_confirmation'], 'write-only')
        self.assertEqual(result['error']['code'], 'steer-reply-pending')
        self.settle(first['turn_request_id'])
        second, _ = self.start_turn('later')
        release.set()
        self.assertTrue(logged.wait(3))
        self.assertEqual(self.holder.turn['request_id'], second['turn_request_id'])
        self.assertTrue(self.holder.turn['active'])
        events = [json.loads(line) for line in self.holder.events.path.read_text().splitlines()]
        reply = next(event for event in events if event['kind'] == 'steer_reply')
        self.assertEqual(reply['response'], raw)
        self.assertEqual(reply['request_id'], result['steer_request_id'])
        self.assertEqual(reply['turn_request_id'], first['turn_request_id'])
        self.assertEqual(len(self.agent.prompts_sent()), 3)
        self.assertFalse(self.agent.cancels_sent())

    def test_later_turn_queue_is_admission_not_rejection_or_processing(self):
        result, _ = self.response({'result': {'outcome': 'queued'}}, 'zcode', '_session/steering')
        self.assertEqual(result['steer_outcome'], 'written')
        self.assertIsNone(result['steer_consumed'])
        self.assertEqual(result['steer_native_outcome'], 'queued')
        self.assertTrue(result['mutation_performed'])

    def test_standard_prompt_refusal_does_not_trigger_cancel_or_replay(self):
        result, _ = self.response({'error': {'code': -32600, 'message': 'refused'}},
                                  'droid', 'session/prompt')
        self.assertEqual(result['steer_outcome'], 'rejected')
        self.assertFalse(result['mutation_performed'])
        self.assertEqual(len(self.agent.prompts_sent()), 2)

    def test_standard_prompt_execution_error_does_not_claim_no_effect(self):
        result, _ = self.response({'error': {'code': -32000, 'message': 'agent exited'}},
                                  'devin', 'session/prompt')
        self.assertEqual(result['steer_outcome'], 'unknown')
        self.assertIsNone(result['steer_consumed'])
        self.assertIsNone(result['mutation_performed'])

    def queued(self):
        first, turn = self.start_turn('original')
        logged = threading.Event()
        append = self.holder.events.append
        def record(event, **kwargs):
            cursor = append(event, **kwargs)
            if event['kind'] == 'steer_followup': logged.set()
            return cursor
        self.holder.events.append = record
        result = self.holder.op_steer({'method': 'session/prompt', 'text': 'later',
                                      'delivery': 'after-turn'})
        return first, turn, result, logged

    def test_after_turn_delivery_waits_then_uses_owned_prompt_lifecycle(self):
        first, original, result, logged = self.queued()
        self.assertEqual(result['steer_outcome'], 'queued')
        self.assertEqual(result['steer_confirmation'], 'holder-queued')
        self.assertFalse(result['steer_native_written'])
        self.assertNotIn('turn_request_id_preserved', result)
        self.assertNotIn('turn_request_id_after', result)
        self.assertEqual(len(self.agent.prompts_sent()), 1)
        self.settle(first['turn_request_id'])
        self.assertTrue(logged.wait(3))
        self.assertEqual(original['outcome'], 'turn_completed')
        self.assertEqual(original['stop_reason'], 'end_turn')
        self.assertNotEqual(self.holder.turn['request_id'], first['turn_request_id'])
        event = next(json.loads(line) for line in self.holder.events.path.read_text().splitlines()
                     if json.loads(line)['kind'] == 'steer_followup')
        self.assertEqual(event['original_turn']['request_id'], first['turn_request_id'])
        self.assertEqual(event['original_turn']['stop_reason'], 'end_turn')
        self.assertNotEqual(event['receipt']['turn_request_id'], first['turn_request_id'])
        self.assertEqual(self.agent.prompts_sent()[-1]['params'],
            {'sessionId': 'ses-race', 'prompt': [{'type': 'text', 'text': 'later'}]})
        self.assertFalse(self.agent.cancels_sent())

    def test_after_turn_competing_prompt_refuses_without_cancel_or_replay(self):
        admitted, release = threading.Event(), threading.Event()
        op_prompt = self.holder.op_prompt
        def delay(params):
            if params.get('text') == 'later':
                admitted.set(); release.wait(3)
            return op_prompt(params)
        self.holder.op_prompt = delay
        first, _, result, logged = self.queued()
        self.settle(first['turn_request_id'])
        self.assertTrue(admitted.wait(3))
        second, _ = self.start_turn('competing')
        release.set()
        self.assertTrue(logged.wait(3))
        event = next(json.loads(line) for line in self.holder.events.path.read_text().splitlines()
                     if json.loads(line)['kind'] == 'steer_followup')
        self.assertFalse(event['receipt']['mutation_performed'])
        self.assertEqual(event['receipt']['active_turn_request_id'], second['turn_request_id'])
        self.assertEqual(len(self.agent.prompts_sent()), 2)
        self.assertFalse(self.agent.cancels_sent())

    def test_after_turn_stop_does_not_send_or_restart(self):
        first, _, result, logged = self.queued()
        self.holder.stop_requested = True
        self.settle(first['turn_request_id'])
        self.assertTrue(logged.wait(3))
        event = next(json.loads(line) for line in self.holder.events.path.read_text().splitlines()
                     if json.loads(line)['kind'] == 'steer_followup')
        self.assertEqual(event['receipt']['outcome'], 'stopping')
        self.assertFalse(event['receipt']['mutation_performed'])
        self.assertEqual(len(self.agent.prompts_sent()), 1)
        self.assertFalse(self.agent.cancels_sent())

class DeliveryCompatibility(unittest.TestCase):
    def test_old_live_holder_refuses_only_missing_after_turn_operation(self):
        record = {'holder_pid': 123, 'holder_features': ['heartbeat-state/2'],
                  'last_prompt': {'mutation_status': 'in_progress'}}
        args = SimpleNamespace(manifest={'steering_delivery': 'after-turn'})
        with patch.object(cli, 'read_record', return_value=record), \
             patch.object(cli, 'pid_alive', return_value=True):
            result = cli.steer_after_turn_refusal(args, Path('/unused'))
            self.assertEqual(result['error']['code'], 'steer-holder-outdated')
            self.assertFalse(result['mutation_performed'])
            self.assertFalse(result['steer_consumed'])
            for platform in ('codex', 'claude-code', 'zcode', 'grok', 'opencode', 'devin', 'droid'):
                args.manifest = {'id': platform}
                self.assertIsNone(cli.steer_after_turn_refusal(args, Path('/unused')))

    def test_current_operation_and_dead_holder_keep_existing_routes(self):
        args = SimpleNamespace(manifest={'steering_delivery': 'after-turn'})
        with patch.object(cli, 'read_record', return_value={
                'holder_pid': 123, 'holder_features': ['steer-after-turn/1']}), \
             patch.object(cli, 'pid_alive', return_value=True):
            self.assertIsNone(cli.steer_after_turn_refusal(args, Path('/unused')))
        with patch.object(cli, 'read_record', return_value={'holder_pid': 123}), \
             patch.object(cli, 'pid_alive', return_value=False):
            self.assertIsNone(cli.steer_after_turn_refusal(args, Path('/unused')))

class OpenCodeAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kpr263-')
        self.child = type('Child', (), {'stdin': io.StringIO(), 'stdout': io.StringIO()})()
        self.adapter = bridge.Adapter(self.child, str(Path(self.tmp.name) / 's.sock'))
        self.prompt = {'jsonrpc':'2.0', 'id':17, 'method':'session/prompt',
                       'params':{'sessionId':'ses_owned','prompt':[{'type':'text','text':'original'}]}}
        self.steer = {'params': {'sessionId':'ses_owned', 'prompt':[{'type':'text','text':'new'}],
            '_meta':{'steering':{'expectedTurnId':17}}}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_foreign_or_replaced_or_ended_turn_writes_nothing(self):
        self.adapter.input(self.prompt)
        before = self.child.stdin.getvalue()
        for session, expected in [('ses_foreign',17),('ses_owned',16),('ses_owned',None)]:
            self.steer['params']['sessionId'] = session
            self.steer['params']['_meta']['steering']['expectedTurnId'] = expected
            self.assertEqual(self.adapter.steer(self.steer)['outcome'], 'promptRequired')
        self.assertEqual(self.child.stdin.getvalue(), before)

    def test_native_concurrent_refusal_does_not_replace_owner(self):
        self.adapter.input(self.prompt)
        self.adapter.input({**self.prompt,'id':18})
        self.assertEqual(self.adapter.active, {'ses_owned':17})
        self.assertEqual(self.adapter.pending, {'17':'ses_owned'})
        # Native stream and original response remain unchanged.
        replies = [{'jsonrpc':'2.0','id':18,'error':{'code':-32000}},
                   {'method':'session/update','params':{'sessionId':'ses_owned'}},
                   {'jsonrpc':'2.0','id':17,'result':{'stopReason':'end_turn'}}]
        self.child.stdout = io.StringIO(''.join(json.dumps(r)+'\n' for r in replies))
        actual = []
        self.adapter.emit = actual.append
        self.adapter.native_output()
        self.assertEqual(actual, replies)
        self.assertEqual(self.adapter.active, {})
        self.assertEqual(self.adapter.steer(self.steer)['outcome'], 'promptRequired')

    def test_unknown_after_write_is_not_replayed(self):
        self.adapter.input(self.prompt)
        count = []
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(self.adapter.endpoint);server.listen()
            def answer():
                connection,_ = server.accept()
                with connection:
                    count.append(connection.recv(4096))
                    connection.sendall(b'not-json\n')
            thread = threading.Thread(target=answer);thread.start()
            result = self.adapter.steer(self.steer);thread.join(3)
        self.assertEqual(result['outcome'], 'unknown')
        self.assertEqual(len(count), 1)
        self.assertEqual(json.loads(count[0]), {'sessionId':'ses_owned','text':'new'})
        self.assertNotIn('cancel', self.child.stdin.getvalue())

    def test_native_exit_is_reported_and_process_overlay_is_removed(self):
        import sys
        fake = Path(self.tmp.name) / 'opencode'
        snapshot = Path(self.tmp.name) / 'config.json'
        fake.write_text('#!' + sys.executable + '\n' +
            'import json,os,sys\n' +
            f'open({str(snapshot)!r},"w").write(json.dumps({{"config":json.loads(os.environ["OPENCODE_CONFIG_CONTENT"]),"args":sys.argv[1:]}}))\n' +
            'request=json.loads(sys.stdin.readline())\n' +
            'print(json.dumps({"jsonrpc":"2.0","id":request["id"],"result":{"protocolVersion":1}}),flush=True)\n' +
            'sys.exit(7)\n')
        fake.chmod(0o700)
        original = {'agents':{'build':{'model':'provider/model'}},'plugins':['file:///keep-plugin']}
        env = {**os.environ,'OPENCODE_BIN':str(fake),'OPENCODE_CONFIG_CONTENT':json.dumps(original)}
        process = subprocess.Popen([sys.executable,str(ROOT/'scripts/kaola-opencode-acp.py')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        try:
            process.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize"}\n');process.stdin.flush()
            result = json.loads(process.stdout.readline())
            self.assertEqual(result['result']['protocolVersion'], 1)
            self.assertEqual(process.wait(timeout=5), 7)
            received = json.loads(snapshot.read_text())
            self.assertEqual(received["args"], ["acp"])
            overlay = received["config"]
            self.assertEqual(overlay['agents'], original['agents'])
            self.assertEqual(overlay['plugins'][0], original['plugins'][0])
            added = overlay['plugins'][-1]
            self.assertFalse(Path(added['options']['socket']).parent.exists())
            self.assertEqual(json.loads(env['OPENCODE_CONFIG_CONTENT']), original)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=5)
            process.stdin.close();process.stdout.close();process.stderr.close()

    @unittest.skipUnless(shutil.which('node'), 'node unavailable: plugin API fixture skipped')
    def test_plugin_calls_native_api_without_resuming_idle_execution(self):
        # This checks the actual plugin bytes with a native-API fixture. The
        # separate live receipt establishes installed CLI adoption.
        source = f'''import plugin from {json.dumps((ROOT/'scripts/kaola-opencode-steer.mjs').as_uri())};
          const dispose=await plugin.setup({{location:{{directory:"/owned"}},options:{{socket:process.argv[1],directory:"/owned"}},
          session:{{prompt:async input=>{{console.log(JSON.stringify(input));return {{id:"msg_owned",sessionID:input.sessionID,delivery:input.delivery,type:"user",time:{{created:1}}}};}}}}}});
          process.on("SIGTERM",async()=>{{await dispose();process.exit(0)}});'''
        child = subprocess.Popen(['node','--input-type=module','-e',source,self.adapter.endpoint],stdout=subprocess.PIPE,text=True)
        try:
            import time
            for _ in range(100):
                if Path(self.adapter.endpoint).exists():break
                time.sleep(.02)
            self.adapter.input(self.prompt)
            result = self.adapter.steer(self.steer)
            self.assertEqual(result['confirmation'], 'native-admitted')
            original = json.loads(child.stdout.readline())
            self.assertEqual(original, {'sessionID':'ses_owned','text':'new','delivery':'steer','resume':False})
        finally:
            child.terminate();child.wait(timeout=5)
            child.stdout.close()

if __name__ == '__main__':
    unittest.main()
