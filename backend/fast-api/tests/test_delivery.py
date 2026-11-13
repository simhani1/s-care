"""실행: python -m tests.test_delivery  (backend/fast-api 에서)"""
import asyncio
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import main

WALK = {'courseId': 7, 'heartRates': [100 + (i % 7) for i in range(300)], 'walkingTime': 300}


class FakeMessage:
    def __init__(self, body, server=None):
        self.body = json.dumps(body).encode()
        self.server = server
        self.events = []

    async def ack(self):
        self.events.append(('ack', len(self.server.requests) if self.server else 0))

    async def reject(self, requeue=False):
        self.events.append(('reject', requeue))


def fake_spring(statuses):
    """statuses 를 차례로 돌려주는 PUT 서버. 요청마다 (경로, 헤더, 본문) 를 남긴다."""
    script = list(statuses)

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            server.requests.append((self.path, dict(self.headers), body))
            self.send_response(script.pop(0))
            self.send_header('Content-Length', '0')
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.requests = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    main.SPRING_BASE_URL = f'http://127.0.0.1:{server.server_port}'
    return server


def run(message):
    sleeps = []

    async def sleep(seconds):
        sleeps.append(seconds)

    asyncio.run(main.handle(message, sleep=sleep))
    return sleeps


def test_acks_only_after_200_with_backoff():
    server = fake_spring([503, 500, 200])
    message = FakeMessage(WALK, server)
    sleeps = run(message)
    server.shutdown()
    assert message.events == [('ack', 3)], message.events
    assert sleeps == [1, 2]
    path, headers, body = server.requests[0]
    assert path == '/internal/v1/walking/7/analysis-result'
    assert headers['X-Internal-Secret'] == main.INTERNAL_API_SECRET
    assert set(body) == {'maxStress', 'minStress', 'healingStressAvg', 'startIdx', 'endIdx'}


def test_dead_letters_after_three_retries():
    server = fake_spring([503] * 4)
    message = FakeMessage(WALK, server)
    sleeps = run(message)
    server.shutdown()
    assert message.events == [('reject', False)]
    assert sleeps == [1, 2, 4] and len(server.requests) == 4


def test_permanent_client_error_dead_letters_without_retry():
    for status in (400, 403, 404):
        server = fake_spring([status])
        message = FakeMessage(WALK, server)
        assert run(message) == []
        server.shutdown()
        assert message.events == [('reject', False)] and len(server.requests) == 1, status


def test_timeout_and_throttle_are_retried():
    server = fake_spring([429, 408, 200])
    message = FakeMessage(WALK, server)
    assert run(message) == [1, 2]
    server.shutdown()
    assert message.events == [('ack', 3)]


def test_unreachable_spring_is_retried_then_dead_lettered():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    main.SPRING_BASE_URL = f'http://127.0.0.1:{port}'
    message = FakeMessage(WALK)
    assert run(message) == [1, 2, 4]
    assert message.events == [('reject', False)]


def test_calculation_error_dead_letters_without_calling_spring():
    calls = []
    for walk in ({**WALK, 'heartRates': [100, 101, 102]}, {**WALK, 'heartRates': [0] * 300}, {'courseId': 7}):
        message = FakeMessage(walk)
        asyncio.run(main.handle(message, put=lambda *a: calls.append(a) or 200))
        assert message.events == [('reject', False)], walk
    assert calls == []


if __name__ == '__main__':
    import logging
    import warnings
    warnings.filterwarnings('ignore')
    logging.disable(logging.CRITICAL)
    tests = [f for name, f in sorted(globals().items()) if name.startswith('test_')]
    for t in tests:
        t()
        print('ok', t.__name__)
    print(f'{len(tests)} passed')
