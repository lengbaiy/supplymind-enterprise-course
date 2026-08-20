export type ExportItem = { id: string; format: string; status: string; error_message?: string; created_at: string };
export function ReportExportStatus({ items, reportId, onRetry }: { items: ExportItem[]; reportId: string; onRetry: (reportId: string, exportId: string) => void }) {
  return <section><h4>导出历史</h4>{items.length ? items.map((item) => <div className="export-row" key={item.id}><span>{item.format.toUpperCase()}</span><span>{item.status}</span>{item.error_message && <small className="export-error">{item.error_message}</small>}{item.status === "failed" && <button className="text-button" onClick={() => onRetry(reportId, item.id)}>重试</button>}<time>{new Date(item.created_at).toLocaleString("zh-CN")}</time></div>) : <p className="detail-hint">尚未创建导出任务。</p>}</section>;
}
