from app.models import AnalysisRun


def render_markdown(run: AnalysisRun, title: str | None = None) -> tuple[str, list]:
    result = run.result or {}
    insight = result.get("insight") or "分析任务已完成，暂无结构化洞察。"
    rows = result.get("rows") or []
    citations = result.get("citations") or []
    heading = title or f"供应链分析报告 · {run.question[:80]}"
    lines = [f"# {heading}", "", f"**问题**：{run.question}", "", "## 结论", "", insight, ""]
    if run.sql:
        lines.extend(["## 受限 SQL", "", "```sql", run.sql, "```", ""])
    if rows:
        lines.extend(["## 数据结果", ""])
        columns = list(rows[0].keys())
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        lines.extend("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in rows[:50])
        lines.append("")
    if citations:
        lines.extend(["## 依据", ""])
        lines.extend(f"- {item.get('document_name', '文档')} · {item.get('location', {})}" for item in citations)
    return "\n".join(lines).strip() + "\n", citations
