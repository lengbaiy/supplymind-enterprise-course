import type { AnalysisResult } from "../../app/domain-types";
import type { SseEvent } from "../../services/sse";

export type AnalysisStage = { id: string; name: string; status: "pending" | "running" | "completed" | "failed"; detail?: string };
export type StreamActivity = { event: string; message: string };
export type StreamSnapshot = { runId?: string; stages: AnalysisStage[]; activity: StreamActivity[]; sqlDraft?: string; citationCount: number; rowCount?: number; chartReady: boolean; result: AnalysisResult | null; error?: string };

const labels: Record<string, string> = { router: "识别问题", rag: "检索口径", schema: "读取数据结构", sql_planner: "生成查询", sql_guard: "校验查询", query: "执行查询", insight: "整理结论", report: "生成报告" };
export const freshSnapshot = (): StreamSnapshot => ({ stages: Object.entries(labels).map(([id, name]) => ({ id, name, status: "pending" })), activity: [], citationCount: 0, chartReady: false, result: null });
const setStage = (snapshot: StreamSnapshot, id: string, status: AnalysisStage["status"], detail?: string) => ({ ...snapshot, stages: snapshot.stages.map((stage) => stage.id === id ? { ...stage, status, detail } : stage) });
const withActivity = (snapshot: StreamSnapshot, event: string, message: string): StreamSnapshot => ({ ...snapshot, activity: [...snapshot.activity, { event, message }].slice(-8) });

export function mergeAnalysisEvent(snapshot: StreamSnapshot, event: SseEvent): StreamSnapshot {
  const data = event.data;
  if (event.event === "queued") return withActivity({ ...snapshot, runId: String(data.run_id || snapshot.runId || "") || undefined }, "任务已创建", "已建立分析任务，正在读取可用资源");
  if (event.event === "step_started") { const step = String(data.step || ""); const detail = String(data.message || "处理中"); return withActivity(setStage(snapshot, step, "running", detail), labels[step] || "正在处理", detail); }
  if (event.event === "sql_draft" || event.event === "sql_repair") { const detail = event.event === "sql_repair" ? "正在修复查询" : "已生成查询草案"; return withActivity({ ...setStage(snapshot, "sql_planner", event.event === "sql_repair" ? "running" : "completed", detail), sqlDraft: String(data.sql || "") || snapshot.sqlDraft }, "查询规划", detail); }
  if (event.event === "tool_result" && data.tool === "knowledge.search") { const detail = `找到 ${Number(data.result_count || 0)} 条引用`; return withActivity({ ...setStage(snapshot, "rag", "completed", detail), citationCount: Number(data.result_count || 0) }, "知识检索", detail); }
  if (event.event === "tool_result" && data.tool === "sql.query") { const detail = `返回 ${Number(data.row_count || 0)} 行`; return withActivity({ ...setStage(snapshot, "query", "completed", detail), rowCount: Number(data.row_count || 0) }, "只读查询", detail); }
  if (event.event === "chart_ready") return withActivity({ ...setStage(snapshot, "insight", "completed", "图表已就绪"), chartReady: true }, "结果整理", "关键图表已就绪");
  if (event.event === "completed") return withActivity({ ...snapshot, runId: String(data.run_id || snapshot.runId || "") || undefined, stages: snapshot.stages.map((stage) => ({ ...stage, status: "completed", detail: stage.detail || "已完成" })), result: { run_id: String(data.run_id || "") || undefined, sql: typeof data.sql === "string" ? data.sql : undefined, result: data.result as AnalysisResult["result"], report_id: typeof data.report_id === "string" ? data.report_id : undefined } }, "分析完成", "业务结论与证据已生成");
  if (event.event === "failed" || event.event === "cancelled") { const message = String(data.message || (event.event === "cancelled" ? "分析已取消" : "分析失败")); return withActivity({ ...snapshot, error: message, stages: snapshot.stages.map((stage) => stage.status === "running" ? { ...stage, status: "failed", detail: message } : stage) }, event.event === "cancelled" ? "分析已取消" : "分析失败", message); }
  return snapshot;
}
