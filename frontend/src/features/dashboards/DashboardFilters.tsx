import type { DashboardFilters as DashboardFilterState } from "../../app/types";

type Props = {
  value: DashboardFilterState;
  refreshing: boolean;
  cacheStatus?: string;
  refreshedAt?: string;
  onChange: (next: DashboardFilterState) => void;
  onRefresh: () => void;
};

export function DashboardFilters({ value, refreshing, cacheStatus, refreshedAt, onChange, onRefresh }: Props) {
  return <section className="dashboard-toolbar" aria-label="大屏筛选和刷新">
    <div className="dashboard-filters">
      <label>工厂<select value={value.factory} onChange={(event) => onChange({ ...value, factory: event.target.value })}><option value="">全部工厂</option><option value="成都工厂">成都工厂</option><option value="苏州工厂">苏州工厂</option><option value="深圳工厂">深圳工厂</option></select></label>
      <label>产品线<select value={value.productLine} onChange={(event) => onChange({ ...value, productLine: event.target.value })}><option value="">全部产品线</option><option value="控制器">控制器</option><option value="动力总成">动力总成</option><option value="结构件">结构件</option></select></label>
      <label>时间范围<select value={value.period} onChange={(event) => onChange({ ...value, period: event.target.value as DashboardFilterState["period"] })}><option value="7d">近 7 天</option><option value="30d">近 30 天</option><option value="90d">近 90 天</option></select></label>
    </div>
    <div className="dashboard-refresh-state"><span>{cacheStatus === "redis" ? "缓存命中" : cacheStatus === "queued" ? "刷新排队中" : "数据已同步"}</span><small>{refreshedAt ? new Date(refreshedAt).toLocaleString("zh-CN") : "尚未刷新"}</small><button className="secondary-button" onClick={onRefresh} disabled={refreshing}>{refreshing ? "刷新中..." : "刷新大屏"}</button></div>
  </section>;
}
