import json
import os
from contextlib import asynccontextmanager

from aio_pika import connect_robust, IncomingMessage, Message
from fastapi import FastAPI

from exceptions.custom_exceptions import CalculateFailedException
from models.response_models import StressOverview
from services.calculate_service import *
from services.stress_overview_service import *

# 접속 정보는 코드에 두지 않는다. 기본값은 backend/docker-compose.yml 의 로컬 브로커
RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://scare:scare@localhost:5672/')


@asynccontextmanager
async def lifespan(app: FastAPI):
    # RabbitMQ 연결 및 큐 선언
    connection = await connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    # 요청 및 응답 큐 설정
    request_queue = await channel.declare_queue('request_queue', durable=True)
    await channel.declare_queue('response_queue', durable=True)

    async def process_message(message: IncomingMessage):
        async with message.process():
            body = message.body.decode()
            data = json.loads(body)

            course_id = data.get('courseId')
            heart_rates = data.get('heartRates')
            walking_time = data.get('walkingTime')

            # 계산 수행
            result = calc_multiple_stress_index(heart_rates, walking_time)

            response = {
                'courseId': course_id,
                'maxStress': result.max_stress,
                'minStress': result.min_stress,
                'healingStressAvg': result.healing_stress_avg,
                'startIdx': result.start_idx,
                'endIdx': result.end_idx
            }

            # 결과를 응답 큐에 전송
            await channel.default_exchange.publish(
                Message(body=json.dumps(response).encode()),
                routing_key='response_queue'
            )

            print(f"Response sent to response_queue: {response}")

    # 요청 큐 소비 시작
    await request_queue.consume(process_message)

    print("Listening on request_queue...")
    yield

    # 애플리케이션 종료 시 연결 정리
    await connection.close()
    print("Connection to RabbitMQ closed.")


def calc_multiple_stress_index(hr_data: list[float], walking_time: int):
    stress_arr = get_multiple_stress_index(hr_data)
    if stress_arr is None:
        raise CalculateFailedException()
    healing_stress_avg, start_idx, end_idx = find_healing_course_idx(
        stress_arr) if walking_time >= 300 else (0.0, 0, 0)
    response = StressOverview(
        max_stress=max(stress_arr),
        min_stress=min(stress_arr),
        stress_indices=stress_arr,
        healing_stress_avg=healing_stress_avg,
        start_idx=start_idx,
        end_idx=end_idx
    )
    return response


app = FastAPI(lifespan=lifespan)
