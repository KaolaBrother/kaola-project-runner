#!/usr/bin/env python3
"""Grok native request/reply mapping and OpenCode original-turn adapter guards."""
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

ROOT = Path(__file__).resolve().parents[2]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

race = module('race263', ROOT / 'tests/contract/test-issue-65-steer-race.py')
bridge = module('oc263', ROOT / 'scripts/kaola-opencode-acp.py')

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
        self.assertEqual(len(self.agent.prompts_sent()), 1)
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
