import asyncio
import functools
import http.client
import json
import logging
import os
import time
import urllib.error
import urllib.request
from contextlib import asynccontextmanager

from aio_pika import connect_robust, IncomingMessage
from fastapi import FastAPI

from services.stress_overview_service import build_stress_overview

RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://scare:scare@localhost:5672/')
REQUIRED_ENV = ('SPRING_BASE_URL', 'INTERNAL_API_SECRET')
SPRING_BASE_URL = os.environ.get('SPRING_BASE_URL')
INTERNAL_API_SECRET = os.environ.get('INTERNAL_API_SECRET')

REQUEST_QUEUE = 'request_queue'
DEAD_LETTER_QUEUE = 'request_queue.dlq'
REQUEST_QUEUE_ARGUMENTS = {'x-dead-letter-exchange': '', 'x-dead-letter-routing-key': DEAD_LETTER_QUEUE}
RETRY_DELAYS = (1, 2, 4)
HTTP_TIMEOUT = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('worker')


def analysis_result(data: dict) -> bytes:
    overview = build_stress_overview(data['heartRates'], data['walkingTime'])
    result = {
        'maxStress': overview.max_stress,
        'minStress': overview.min_stress,
        'healingStressAvg': overview.healing_stress_avg,
        'startIdx': overview.start_idx,
        'endIdx': overview.end_idx,
    }
    return json.dumps(result, allow_nan=False).encode()


def put_result(course_id: int, payload: bytes) -> int | None:
    req = urllib.request.Request(
        f'{SPRING_BASE_URL}/internal/v1/walking/{course_id}/analysis-result', data=payload, method='PUT',
        headers={'Content-Type': 'application/json', 'X-Internal-Secret': INTERNAL_API_SECRET})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (OSError, http.client.HTTPException) as e:
        log.warning('PUT courseId=%s failed: %r', course_id, e)
        return None


def is_permanent(status: int | None) -> bool:
    return status is not None and 400 <= status < 500 and status not in (408, 429)


def is_config_error(status: int | None) -> bool:
    return status in (401, 403)


async def handle(message: IncomingMessage, halt, put=put_result, sleep=asyncio.sleep):
    """200 을 받은 뒤에만 ack 한다. 그 전에 워커가 죽으면 메시지가 큐로 돌아가 다시 전달되고,
    중복 결과는 Spring 이 200 으로 흡수한다. 계산 실패와 4xx 는 다시 해도 같으므로 바로 데드레터로 보낸다.
    401/403 은 메시지가 아니라 비밀 설정 문제라 데드레터로 보내지 않고 halt 로 메시지를 돌려놓고 워커를 멈춘다."""
    course_id = None
    try:
        data = json.loads(message.body)
        course_id = data['courseId']
        started = time.perf_counter()
        payload = await asyncio.to_thread(analysis_result, data)
        log.info('calculated courseId=%s samples=%s in %.3fs', course_id, len(data['heartRates']),
                 time.perf_counter() - started)
    except Exception as e:
        log.warning('calculation failed, dead-lettering courseId=%s: %r', course_id, e)
        await message.reject(requeue=False)
        return

    status = None
    for delay in (*RETRY_DELAYS, None):
        started = time.perf_counter()
        status = await asyncio.to_thread(put, course_id, payload)
        log.info('PUT courseId=%s status=%s in %.3fs', course_id, status, time.perf_counter() - started)
        if status == 200:
            await message.ack()
            log.info('acked courseId=%s', course_id)
            return
        if is_config_error(status):
            log.error('Spring rejected INTERNAL_API_SECRET (status=%s), requeueing courseId=%s and stopping worker',
                      status, course_id)
            await halt(message)
            return
        if is_permanent(status) or delay is None:
            break
        log.warning('retry courseId=%s in %ss', course_id, delay)
        await sleep(delay)
    log.error('dead-lettering courseId=%s last status=%s', course_id, status)
    await message.reject(requeue=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f'required environment variables not set: {", ".join(missing)}')
    connection = await connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
    request_queue = await channel.declare_queue(REQUEST_QUEUE, durable=True, arguments=REQUEST_QUEUE_ARGUMENTS)

    async def halt(message: IncomingMessage):
        # 소비 취소나 연결 종료는 진행 중인 이 콜백을 기다려 멈추므로 곧바로 프로세스를 끝낸다.
        # reject 프레임이 나가지 못해도 연결이 끊기면 브로커가 미확인 메시지를 되돌리고, 프로세스가 없으니 다시 받지 않는다.
        await message.reject(requeue=True)
        os._exit(1)

    await request_queue.consume(functools.partial(handle, halt=halt))
    log.info('Listening on %s', REQUEST_QUEUE)
    yield
    await connection.close()


app = FastAPI(lifespan=lifespan)
