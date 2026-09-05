"""Read the installed CLI's native skills/list registry; no model or thread start."""
import importlib.util
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

spec = importlib.util.spec_from_file_location('harness', str(Path(__file__).with_name('native_harness.py')))
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
skill = sys.argv[1]
assert skill in harness.SKILLS
project = harness.LAB / skill / 'project'
process = subprocess.Popen([harness.CLI, 'app-server', '--stdio'], cwd=project,
                           env=harness.environment(skill), stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
messages = queue.Queue()
stderr = []
transcript = []


def read_stdout():
    for line in process.stdout:
        messages.put(line)


def read_stderr():
    stderr.append(process.stderr.read())


threading.Thread(target=read_stdout, daemon=True).start()
err_reader = threading.Thread(target=read_stderr, daemon=True)
err_reader.start()


def send(value):
    transcript.append({'direction': 'client_to_cli', 'message': value})
    process.stdin.write(json.dumps(value) + '\n')
    process.stdin.flush()


def receive(identifier):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            line = messages.get(timeout=min(1, deadline - time.monotonic()))
        except queue.Empty:
            continue
        value = json.loads(line)
        transcript.append({'direction': 'cli_to_client', 'message': value})
        if value.get('id') == identifier:
            return value
    raise TimeoutError('Native skills registry response timed out')


result = {'contract': 'sdlc-ai-spec/native-cli-registry-observation/v1', 'skill': skill,
          'surface': 'codex-cli', 'provider': 'same Codex CLI binary app-server skills/list',
          'project': str(project), 'thread_started': False, 'model_called': False}
code = 1
try:
    send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'post-integration-registry-observer', 'version': '1'}}})
    initialized = receive(1)
    assert 'result' in initialized, initialized
    send({'method': 'initialized', 'params': {}})
    send({'id': 2, 'method': 'skills/list', 'params': {'cwds': [str(project)], 'forceReload': True}})
    response = receive(2)
    assert 'result' in response, response
    result['response'] = response['result']
    result['success'] = True
    code = 0
except Exception as exc:
    result.update(success=False, error=str(exc))
finally:
    try:
        process.stdin.close()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)
    err_reader.join(timeout=2)
    result.update(protocol_transcript=transcript, cli_process_exit_code=process.returncode,
                  shutdown='stdin closed after registry response, terminate only if exit exceeded 5 seconds')
    # This helper is itself captured through the accepted run_step redactor.
    print(json.dumps(result, ensure_ascii=False))
    print(''.join(stderr), file=sys.stderr, end='')
sys.exit(code)
