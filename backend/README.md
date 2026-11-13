## 백엔드

### 로컬 실행

인프라(MySQL, RabbitMQ, Redis)는 docker-compose 로 띄우고, 애플리케이션은 호스트에서 직접 실행한다.

```bash
# 1. 인프라
cd backend
docker compose up -d --wait

# 2. Spring API (JDK 21)
cd api
cp .env.example .env
sh gradlew bootRun

# 3. 스트레스 계산 워커 (Python 3.12)
cd ../fast-api
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8000
```

- RabbitMQ 관리 콘솔: http://localhost:15672 (scare / scare)
- Swagger: http://localhost:8080/swagger-ui
- `.env.example` 의 값은 로컬 전용이다. 운영 접속 정보는 커밋하지 않는다.
