import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.config import settings
from app.schemas.chat import ExportRequest

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class PDFExportService:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        self.font_dir = os.path.abspath(settings.font_dir)

    def generate_pdf(self, request: ExportRequest) -> bytes:
        """대화 내역을 PDF로 변환하여 바이너리 반환."""
        # 마지막 assistant 메시지에서 compliance_data 추출
        compliance_data = None
        for msg in reversed(request.messages):
            if msg.role == "assistant" and msg.compliance_data:
                compliance_data = msg.compliance_data
                break

        overall = compliance_data.overall if compliance_data else "N/A"
        items = compliance_data.items if compliance_data else []

        # 우선순위 순 정렬: 높음 > 중간 > 낮음
        priority_order = {"높음": 0, "중간": 1, "낮음": 2}
        sorted_items = sorted(items, key=lambda x: priority_order.get(x.priority, 9))

        template = self.env.get_template("export_report.html")
        html_content = template.render(
            analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            project_summary=request.project_summary,
            overall=overall,
            items=sorted_items,
            font_dir=self.font_dir,
        )

        try:
            from weasyprint import HTML
        except ImportError as e:
            raise RuntimeError(
                "weasyprint가 설치되지 않았습니다. "
                "Windows에서는 GTK 런타임 설치 후 pip install weasyprint 를 실행하세요."
            ) from e

        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
