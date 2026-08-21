import { lazy, Suspense, type ComponentType } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { NAV_ITEMS, type NavItem } from "./navigation";

const LegacyConsole = lazy(() =>
  import("../features/legacy/LegacyConsole").then((module) => ({ default: module.LegacyConsole })),
);
const AnalysisRoute = lazy(() =>
  import("../features/analysis/AnalysisRoute").then((module) => ({ default: module.AnalysisRoute })),
);
const DataSourcesRoute = lazy(() =>
  import("../features/datasources/DataSourcesRoute").then((module) => ({ default: module.DataSourcesRoute })),
);
const OperationsOverviewRoute = lazy(() =>
  import("../features/dashboards/OperationsOverviewRoute").then((module) => ({ default: module.OperationsOverviewRoute })),
);
const ReportsRoute = lazy(() =>
  import("../features/reports/ReportsRoute").then((module) => ({ default: module.ReportsRoute })),
);
const SystemStatusRoute = lazy(() =>
  import("../features/system/SystemStatusRoute").then((module) => ({ default: module.SystemStatusRoute })),
);
const DashboardConfigurationRoute = lazy(() =>
  import("../features/dashboards/DashboardConfigurationRoute").then((module) => ({ default: module.DashboardConfigurationRoute })),
);
const ProjectManagementRoute = lazy(() =>
  import("../features/projects/ProjectManagementRoute").then((module) => ({ default: module.ProjectManagementRoute })),
);
const PlatformOrganizationsRoute = lazy(() =>
  import("../features/system/PlatformOrganizationsRoute").then((module) => ({ default: module.PlatformOrganizationsRoute })),
);

export const NAV_PATHS: Record<NavItem, string> = {
  "运营总览": "/overview",
  "项目管理": "/project",
  "企业管理": "/platform/organizations",
  "大屏配置": "/dashboard/configuration",
  "分析会话": "/analysis",
  "数据源": "/data-sources",
  "知识库": "/knowledge",
  "报告中心": "/reports",
  "组织与审计": "/audit",
  "系统状态": "/system-status",
};

function legacyRoute(item: NavItem): ComponentType {
  return () => <Suspense fallback={<RouteLoading />}><LegacyConsole initialNav={item} /></Suspense>;
}

function RouteLoading() {
  return <main className="route-loading" role="status">正在加载工作区…</main>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to={NAV_PATHS["运营总览"]} replace />} />
      <Route path="/analysis" element={<Suspense fallback={<RouteLoading />}><AnalysisRoute /></Suspense>} />
      <Route path="/data-sources" element={<Suspense fallback={<RouteLoading />}><DataSourcesRoute /></Suspense>} />
      <Route path="/overview" element={<Suspense fallback={<RouteLoading />}><OperationsOverviewRoute /></Suspense>} />
      <Route path="/reports" element={<Suspense fallback={<RouteLoading />}><ReportsRoute /></Suspense>} />
      <Route path="/system-status" element={<Suspense fallback={<RouteLoading />}><SystemStatusRoute /></Suspense>} />
      <Route path="/dashboard/configuration" element={<Suspense fallback={<RouteLoading />}><DashboardConfigurationRoute /></Suspense>} />
      <Route path="/project" element={<Suspense fallback={<RouteLoading />}><ProjectManagementRoute /></Suspense>} />
      <Route path="/platform/organizations" element={<Suspense fallback={<RouteLoading />}><PlatformOrganizationsRoute /></Suspense>} />
      {NAV_ITEMS.map((item) => {
        if (item === "运营总览" || item === "项目管理" || item === "企业管理" || item === "分析会话" || item === "数据源" || item === "报告中心" || item === "系统状态" || item === "大屏配置") return null;
        const Page = legacyRoute(item);
        return <Route key={item} path={NAV_PATHS[item]} element={<Page />} />;
      })}
      <Route path="*" element={<Navigate to={NAV_PATHS["运营总览"]} replace />} />
    </Routes>
  );
}
