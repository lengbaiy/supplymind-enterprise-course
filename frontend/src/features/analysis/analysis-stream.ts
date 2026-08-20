import type { AnalysisResult } from "../../app/domain-types";
import type { SseEvent } from "../../services/sse";

export type AnalysisStage = { id: string; name: string; status: "pending" | "running" | "completed" | "failed"; detail?: string };
export type StreamSnapshot = { runId?: string; stages: AnalysisStage[]; sqlDraft?: string; citationCount: number; rowCount?: number; chartReady: boolean; result: AnalysisResult | null; error?: string };

const labels: Record<string, string> = { router: "识别问题", rag: "检索口径", schema: "读取数据结构", sql_planner: "生成查询", sql_guard: "校验查询", query: "执行查询", insight: "整理结论", report: "生成报告" };
export const freshSnapshot = (): StreamSnapshot => ({ stages: Object.entries(labels).map(([id, name]) => ({ id, name, status: "pending" })), citationCount: 0, chartReady: false, result: null });
const setStage = (snapshot: StreamSnapshot, id: string, status: AnalysisStage["status"], detail?: string) => ({ ...snapshot, stages: snapshot.stages.map((stage) => stage.id === id ? { ...stage, status, detail } : stage) });

export function mergeAnalysisEvent(snapshot: StreamSnapshot, event: SseEvent): StreamSnapshot {
  const data = event.data;
  if (event.event === "queued") return { ...snapshot, runId: String(data.run_id || snapshot.runId || "") || undefined };
  if (event.event === "step_started") return setStage(snapshot, String(data.step || ""), "running", String(data.message || "处理中"));
  if (event.event === "sql_draft" || event.event === "sql_repair") return { ...setStage(snapshot, "sql_planner", event.event === "sql_repair" ? "running" : "completed", event.event === "sql_repair" ? "正在修复查询" : "已生成查询草案"), sqlDraft: String(data.sql || "") || snapshot.sqlDraft };
  if (event.event === "tool_result" && data.tool === "knowledge.search") return { ...setStage(snapshot, "rag", "completed", `找到 ${Number(data.result_count || 0)} 条引用`), citationCount: Number(data.result_count || 0) };
  if (event.event === "tool_result" && data.tool === "sql.query") return { ...setStage(snapshot, "query", "completed", `返回 ${Number(data.row_count || 0)} 行`), rowCount: Number(data.row_count || 0) };
  if (event.event === "chart_ready") return { ...setStage(snapshot, "insight", "completed", "图表已就绪"), chartReady: true };
  if (event.event === "completed") return { ...snapshot, runId: String(data.run_id || snapshot.runId || "") || undefined, stages: snapshot.stages.map((stage) => ({ ...stage, status: "completed" })), result: { run_id: String(data.run_id || "") || undefined, sql: typeof data.sql === "string" ? data.sql : undefined, result: data.result as AnalysisResult["result"], report_id: typeof data.report_id === "string" ? data.report_id : undefined } };
  if (event.event === "failed" || event.event === "cancelled") { const message = String(data.message || (event.event === "cancelled" ? "分析已取消" : "分析失败")); return { ...snapshot, error: message, stages: snapshot.stages.map((stage) => stage.status === "running" ? { ...stage, status: "failed", detail: message } : stage) }; }
  return snapshot;
}
