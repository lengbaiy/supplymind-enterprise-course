import { DataView } from "../../components/DataView";
import { DashboardConfigPanel } from "./DashboardConfigPanel";

type DashboardConfig = { dashboard_id: string; refresh_interval_seconds: number; visible_widgets: string[] };
export function DashboardConfigurationPage({ config, busy, onSave }: { config: DashboardConfig; busy: boolean; onSave: (seconds: number, widgets: string[]) => void }) {
  return <DataView kicker="DASHBOARD / GOVERNANCE" title="大屏配置" copy="组织管理员配置指标显隐与刷新策略。"><DashboardConfigPanel config={config} busy={busy} onSave={onSave} /></DataView>;
}
