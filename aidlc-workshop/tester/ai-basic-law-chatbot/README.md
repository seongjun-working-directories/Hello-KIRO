# AI 기본법 준수 확인 챗봇

## 빠른 시작

### 백엔드

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY, ADMIN_SECRET_KEY 설정
uvicorn app.main:app --reload
```

### 프론트엔드

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

### 테스트

```bash
# 백엔드
cd backend
pytest

# 프론트엔드
cd frontend
npm test
```

### 법령 DB 초기화

```bash
curl -X POST http://localhost:8000/admin/parse-law \
  -H "X-Admin-Key: your-secret-key"
```
