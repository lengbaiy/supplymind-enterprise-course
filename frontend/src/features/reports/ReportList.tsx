export type ReportRow = { id: string; title: string; status: string; created_at: string };
export function ReportList({ reports, onOpen, onDownload }: { reports: ReportRow[]; onOpen: (id: string) => void; onDownload: (id: string) => void }) {
  return reports.length ? <>{reports.map((report) => <article className="list-row" key={report.id}><button className="row-main-button" onClick={() => onOpen(report.id)}><strong>{report.title}</strong><p>{new Date(report.created_at).toLocaleString("zh-CN")} · {report.status}</p></button><button className="secondary-button" onClick={() => onDownload(report.id)}>下载 PDF</button></article>)}</> : <p className="detail-hint">还没有报告，请从分析会话发起问题。</p>;
}
