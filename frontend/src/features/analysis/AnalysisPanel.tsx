import { useEffect, useRef } from "react";
import type { FormEvent } from "react";
import { loadCharts } from "../../services/charts";

type AnalysisResult = { run_id?: string; trace_id?: string; sql?: string; sql_draft?: string; guard_error?: string; result?: { rows?: Record<string, unknown>[]; insight?: string; direct_answer?: string; insights?: { facts?: string[]; risks?: string[]; recommendations?: string[]; assumptions?: string[]; limitations?: string[] }; chart?: Record<string, unknown>; citations?: Record<string, unknown>[]; report_id?: string }; report_id?: string };
type Resource = { id: string; name: string };
type ConversationMessage = { role: "user" | "assistant"; content: string; created_at: string };
type Props = { question: string; setQuestion: (value: string) => void; events: string[]; result: AnalysisResult | null; messages?: ConversationMessage[]; loading: boolean; onSubmit: (event: FormEvent) => void; onDownloadReport: (id: string) => Promise<void>; sources?: Resource[]; knowledgeBases?: Resource[]; sourceId?: string; knowledgeBaseId?: string; setSourceId?: (value: string) => void; setKnowledgeBaseId?: (value: string) => void };

const templates = ["近 30 天各工厂生产达成率", "识别当前缺料风险和影响物料", "比较供应商交付及时率", "分析库存周转和呆滞风险", "统计质量合格率趋势", "分析订单履约情况"];

