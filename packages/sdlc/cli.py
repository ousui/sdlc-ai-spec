"""One CLI entry; stdout contains exactly one JSON response."""
import argparse
import sys
from .common import API, MAX_REQUEST_BYTES, Fault, canonical, loads
from .protocol import contract
from .runtime import Runtime, failure


def main(argv=None):
    parser = argparse.ArgumentParser(description='SDLC v2 public JSON runtime')
    parser.add_argument('--root', default='.')
    parser.add_argument('--request', default='-', help='UTF-8 JSON file or - for stdin')
    parser.add_argument('--contract', action='store_true')
    args = parser.parse_args(argv)
    if args.contract:
        print(canonical(contract()).decode())
        return 0
    try:
        if args.request == '-':
            raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES+1)
        else:
            with open(args.request, 'rb') as stream:
                raw = stream.read(MAX_REQUEST_BYTES+1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise Fault('REQUEST_LIMIT', 'Request exceeds 4 MiB')
        request = loads(raw)
        runtime = Runtime(args.root)
        response = runtime.invoke(request)
        if response['ok'] and request['command'] == 'render':
            from .rendering import render_change
            project = request.get('project_id', runtime.store.config()['project_id'])
            try:
                response['data']['path'] = str(render_change(runtime.store, project, request['change_id']))
            except (OSError, Fault) as exc:
                response['warnings'] = [{'code': 'VIEW_FAILED', 'message': str(exc)}]
    except (Fault, OSError) as exc:
        fault = exc if isinstance(exc, Fault) else Fault('REQUEST_IO', str(exc), status='runtime_error')
        response = failure(fault)
        response['diagnostic_path'] = Runtime(args.root).bootstrap({'raw_request': '[unparsed]'}, response)
    print(canonical(response).decode())
    return 0 if response['ok'] else {'invalid_input': 2, 'conflict': 2, 'blocked': 3, 'needs_input': 3, 'needs_work': 3, 'unknown': 3}.get(response['status'], 4)


if __name__ == '__main__':
    sys.exit(main())
