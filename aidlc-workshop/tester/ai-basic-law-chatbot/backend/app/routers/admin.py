import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.law import ParseLawResponse
from app.services.law_parser_service import LawParserService
from app.services.openai_service import OpenAIService
from app.services.embedding_service import EmbeddingService
from app.services.guideline_service import GuidelineService
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])


def verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not x_admin_key or x_admin_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=401,
            detail={"detail": "인증 실패: 유효하지 않은 관리자 키입니다.", "error_code": "UNAUTHORIZED"},
        )


@router.post(
    "/parse-law",
    response_model=ParseLawResponse,
    summary="AI 기본법 파싱 및 DB 초기화",
    description="""
프로젝트 루트의 AI 기본법 원문 PDF를 파싱하여 SQLite DB에 저장합니다.

**인증 필요**: 요청 헤더에 `X-Admin-Key` 값을 포함해야 합니다.

- 기존 데이터를 전체 삭제 후 새 데이터로 교체합니다.
- 파싱 실패 시 트랜잭션이 롤백되어 DB가 부분 업데이트되지 않습니다.
""",
    responses={
        200: {"description": "파싱 및 저장 성공"},
        401: {"description": "X-Admin-Key 없음 또는 불일치"},
        500: {"description": "파싱 오류 또는 DB 저장 실패"},
    },
)
async def parse_law(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    parser = LawParserService(OpenAIService())
    try:
        text = parser.extract_text_from_pdf(settings.law_pdf_path)
        chunks = parser.split_into_chunks(text)
        total = len(chunks)

        articles_data = []
        for i, chunk in enumerate(chunks, 1):
            try:
                logger.info("[파싱] %d/%d 조항 처리 중...", i, total)
                parsed = await parser.parse_chunk_with_gpt(chunk)
                articles_data.append(parsed)
            except Exception as e:
                logger.warning("[파싱] %d/%d 조항 실패 (스킵): %s", i, total, e)

        stats = parser.validate_and_save(db, articles_data)
        logger.info("[파싱] 완료 - 조 %d개, 항 %d개, 호 %d개, 목 %d개",
                    stats["articles"], stats["paragraphs"],
                    stats["subparagraphs"], stats["items"])

        return ParseLawResponse(
            status="success",
            message="AI 기본법 파싱 및 저장 완료",
            stats=stats,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Law parsing error: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"detail": f"파싱 오류: {str(e)}", "error_code": "PARSE_ERROR"},
        )


