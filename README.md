
# 🚚 S-Care

<div align='center'>
    <img src='https://github.com/user-attachments/assets/1669732b-f465-4727-b02a-d9bb2174f361' />
</div>

## ✨ 주제

-   일상 속 스트레스 관리를 함께 해주는 서비스

## 📅 기간

-   2024.10.21 ~ 2024.11.19

## 📜 주요 기능

### 스트레스 시각화 및 알림

- 나를 투영한 펫이 스트레스 수치에 맞춰서 표정 변화

### 산책 유도 & 지압 유도 알림

- 스트레스가 **나쁨** 구간에 해당되면 기상청 API를 호출하여 날씨 정보를 조회
- 온도, 습도, 눈/비, 풍속의 상황에 맞춰서 산책 or 지압 중 하나를 사용자에게 제안하는 알림 전송

### 개인별 통계

- 일주일 동안 S-Care의 솔루션을 사용했던 통계 결과를 조회하여 한눈에 파악

### 산책하기

- 실시간 위치로 산책 경로를 지도에 표시
- 산책을 3분 이상으로 할 경우, 코스 기록 저장 가능
- 산책을 5분 이상으로 할 경우, 산책 중 제일 스트레스가 낮았던 구간 기록 가능
- 스트레스 분석은 저장 후 비동기로 진행되며, 분석이 끝나기 전에는 결과 화면에 대기 문구 표시

## 💻 개발 환경 및 문서

### 1️⃣ Stacks

#### 🛠 Front-End 🛠

![Android](https://img.shields.io/badge/android-%2320232a.svg?style=for-the-badge&logo=android&logoColor=%#34A853)

#### 🛠 Back-End 🛠

![Java](https://img.shields.io/badge/java-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)
![SpringBoot](https://img.shields.io/badge/SpringBoot-%236DB33F.svg?style=for-the-badge&logo=SpringBoot&logoColor=white)
![SpringBoot](https://img.shields.io/badge/JPA-%236DB33F.svg?style=for-the-badge&logo=SpringBoot&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)

![MySQL](https://img.shields.io/badge/mysql-4479A1.svg?style=for-the-badge&logo=mysql&logoColor=white)
![QueryDSL](https://img.shields.io/badge/QueryDSL-black.svg?style=for-the-badge&logo=QueryDSL&logoColor=white)
![Python](https://img.shields.io/badge/python-4479A1.svg?style=for-the-badge&logo=python&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)

#### 🛠 CI / CD 🛠

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Jenkins](https://img.shields.io/badge/jenkins-%23D24939.svg?style=for-the-badge&logo=jenkins&logoColor=white)
![NGINX](https://img.shields.io/badge/NGINX-009639?style=for-the-badge&logo=nginx&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)

#### 🛠 Tools 🛠

![Git](https://img.shields.io/badge/git-%23F05033.svg?style=for-the-badge&logo=git&logoColor=white)
![GitLab](https://img.shields.io/badge/gitlab-%23181717.svg?style=for-the-badge&logo=gitlab&logoColor=white)
![Jira](https://img.shields.io/badge/jira-%230A0FFF.svg?style=for-the-badge&logo=jira&logoColor=white)
[![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white)](https://imminent-hamburger-1d8.notion.site/8-0-4-0fbd317ef9d840bc9d31ea8adfa50ceb)
[![Figma](https://img.shields.io/badge/Figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white)](https://www.figma.com/design/7WUqXjKvUcDPLKYMUa9P4Y/%EC%98%B7%EC%A7%B1?node-id=0-1&t=K68NqokoRcvm5jnd-0)

### 2️⃣ Architecture

<div align='center'>
  <img src='docs/images/architecture.png' width='800px' >
</div>

### 3️⃣ ERD

<div align='center'>
  <img src='https://github.com/user-attachments/assets/3315086c-b253-48c6-beec-0a4c7a5216db' width='600px' >
</div>

### 4️⃣ 로컬 실행

MySQL, RabbitMQ, Redis 는 docker compose 로 띄우고 Spring API 와 스트레스 계산 워커는 호스트에서 실행합니다. 자세한 방법은 [backend/README.md](backend/README.md) 에 있습니다.

```bash
cd backend && docker compose up -d --wait
cd api && cp .env.example .env && sh gradlew bootRun
cd ../fast-api && python -m venv .venv && .venv/bin/pip install -r requirements.txt
env $(cat .env.example | xargs) .venv/bin/uvicorn main:app --port 8000
```

## 🔧 산책 저장 흐름 고도화 (2026)

프로젝트 종료 후 이 포크에서 산책 저장과 스트레스 분석 흐름을 다시 설계했습니다. 요구사항과 결정 과정은 [docs/spec/walk-save-improvement.md](docs/spec/walk-save-improvement.md) 에 있습니다.

### 주요 작업

- **비동기 분석**: 산책은 분석 중 상태로 먼저 저장하고, 스트레스 분석은 RabbitMQ 를 거쳐 워커가 처리합니다.
- **Transactional Outbox**: 산책 코스, 좌표, 분석 요청 기록을 하나의 DB 트랜잭션으로 저장합니다. 10초 주기 스케줄러가 발행 대기 행을 읽어 발행하고, 브로커의 확인 응답을 받은 뒤에만 발행됨으로 표시합니다.
- **결과 저장 후 ACK**: 워커는 Spring Boot 의 결과 저장 API 에서 200 을 받은 뒤에만 메시지를 ACK 합니다. 실패하면 1초, 2초, 4초 간격으로 재시도한 뒤 데드레터 큐로 보냅니다.
- **멱등한 결과 저장**: 같은 메시지가 다시 전달되어도 조건부 UPDATE 로 한 번만 반영합니다.
- **워커 전용 API 보호**: 결과 저장 API 는 공유 비밀 헤더로 호출자를 확인하고, 결과 값과 좌표 인덱스의 범위를 검증합니다.
- **분석 방식 교체**: 누적 계산을 120 샘플 고정 윈도우로 바꾸고, 평균 스트레스가 가장 낮은 구간을 누적합으로 찾습니다.
- **저장소 통합**: 경로 좌표를 MongoDB 에서 MySQL JSON 컬럼으로 옮겨 산책과 한 트랜잭션으로 저장합니다.
- **분석 상태 표시**: 산책 조회 응답에 분석 상태를 포함하고, 앱은 분석이 끝나기 전에 대기 문구를 보여줍니다.

### 문서

| 문서 | 내용 |
| --- | --- |
| [docs/spec/walk-save-improvement.md](docs/spec/walk-save-improvement.md) | 요구사항, 목표 구조, 채택하지 않은 것과 이유 |
| [backend/fast-api/experiments/RESULTS.md](backend/fast-api/experiments/RESULTS.md) | 윈도우 크기 실험 |
| [backend/README.md](backend/README.md) | 로컬 실행 방법 |