export function AnalysisPanel({ question, setQuestion, events, result, messages = [], loading, onSubmit, onDownloadReport, sources = [], knowledgeBases = [], sourceId = "", knowledgeBaseId = "", setSourceId = () => undefined, setKnowledgeBaseId = () => undefined }: Props) {
  const rows = result?.result?.rows || [];
  const citations = result?.result?.citations || [];
  const chartRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!chartRef.current || !result?.result?.chart || rows.length === 0) return;
    const spec = result.result.chart;
    const xField = String(spec.x || Object.keys(rows[0])[0] || "");
    const yField = String(spec.y || Object.keys(rows[0])[1] || "");
    if (!xField || !yField) return;
    let disposed = false;
    let chart: import("../../services/charts-runtime").ChartInstance | undefined;
    const resize = () => chart?.resize();
    window.addEventListener("resize", resize);
    void loadCharts().then((echarts) => {
      if (disposed || !chartRef.current) return;
      chart = echarts.init(chartRef.current);
      chart.setOption({ grid: { left: 12, right: 18, top: 18, bottom: 28, containLabel: true }, tooltip: { trigger: "axis", backgroundColor: "#14352c", borderWidth: 0, textStyle: { color: "#fff" } }, xAxis: { type: "category", data: rows.map((row) => String(row[xField] ?? "-")), axisLabel: { color: "#73847c", interval: 0, rotate: rows.length > 7 ? 25 : 0 } }, yAxis: { type: "value", axisLabel: { color: "#73847c" }, splitLine: { lineStyle: { color: "#edf2ef" } } }, series: [{ type: spec.type === "line" ? "line" : "bar", smooth: spec.type === "line", data: rows.map((row) => Number(row[yField] ?? 0)), itemStyle: { color: "#15966d" }, barMaxWidth: 34 }] });
    });
    return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); };
  }, [result, rows]);

  return <section className="analysis-workbench">
    <div className="analysis-header"><div><p className="section-kicker">ANALYSIS ASSISTANT</p><h3>供应链分析会话</h3><p>基于真实数据源和知识库连续追问，所有结论都附带可核验 SQL 与数据。</p></div><span className="live-indicator"><i />实时运行链路</span></div>
    {sources.length > 0 && <div className="analysis-resources"><label>数据源<select value={sourceId} onChange={(event) => setSourceId(event.target.value)} required><option value="">选择数据源</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label><label>知识库<select value={knowledgeBaseId} onChange={(event) => setKnowledgeBaseId(event.target.value)} required><option value="">选择知识库</option>{knowledgeBases.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>}
    <div className="analysis-templates" aria-label="问题模板">{templates.map((template) => <button type="button" className="text-button" key={template} onClick={() => setQuestion(template)}>{template}</button>)}</div>
    {messages.length > 0 && <div className="chat-transcript" aria-live="polite">{messages.map((message, index) => <article className={`chat-message ${message.role}`} key={`${message.created_at}-${index}`}><div className="chat-avatar" aria-hidden="true">{message.role === "user" ? "你" : "AI"}</div><div className="chat-bubble"><p>{message.content}</p><time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</time></div></article>)}</div>}
    <form onSubmit={onSubmit} className="analysis-composer"><label htmlFor="analysis-question">继续追问</label><div><input id="analysis-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：那只看低于 90% 的工厂" required /><button className="primary-button" disabled={loading || !sourceId || !knowledgeBaseId}>{loading ? "分析中…" : "发送问题"}<span aria-hidden="true">↗</span></button></div></form>
    {events.length > 0 && <details className="analysis-status-panel" open={loading}><summary>运行状态 <span>{loading ? "处理中" : "已完成"}</span></summary><div className="event-log" aria-live="polite">{events.slice(-12).map((event, index) => <p key={`${event}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span>{event}</p>)}</div></details>}
    {result && <section className="analysis-evidence" aria-label="分析结果"><div className="result-heading"><div><p className="section-kicker">最新分析结果</p><h3>{result.result?.direct_answer || result.result?.insight || "分析已完成"}</h3></div><span className="analysis-status">{loading ? "处理中" : "已完成"}</span></div><div className="detail-meta"><span>运行 ID：{result.run_id || "—"}</span><span>数据源：{sources.find((item) => item.id === sourceId)?.name || sourceId || "—"}</span><span>知识库：{knowledgeBases.find((item) => item.id === knowledgeBaseId)?.name || knowledgeBaseId || "—"}</span><span>Trace ID：{result.trace_id || "响应头未提供"}</span></div>{result.result?.insights && <div className="insight-grid">{([ ["事实", result.result.insights.facts], ["风险", result.result.insights.risks], ["建议", result.result.insights.recommendations], ["假设", result.result.insights.assumptions], ["限制", result.result.insights.limitations] ] as const).map(([label, values]) => <section className="insight-block" key={label}><strong>{label}</strong>{values?.length ? values.map((value, index) => <p key={index}>{value}</p>) : <p className="detail-hint">暂无</p>}</section>)}</div>}<div className="evidence-grid">{result.sql_draft && <details className="result-detail"><summary>SQL 草案</summary><pre className="sql-preview"><code>{result.sql_draft}</code></pre></details>}{result.sql && <details className="result-detail" open><summary>最终 SQL</summary><pre className="sql-preview"><code>{result.sql}</code></pre></details>}</div>{result.guard_error && <p className="form-error">SQL Guard：{result.guard_error}</p>}{result.result?.chart && rows.length > 0 && <div className="analysis-chart" ref={chartRef} aria-label="分析结果图表" />}{rows.length > 0 ? <div className="result-table-wrap"><table className="result-table"><thead><tr>{Object.keys(rows[0]).map((key) => <th key={key}>{key}</th>)}</tr></thead><tbody>{rows.slice(0, 50).map((row, index) => <tr key={index}>{Object.keys(rows[0]).map((key) => <td key={key}>{String(row[key] ?? "-")}</td>)}</tr>)}</tbody></table></div> : <p className="detail-hint">查询没有返回数据，因此不生成确定性图表或结论。</p>}{citations.length > 0 && <details className="result-detail" open><summary>引用依据（{citations.length}）</summary>{citations.map((citation, index) => <p key={index}>{String(citation.filename || citation.document_name || citation.document_id || "文档")} · {String(citation.location || citation.score || "已引用")}</p>)}</details>}{(result.report_id || result.result?.report_id) && <button className="secondary-button" onClick={() => void onDownloadReport(String(result.report_id || result.result?.report_id))}>下载 PDF 报告</button>}</section>}
  </section>;
}
