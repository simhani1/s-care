import json
import os
from contextlib import asynccontextmanager

from aio_pika import connect_robust, IncomingMessage, Message
from fastapi import FastAPI

from services.stress_overview_service import build_stress_overview

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
            result = build_stress_overview(heart_rates, walking_time)

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


app = FastAPI(lifespan=lifespan)
