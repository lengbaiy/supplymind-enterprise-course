from app.models import AnalysisRun
from app.services.reports import render_markdown, render_pdf


def test_render_markdown_contains_sql_rows_and_citations() -> None:
    run = AnalysisRun(
        id="run-1",
        tenant_id="tenant-1",
        conversation_id="conversation-1",
        data_source_id="source-1",
        question="生产达成率是多少？",
        sql="SELECT rate FROM production_orders",
        result={
            "insight": "达成率为 91.4%。",
            "rows": [{"factory": "成都", "rate": 91.4}],
            "citations": [{"document_name": "metrics.md", "location": {"start": 0, "end": 22}}],
        },
    )
    markdown, citations = render_markdown(run, "月度生产报告")
    assert markdown.startswith("# 月度生产报告")
    assert "SELECT rate" in markdown
    assert "| 成都 | 91.4 |" in markdown
    assert citations[0]["document_name"] == "metrics.md"


def test_render_pdf_creates_pdf(tmp_path) -> None:
    destination = tmp_path / "report.pdf"
    render_pdf("# 月度报告\n\n## 结论\n\n完成", str(destination))
    assert destination.read_bytes().startswith(b"%PDF")
