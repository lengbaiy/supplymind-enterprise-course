from app.models import AnalysisRun


def render_pdf(markdown: str, destination: str) -> None:
    """Render a readable, dependency-light PDF from report markdown."""
    from xml.sax.saxutils import escape

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    # The TrueType WenQuanYi CJK face is embedded in the PDF. Browser PDF
    # viewers cannot reliably render unembedded CID fallback fonts.
    font_name = "SupplyMindCJK"
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name
    story = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4 * mm))
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), styles["Heading2"]))
        elif line.startswith("- "):
            story.append(Paragraph("&#8226; " + escape(line[2:]), styles["BodyText"]))
        else:
            story.append(Paragraph(escape(line.replace("**", "")), styles["BodyText"]))
    SimpleDocTemplate(
        destination,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    ).build(story)


def render_markdown(run: AnalysisRun, title: str | None = None) -> tuple[str, list]:
    result = run.result or {}
    insight = result.get("insight") or "分析任务已完成，暂无结构化洞察。"
    insights = result.get("insights") or {}
    rows = result.get("rows") or []
    citations = result.get("citations") or []
    heading = title or f"供应链分析报告 · {run.question[:80]}"
    lines = [f"# {heading}", "", f"**问题**：{run.question}", "", "## 结论", "", insight, ""]
    for label, key in (("事实", "facts"), ("风险", "risks"), ("建议", "recommendations")):
        values = insights.get(key) or []
        if values:
            lines.extend([f"## {label}", ""])
            lines.extend(f"- {value}" for value in values)
            lines.append("")
    if run.sql:
        lines.extend(["## 受限 SQL", "", "```sql", run.sql, "```", ""])
    if rows:
        lines.extend(["## 数据结果", ""])
        columns = list(rows[0].keys())
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        lines.extend(
            "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
            for row in rows[:50]
        )
        lines.append("")
    if citations:
        lines.extend(["## 依据", ""])
        lines.extend(
            f"- {item.get('document_name', '文档')} · {item.get('location', {})}"
            for item in citations
        )
    return "\n".join(lines).strip() + "\n", citations
