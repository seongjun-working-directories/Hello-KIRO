"""
Feature: ai-basic-law-chatbot, Property 5: PDF 내용 완전성
Validates: Requirements 5.2, 5.3
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.services.pdf_export_service import PDFExportService
from app.schemas.chat import ExportRequest, ChatMessage, ComplianceData, ComplianceItem


def make_export_request(project_summary: str = "테스트 프로젝트") -> ExportRequest:
    compliance = ComplianceData(
        overall="Partially Compliant",
        items=[
            ComplianceItem(
                article_no="제22조",
                title="고위험 AI 시스템",
                status="Non-Compliant",
                priority="높음",
                recommendation="생체정보 처리 동의 절차 필요",
                article_summary="고위험 AI 시스템에 대한 요건",
            )
        ],
    )
    messages = [
        ChatMessage(
            role="user",
            content="얼굴 인식 시스템을 개발하려고 합니다.",
            timestamp=datetime.now(timezone.utc),
        ),
        ChatMessage(
            role="assistant",
            content="분석 결과입니다.",
            timestamp=datetime.now(timezone.utc),
            compliance_data=compliance,
        ),
    ]
    return ExportRequest(
        session_id="test-session",
        messages=messages,
        project_summary=project_summary,
    )


def test_pdf_contains_required_sections():
    """생성된 PDF HTML에 필수 항목이 포함되어야 한다."""
    service = PDFExportService()

    # WeasyPrint 실제 호출 대신 HTML 렌더링만 검증
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    template_dir = Path(__file__).parent.parent / "app" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("export_report.html")

    request = make_export_request("얼굴 인식 출입 통제 시스템")
    compliance = request.messages[-1].compliance_data

    html = template.render(
        analyzed_at="2025-01-15 10:30:00 UTC",
        project_summary=request.project_summary,
        overall=compliance.overall,
        items=compliance.items,
        font_dir="/fake/fonts",
    )

    assert "얼굴 인식 출입 통제 시스템" in html  # 프로젝트 요약
    assert "Partially Compliant" in html           # 준수 등급
    assert "제22조" in html                         # 조항 번호
    assert "생체정보 처리 동의 절차 필요" in html   # 개선 권고사항
    assert "본 결과는 참고용이며" in html            # 면책 조항
    assert "2025-01-15 10:30:00 UTC" in html        # 분석 일시
