import asyncio
import http.client
import json
import logging
import os
import urllib.error
import urllib.request
from contextlib import asynccontextmanager

from aio_pika import connect_robust, IncomingMessage
from fastapi import FastAPI

from services.stress_overview_service import build_stress_overview

RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://scare:scare@localhost:5672/')
SPRING_BASE_URL = os.environ.get('SPRING_BASE_URL', 'http://localhost:8080')
INTERNAL_API_SECRET = os.environ.get('INTERNAL_API_SECRET', 'local-dev-only-internal-secret')

REQUEST_QUEUE = 'request_queue'
DEAD_LETTER_QUEUE = 'request_queue.dlq'
# Spring 의 RabbitMqConfig 와 인수가 하나라도 다르면 나중에 선언하는 쪽이 PRECONDITION_FAILED 로 거부된다.
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
    """Spring 저장 API 의 HTTP 상태 코드. 연결 실패나 시간 초과면 None."""
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


async def handle(message: IncomingMessage, put=put_result, sleep=asyncio.sleep):
    """200 을 받은 뒤에만 ack 한다. 그 전에 워커가 죽으면 메시지가 큐로 돌아가 다시 전달되고,
    중복 결과는 Spring 이 200 으로 흡수한다. 계산 실패와 4xx 는 다시 해도 같으므로 바로 데드레터로 보낸다."""
    course_id = None
    try:
        data = json.loads(message.body)
        course_id = data['courseId']
        payload = await asyncio.to_thread(analysis_result, data)
    except Exception as e:
        log.warning('calculation failed, dead-lettering courseId=%s: %r', course_id, e)
        await message.reject(requeue=False)
        return

    status = None
    for delay in (*RETRY_DELAYS, None):
        status = await asyncio.to_thread(put, course_id, payload)
        log.info('PUT courseId=%s status=%s', course_id, status)
        if status == 200:
            await message.ack()
            log.info('acked courseId=%s', course_id)
            return
        if is_permanent(status) or delay is None:
            break
        log.warning('retry courseId=%s in %ss', course_id, delay)
        await sleep(delay)
    log.error('dead-lettering courseId=%s last status=%s', course_id, status)
    await message.reject(requeue=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
    request_queue = await channel.declare_queue(REQUEST_QUEUE, durable=True, arguments=REQUEST_QUEUE_ARGUMENTS)
    await request_queue.consume(handle)
    log.info('Listening on %s', REQUEST_QUEUE)
    yield
    await connection.close()


app = FastAPI(lifespan=lifespan)