@router.post(
    "/embed-law",
    summary="AI 기본법 임베딩 생성",
    description="""
파싱된 AI 기본법 조항을 OpenAI text-embedding-3-small 모델로 임베딩하여 SQLite에 저장합니다.

**`POST /admin/parse-law` 실행 후 호출해야 합니다.**

**인증 필요**: 요청 헤더에 `X-Admin-Key` 값을 포함해야 합니다.
""",
    responses={
        200: {"description": "임베딩 생성 성공"},
        401: {"description": "X-Admin-Key 없음 또는 불일치"},
        500: {"description": "임베딩 생성 실패"},
    },
)
async def embed_law(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    try:
        emb_service = EmbeddingService()
        logger.info("[임베딩] 시작")
        stats = await emb_service.embed_all_articles(db)
        logger.info("[임베딩] 완료 - 성공 %d개, 실패 %d개", stats["embedded"], stats["failed"])
        return {
            "status": "success",
            "message": "AI 기본법 임베딩 생성 완료",
            "stats": stats,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("임베딩 생성 오류: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"detail": f"임베딩 생성 오류: {str(e)}", "error_code": "EMBED_ERROR"},
        )


@router.post(
    "/embed-guideline",
    summary="AI 가이드라인 임베딩 생성",
    description="""
`data/guidelines/` 폴더의 PDF 가이드라인 파일들을 페이지 단위로 청크화하여 임베딩 저장합니다.

**인증 필요**: 요청 헤더에 `X-Admin-Key` 값을 포함해야 합니다.
""",
    responses={
        200: {"description": "임베딩 생성 성공"},
        401: {"description": "X-Admin-Key 없음 또는 불일치"},
        500: {"description": "임베딩 생성 실패"},
    },
)
async def embed_guideline(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    import os
    from pathlib import Path
    # law_pdf_path 기준으로 guidelines 폴더 경로 계산
    law_pdf_abs = Path(settings.law_pdf_path)
    if not law_pdf_abs.is_absolute():
        law_pdf_abs = Path.cwd() / law_pdf_abs
    guideline_dir = str(law_pdf_abs.parent / "guidelines")

    if not os.path.exists(guideline_dir):
        raise HTTPException(
            status_code=400,
            detail={"detail": f"가이드라인 디렉토리가 없습니다: {guideline_dir}",
                    "error_code": "DIR_NOT_FOUND"},
        )
    try:
        svc = GuidelineService()
        stats = await svc.embed_all_guidelines(db, guideline_dir)
        return {
            "status": "success",
            "message": "가이드라인 임베딩 생성 완료",
            "stats": stats,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("가이드라인 임베딩 오류: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"detail": f"가이드라인 임베딩 오류: {str(e)}",
                    "error_code": "GUIDELINE_EMBED_ERROR"},
        )


@router.post(
    "/embed-guideline-ocr",
    summary="스캔본 가이드라인 OCR 임베딩",
    description="""
텍스트 추출이 불가능한 스캔본 PDF를 GPT-4o Vision으로 OCR하여 임베딩 저장합니다.

**요청 본문**: `{"filename": "파일명.pdf"}` - data/guidelines/ 폴더 내 파일명

**인증 필요**: 요청 헤더에 `X-Admin-Key` 값을 포함해야 합니다.

⚠️ GPT-4o Vision 사용으로 페이지당 약 $0.003 비용 발생
""",
    responses={
        200: {"description": "OCR 임베딩 성공"},
        400: {"description": "파일 없음"},
        401: {"description": "X-Admin-Key 없음 또는 불일치"},
        500: {"description": "OCR 실패"},
    },
)
async def embed_guideline_ocr(
    body: dict,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    from pathlib import Path
    filename = body.get("filename")
    if not filename:
        raise HTTPException(status_code=400,
                            detail={"detail": "filename 필드가 필요합니다."})

    law_pdf_abs = Path(settings.law_pdf_path)
    if not law_pdf_abs.is_absolute():
        law_pdf_abs = Path.cwd() / law_pdf_abs
    pdf_path = law_pdf_abs.parent / "guidelines" / filename

    if not pdf_path.exists():
        raise HTTPException(status_code=400,
                            detail={"detail": f"파일을 찾을 수 없습니다: {filename}"})
    try:
        svc = OCRService()
        stats = await svc.embed_scanned_pdf(db, str(pdf_path))
        return {
            "status": "success",
            "message": "OCR 임베딩 완료",
            "stats": stats,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("OCR 임베딩 오류: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"detail": f"OCR 오류: {str(e)}", "error_code": "OCR_ERROR"},
        )


@router.post(
    "/tag-guidelines",
    summary="가이드라인 법령 조항 자동 태깅",
    description="""
저장된 가이드라인 청크를 GPT-4o mini로 분석하여 관련 AI 기본법 조항 번호를 자동 태깅합니다.

**`POST /admin/embed-guideline` 실행 후 호출해야 합니다.**

**인증 필요**: 요청 헤더에 `X-Admin-Key` 값을 포함해야 합니다.
""",
)
async def tag_guidelines(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    try:
        svc = GuidelineService()
        stats = await svc.tag_all_chunks(db)
        return {
            "status": "success",
            "message": "가이드라인 태깅 완료",
            "stats": stats,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("태깅 오류: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"detail": f"태깅 오류: {str(e)}", "error_code": "TAG_ERROR"},
        )


@router.get(
    "/logs",
    summary="대화 로그 목록 조회",
    description="저장된 대화 세션 목록을 최신순으로 반환합니다. X-Admin-Key 인증 필요.",
)
def get_logs(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    from app.models.log import ConversationLog
    logs = db.query(ConversationLog).order_by(
        ConversationLog.created_at.desc()
    ).all()
    return [
        {
            "id": log.id,
            "session_id": log.session_id,
            "first_question": log.first_question,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.get(
    "/logs/{session_id}",
    summary="특정 세션 대화 내역 조회",
    description="특정 세션의 전체 대화 내역을 반환합니다. X-Admin-Key 인증 필요.",
)
def get_log_detail(
    session_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    import json as _json
    from app.models.log import ConversationLog
    log = db.query(ConversationLog).filter(
        ConversationLog.session_id == session_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail={"detail": "세션을 찾을 수 없습니다."})
    return {
        "session_id": log.session_id,
        "first_question": log.first_question,
        "created_at": log.created_at,
        "messages": _json.loads(log.messages),
    }


@router.delete(
    "/logs/{session_id}",
    summary="대화 로그 삭제",
    description="특정 세션의 대화 로그를 삭제합니다. X-Admin-Key 인증 필요.",
)
def delete_log(
    session_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    from app.models.log import ConversationLog
    log = db.query(ConversationLog).filter(
        ConversationLog.session_id == session_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail={"detail": "세션을 찾을 수 없습니다."})
    db.delete(log)
    db.commit()
    logger.info("로그 삭제 완료: session_id=%s", session_id)
    return {"status": "ok"}
