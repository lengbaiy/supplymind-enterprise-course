export type SourceRow = { id: string; name: string; engine: string; host: string; port: number; database_name: string; allowed_tables: string[]; status?: string };
type Props = { sources: SourceRow[]; onOpen: (id: string) => void; onTest: (id: string) => void; onSync: (id: string) => void; onToggle: (id: string) => void };
export function SourceList({ sources, onOpen, onTest, onSync, onToggle }: Props) {
  return <section className="source-list list-scroll">{sources.length ? sources.map((source) => {
    const disabled = source.status === "disabled";
    const label = disabled ? "已停用" : source.status === "failed" ? "连接异常" : source.status === "syncing" ? "同步中" : "已启用";
    return <article className="list-row datasource-row" key={source.id}><button className="row-main-button" onClick={() => onOpen(source.id)}><strong>{source.name}</strong><p>{source.engine} · {source.host}:{source.port} · {source.database_name}</p></button><span className={`status-chip ${disabled || source.status === "failed" ? "muted" : ""}`}>{label} · {source.allowed_tables.length} 张表</span><div className="row-actions"><button className="secondary-button" onClick={() => onTest(source.id)} disabled={disabled || source.status === "syncing"}>测试连接</button><button className="secondary-button" onClick={() => onSync(source.id)} disabled={disabled || source.status === "syncing"}>同步 Schema</button><button className="text-button" onClick={() => onToggle(source.id)}>{disabled ? "启用" : "停用"}</button></div></article>;
  }) : <p className="detail-hint">还没有数据源，请由组织管理员接入只读数据库。</p>}</section>;
}
