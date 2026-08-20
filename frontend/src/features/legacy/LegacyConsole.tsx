import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, API_BASE } from "../../services/api";
import { parseSseEvents, readSseResponse } from "../../services/sse";
import { NAV_ITEMS, type NavItem } from "../../app/navigation";
import type { Dashboard, DashboardFilters } from "../../app/types";
import { canAccessNav } from "../../app/route-registry";
import { DataView } from "../../components/DataView";
import { Pagination } from "../../components/Pagination";
import { EmptyState as Empty } from "../../components/EmptyState";
import { AuthScreen } from "../auth/AuthScreen";
import { DashboardConfigurationPage } from "../dashboards/DashboardConfigurationPage";
import type { AuditEvent } from "../audit/AuditPanel";
import "../datasources/datasource.css";
import { SystemStatusPanel, type SystemStatusData } from "../system/SystemStatusPanel";
import { SourceList } from "../datasources/SourceList";
import { ReportsPage } from "../reports/ReportsPage";
import { AnalysisSessionPage } from "../analysis/AnalysisSessionPage";
import { OperationsOverviewPage } from "../dashboards/OperationsOverviewPage";
import { ProjectManagementPage } from "../projects/ProjectManagementPage";
import { DataSourcesPage } from "../datasources/DataSourcesPage";
import { DataSourceDetail } from "../datasources/DataSourceDetail";
import { KnowledgeBasePage } from "../knowledge/KnowledgeBasePage";
import { DocumentTaskList } from "../knowledge/DocumentTaskList";
import { OrganizationAuditPage } from "../identity/OrganizationAuditPage";
import type { PlatformOrganization } from "../system/OrganizationAdminPanel";
import { PlatformOrganizationsPage } from "../system/PlatformOrganizationsPage";
import { SystemStatusPage } from "../system/SystemStatusPage";
import { KnowledgeCard } from "../knowledge/KnowledgeCard";
import { AppShell } from "../../components/AppShell";
import type { Source, KnowledgeBase, Report, ReportExport, AnalysisRun, AgentStep, Member, Invitation, Document, KnowledgeDetail, Citation, DocumentSource, AnalysisResult, OrganizationSummary, OrganizationAccess, PermissionMatrix, SystemStatus, SchemaTable } from "../../app/domain-types";
import type { FormEvent } from "react";
import { loadCharts } from "../../services/charts";
import { getApiErrorMessage, getApiErrorState } from "../../services/api-errors";

const API = API_BASE;
const navItems = NAV_ITEMS;
const navPaths: Record<string, string> = {
  "运营总览": "/overview", "项目管理": "/project", "企业管理": "/platform/organizations", "大屏配置": "/dashboard/configuration", "分析会话": "/analysis", "数据源": "/data-sources", "知识库": "/knowledge", "报告中心": "/reports", "组织与审计": "/audit", "系统状态": "/system-status",
};

export function LegacyConsole({ initialNav = "运营总览" }: { initialNav?: string }) {
  const navigate = useNavigate();
  const [token, setToken] = useState(
    localStorage.getItem("supplymind_token") || "",
  );
  const [refresh, setRefresh] = useState(
    localStorage.getItem("supplymind_refresh") || "",
  );
  const [nav, setNav] = useState<string>(initialNav);
  const selectNav = (nextNav: string) => {
    setNav(nextNav);
    navigate(navPaths[nextNav] || "/overview");
  };
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashboardDimensions, setDashboardDimensions] = useState<{ factories: string[]; product_lines: string[]; suppliers: string[] }>({ factories: [], product_lines: [], suppliers: [] });
  const [dashboardConfig, setDashboardConfig] = useState<{ dashboard_id: string; refresh_interval_seconds: number; visible_widgets: string[] }>({ dashboard_id: "", refresh_interval_seconds: 300, visible_widgets: [] });
  const [sources, setSources] = useState<Source[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeBase[]>([]);
  const [knowledgeFilter, setKnowledgeFilter] = useState({ name: "", status: "" });
  const [knowledgePage, setKnowledgePage] = useState(1);
  const [knowledgePageSize, setKnowledgePageSize] = useState(10);
  const [knowledgeHasMore, setKnowledgeHasMore] = useState(false);
  const [platformOrganizations, setPlatformOrganizations] = useState<PlatformOrganization[]>([]);
  const [platformPage, setPlatformPage] = useState(1);
  const [reports, setReports] = useState<Report[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisRun[]>([]);
  const [analysisPage, setAnalysisPage] = useState(1);
  const [analysisPageSize, setAnalysisPageSize] = useState(10);
  const [analysisHasMore, setAnalysisHasMore] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisRun | null>(
    null,
  );
  const [analysisSteps, setAnalysisSteps] = useState<AgentStep[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [reportExports, setReportExports] = useState<ReportExport[]>([]);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [sourceSchema, setSourceSchema] = useState<{
    tables: SchemaTable[];
    table_count: number;
    created_at: string;
  } | null>(null);
  const [sourceSyncTasks, setSourceSyncTasks] = useState<{ id: string; status: string; started_at?: string; finished_at?: string; error_message?: string; celery_task_id?: string }[]>([]);
  const [selectedSchemaTable, setSelectedSchemaTable] = useState<SchemaTable | null>(null);
  const [allowlistDraft, setAllowlistDraft] = useState<string[]>([]);
  const [sourceQuery, setSourceQuery] = useState("SELECT * FROM production_work_orders LIMIT 20");
  const [sourceQueryResult, setSourceQueryResult] = useState<{ sql: string; tables: string[]; rows: Record<string, unknown>[]; row_count: number; max_rows: number; elapsed_ms: number; timed_out: boolean; redacted: boolean } | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [invitationLink, setInvitationLink] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [failedTasks, setFailedTasks] = useState<{ id: string; document_id: string; status: string; dead_letter?: boolean; attempts?: number; error_message?: string; created_at: string }[]>([]);
  const [selectedAudit, setSelectedAudit] = useState<AuditEvent | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedKnowledge, setSelectedKnowledge] =
    useState<KnowledgeDetail | null>(null);
  const [pendingKnowledgeDelete, setPendingKnowledgeDelete] =
    useState<KnowledgeDetail | null>(null);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeCitations, setKnowledgeCitations] = useState<Citation[]>([]);
  const [documentSource, setDocumentSource] = useState<DocumentSource | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null,
  );
  const [organization, setOrganization] = useState<OrganizationSummary | null>(
    null,
  );
  const [organizations, setOrganizations] = useState<OrganizationAccess[]>([]);
  const [permissions, setPermissions] = useState<PermissionMatrix | null>(null);
  const [quotaDraft, setQuotaDraft] = useState({
    max_concurrent_analyses: 4,
    daily_analysis_runs: 100,
    max_document_size_mb: 10,
    retention_days: 90,
  });
  const [auditFilter, setAuditFilter] = useState("");
  const [auditRunId, setAuditRunId] = useState("");
  const [reportFilter, setReportFilter] = useState({ title: "", status: "", createdBy: "", runId: "", createdFrom: "", createdTo: "" });
  const [refreshingDashboard, setRefreshingDashboard] = useState(false);
  const [dashboardFilters, setDashboardFilters] = useState<DashboardFilters>({
    factory: "",
    productLine: "",
    period: "30d",
  });
  const [profileOpen, setProfileOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const [question, setQuestion] = useState("近30天各工厂生产达成率与缺料风险");
  const [analysisSourceId, setAnalysisSourceId] = useState("");
  const [analysisKnowledgeBaseId, setAnalysisKnowledgeBaseId] = useState("");
  const [analysisConversationId, setAnalysisConversationId] = useState<string>(() => crypto.randomUUID());
  const [analysisMessages, setAnalysisMessages] = useState<{ role: "user" | "assistant"; content: string; created_at: string }[]>([]);
  const analysisContextLoadedRef = useRef("");
  const analysisContextStorageKey = organization?.id ? `supplymind_analysis_context_${organization.id}` : "";
  const [events, setEvents] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [accessError, setAccessError] = useState<"forbidden" | "not-found" | "expired" | "">("");
  const [systemStatus, setSystemStatus] = useState<"ready" | "degraded">(
    "ready",
  );
  const [systemDetails, setSystemDetails] = useState<SystemStatus | null>(null);
  const [loginError, setLoginError] = useState("");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginOrganization, setLoginOrganization] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginBusy, setLoginBusy] = useState(false);
  const [oidcBusy, setOidcBusy] = useState(false);
  const [inviteToken] = useState(() => new URLSearchParams(window.location.search).get("invite") || "");
  const [inviteError, setInviteError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sourceDraft, setSourceDraft] = useState({
    name: "",
    engine: "postgresql",
    host: "",
    port: "5432",
    database_name: "",
    username: "",
    password: "",
    allowed_tables: "",
    tls_required: true,
  });
  const canViewNav = (item: NavItem) => canAccessNav(item, organization?.role, permissions);
  const visibleNavItems = navItems.filter(canViewNav);
  const canManageOrganization = ["org_admin", "platform_admin"].includes(organization?.role || "");
  useEffect(() => {
    const requested = navItems.find((item) => item === nav);
    if (!organization || !requested || canAccessNav(requested, organization.role, permissions)) return;
    setAccessError("forbidden");
    setNav("运营总览");
    navigate("/overview", { replace: true });
  }, [nav, navigate, organization, permissions]);
  const chartRef = useRef<HTMLDivElement>(null);
  const factoryChartRef = useRef<HTMLDivElement>(null);
  const supplierChartRef = useRef<HTMLDivElement>(null);
  const workspaceLoadedRef = useRef(false);
  useEffect(() => {
    if (!profileOpen) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) setProfileOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  }, [profileOpen]);
  const headers: HeadersInit = token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : {};
  async function api<T>(path: string, init?: RequestInit): Promise<T> {
    try {
      return await apiRequest<T>(API, token, path, init, refresh, (accessToken, nextRefresh) => {
        localStorage.setItem("supplymind_token", accessToken);
        localStorage.setItem("supplymind_refresh", nextRefresh);
        setToken(accessToken);
        setRefresh(nextRefresh);
      });
    } catch (error) {
      if (error instanceof Error && "status" in error) {
        const status = Number((error as { status?: number }).status);
        setAccessError(status === 403 ? "forbidden" : status === 404 ? "not-found" : status === 401 ? "expired" : "");
      }
      if (error instanceof Error && "status" in error && (error as { status?: number }).status === 401 && !path.startsWith("/auth/login")) {
        localStorage.removeItem("supplymind_token");
        localStorage.removeItem("supplymind_refresh");
        setToken("");
        setRefresh("");
        setOrganization(null);
        setOrganizations([]);
        setNotice("登录已过期，请重新登录");
      }
      throw error;
    }
  }
  async function load() {
    if (!token) return;
    setBusy(true);
    try {
      let currentRole = organization?.role || "";
      if (!workspaceLoadedRef.current) {
        const [currentOrganization, currentPermissions, availableOrganizations] = await Promise.all([
          api<OrganizationSummary>("/organization"),
          api<PermissionMatrix>("/organization/permissions"),
          api<OrganizationAccess[]>("/auth/organizations"),
        ]);
        setOrganization(currentOrganization);
        setPermissions(currentPermissions);
        setOrganizations(availableOrganizations);
        setQuotaDraft((current) => ({ ...current, ...currentOrganization.quota }));
        currentRole = currentOrganization.role;
        workspaceLoadedRef.current = true;
      }

      if (nav === "运营总览" || nav === "大屏配置") {
        const query = new URLSearchParams({ ...(dashboardFilters.factory ? { factory: dashboardFilters.factory } : {}), ...(dashboardFilters.productLine ? { product_line: dashboardFilters.productLine } : {}), period: dashboardFilters.period });
        const [currentDashboard, dimensions, config] = await Promise.all([
          api<Dashboard>(`/dashboards/supply-chain?${query.toString()}`),
          api<{ factories: string[]; product_lines: string[]; suppliers: string[] }>("/dashboards/supply-chain/dimensions"),
          api<typeof dashboardConfig>("/dashboards/supply-chain/config"),
        ]);
        setDashboard(currentDashboard);
        setDashboardDimensions(dimensions);
        setDashboardConfig(config);
      }
      if (nav === "数据源" || nav === "分析会话") {
        const currentSources = await api<Source[]>("/data-sources");
        setSources(currentSources);
        setAnalysisSourceId((current) => current && currentSources.some((item) => item.id === current) ? current : "");
      }
      if (nav === "知识库" || nav === "分析会话") {
        const currentKnowledge = await api<KnowledgeBase[]>(`/knowledge-bases?${new URLSearchParams({ page: String(knowledgePage), page_size: String(knowledgePageSize), ...(knowledgeFilter.name ? { name: knowledgeFilter.name } : {}), ...(knowledgeFilter.status ? { status: knowledgeFilter.status } : {}) }).toString()}`);
        setKnowledge(currentKnowledge);
        setKnowledgeHasMore(currentKnowledge.length === knowledgePageSize);
        setAnalysisKnowledgeBaseId((current) => current && currentKnowledge.some((item) => item.id === current) ? current : "");
        if (nav === "知识库") setDocuments([]);
      }
      if (nav === "报告中心") {
        const reportQuery = new URLSearchParams({ ...(reportFilter.title ? { title: reportFilter.title } : {}), ...(reportFilter.status ? { status: reportFilter.status } : {}), ...(reportFilter.createdBy ? { created_by: reportFilter.createdBy } : {}), ...(reportFilter.runId ? { run_id: reportFilter.runId } : {}), ...(reportFilter.createdFrom ? { created_from: new Date(reportFilter.createdFrom).toISOString() } : {}), ...(reportFilter.createdTo ? { created_to: new Date(reportFilter.createdTo).toISOString() } : {}) });
        setReports(await api<Report[]>(`/reports?${reportQuery.toString()}`));
      }
      if (nav === "分析会话") {
        const currentAnalyses = await api<AnalysisRun[]>(`/analyses?page=${analysisPage}&page_size=${analysisPageSize}`);
        setAnalyses(currentAnalyses);
        setAnalysisHasMore(currentAnalyses.length === analysisPageSize);
      }
      if (nav === "组织与审计" || nav === "项目管理") {
        setMembers(await api<Member[]>("/members"));
      }
      if (nav === "组织与审计") {
        const [currentInvitations, currentAuditEvents] = await Promise.all([
          api<Invitation[]>("/members/invitations"),
          api<AuditEvent[]>(`/audit?${new URLSearchParams({ limit: "20", ...(auditFilter ? { action: auditFilter } : {}), ...(auditRunId ? { run_id: auditRunId } : {}) }).toString()}`),
        ]);
        setInvitations(currentInvitations);
        setAuditEvents(currentAuditEvents);
      }
      if (nav === "企业管理" && currentRole === "platform_admin") {
        setPlatformOrganizations(await api<PlatformOrganization[]>(`/platform/organizations?page=${platformPage}&page_size=10`));
      }
      if (nav === "系统状态") {
        const health = await api<SystemStatus>("/system/status");
        setSystemStatus(health.status === "ready" ? "ready" : "degraded");
        setSystemDetails(health);
        if (["org_admin", "platform_admin"].includes(currentRole)) {
          api<typeof failedTasks>("/ingestion-tasks?status=failed&page=1&page_size=10").then(setFailedTasks).catch(() => setFailedTasks([]));
        }
      }
    } catch (error) {
      setNotice(error instanceof Error ? `${getApiErrorMessage(getApiErrorState(error))} ${error.message}` : "无法读取工作区");
    } finally {
      setBusy(false);
    }
  }
  async function saveDashboardConfig(seconds: number, widgets = dashboardConfig.visible_widgets) {
    try {
      const config = await api<typeof dashboardConfig>("/dashboards/supply-chain/config", { method: "PATCH", body: JSON.stringify({ refresh_interval_seconds: seconds, visible_widgets: widgets }) });
      setDashboardConfig(config);
      setNotice("大屏组织级刷新配置已保存");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存大屏配置失败");
    }
  }
  useEffect(() => {
    if (window.location.pathname !== "/auth/callback") return;
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setLoginError("单点登录回调缺少授权参数");
      return;
    }
    fetch(`${API}/auth/oidc/callback?${new URLSearchParams({ code, state })}`)
      .then(async (response) => {
        if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "单点登录失败");
        return response.json() as Promise<{ access_token: string; refresh_token: string }>;
      })
      .then((body) => {
        localStorage.setItem("supplymind_token", body.access_token);
        localStorage.setItem("supplymind_refresh", body.refresh_token);
        setToken(body.access_token);
        setRefresh(body.refresh_token);
        window.history.replaceState({}, document.title, "/");
      })
      .catch((error) => setLoginError(error instanceof Error ? error.message : "单点登录失败"));
  }, []);
  useEffect(() => {
    void load();
  }, [token, nav, dashboardFilters, reportFilter, auditFilter, auditRunId, knowledgeFilter, analysisPage, analysisPageSize, knowledgePage, knowledgePageSize, platformPage]);
  useEffect(() => {
    if (token && organization && !canViewNav(nav as NavItem)) {
      selectNav(visibleNavItems[0] || "运营总览");
    }
  }, [token, organization, permissions, nav]);
  useEffect(() => {
    if (!analysisContextStorageKey) return;
    try {
      const saved = localStorage.getItem(analysisContextStorageKey);
      if (saved) {
        const parsed = JSON.parse(saved) as { conversationId?: string; messages?: typeof analysisMessages };
        if (parsed.conversationId) setAnalysisConversationId(parsed.conversationId);
        if (Array.isArray(parsed.messages)) setAnalysisMessages(parsed.messages.slice(-20));
      }
      analysisContextLoadedRef.current = analysisContextStorageKey;
    } catch {
      localStorage.removeItem(analysisContextStorageKey);
      analysisContextLoadedRef.current = analysisContextStorageKey;
    }
  }, [analysisContextStorageKey]);
  useEffect(() => {
    if (!analysisContextStorageKey || analysisContextLoadedRef.current !== analysisContextStorageKey) return;
    localStorage.setItem(analysisContextStorageKey, JSON.stringify({ conversationId: analysisConversationId, messages: analysisMessages.slice(-20) }));
  }, [analysisContextStorageKey, analysisConversationId, analysisMessages]);
  useEffect(() => {
    if (!dashboard || !chartRef.current || nav !== "运营总览") return;
    let disposed = false;
    let chart: import("../../services/charts-runtime").ChartInstance | undefined;
    let factoryChart: import("../../services/charts-runtime").ChartInstance | undefined;
    let supplierChart: import("../../services/charts-runtime").ChartInstance | undefined;
    const resize = () => chart?.resize();
    const renderCharts = async () => {
      const echarts = await loadCharts();
      if (disposed || !chartRef.current) return;
      chart = echarts.init(chartRef.current);
      chart.setOption({
      grid: { left: 12, right: 12, top: 20, bottom: 18, containLabel: true },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#14352c",
        borderWidth: 0,
        textStyle: { color: "#fff" },
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: dashboard.trend.map((x) => x.month),
        axisLabel: { color: "#73847c" },
      },
      yAxis: {
        type: "value",
        min: 80,
        max: 100,
        axisLabel: { color: "#73847c", formatter: "{value}%" },
        splitLine: { lineStyle: { color: "#edf2ef" } },
      },
      series: [
        {
          type: "line",
          smooth: true,
          data: dashboard.trend.map((x) => x.rate),
          symbol: "circle",
          symbolSize: 7,
          lineStyle: { width: 3, color: "#15966d" },
          itemStyle: { color: "#15966d", borderColor: "#fff", borderWidth: 2 },
          areaStyle: { color: "rgba(21,150,109,.1)" },
        },
      ],
    });
    const makeRankingChart = (element: HTMLDivElement, labels: string[], values: number[], color: string) => {
      const ranking = echarts.init(element);
      ranking.setOption({
        grid: { left: 82, right: 28, top: 8, bottom: 8, containLabel: false },
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (value: number) => `${value.toFixed(1)}%` },
        xAxis: { type: "value", min: 0, max: 100, axisLabel: { color: "#73847c", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#edf2ef" } } },
        yAxis: { type: "category", inverse: true, data: labels, axisLabel: { color: "#40584e", fontSize: 11 }, axisLine: { show: false }, axisTick: { show: false } },
        series: [{ type: "bar", barWidth: 16, data: values, itemStyle: { color, borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", color: "#40584e", formatter: (params: { value: number }) => `${params.value.toFixed(1)}%` } }],
      });
      return ranking;
    };
    factoryChart = (factoryChartRef.current && makeRankingChart(factoryChartRef.current, (dashboard.rankings?.factories || []).map((item) => item.factory || "未命名"), (dashboard.rankings?.factories || []).map((item) => Number(item.rate || 0)), "#15966d")) || undefined;
    supplierChart = (supplierChartRef.current && makeRankingChart(supplierChartRef.current, (dashboard.rankings?.suppliers || []).map((item) => item.supplier_name || "未命名"), (dashboard.rankings?.suppliers || []).map((item) => Number(item.rate || 0)), "#4c8fba")) || undefined;
    };
    window.addEventListener("resize", resize);
    void renderCharts();
    return () => {
      disposed = true;
      window.removeEventListener("resize", resize);
      chart?.dispose();
      factoryChart?.dispose();
      supplierChart?.dispose();
    };
  }, [dashboard, nav]);
  async function login(event: FormEvent) {
    event.preventDefault();
    setLoginError("");
    if (!loginEmail.trim() || !loginPassword || !loginOrganization.trim()) {
      setLoginError("请填写邮箱、密码和组织标识");
      return;
    }
    setLoginBusy(true);
    try {
      const body = await api<{ access_token: string; refresh_token?: string }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            email: loginEmail.trim(),
            password: loginPassword,
            organization_slug: loginOrganization.trim(),
          }),
        },
      );
      localStorage.setItem("supplymind_token", body.access_token);
      if (body.refresh_token)
        localStorage.setItem("supplymind_refresh", body.refresh_token);
      setToken(body.access_token);
      setRefresh(body.refresh_token || "");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "登录失败");
      setLoginPassword("");
    } finally {
      setLoginBusy(false);
    }
  }
  async function startOidc() {
    setOidcBusy(true);
    try {
      if (!loginOrganization.trim()) throw new Error("请先填写组织标识");
      window.location.assign(`${API}/auth/oidc/start?organization_slug=${encodeURIComponent(loginOrganization.trim())}`);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "单点登录暂不可用");
      setOidcBusy(false);
    }
  }
  async function acceptInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setInviteError("");
    try {
      const response = await fetch(`${API}/members/invitations/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: inviteToken, display_name: values.get("display_name"), password: values.get("password") }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(String(payload.detail || "邀请接受失败"));
      localStorage.setItem("supplymind_token", payload.access_token);
      localStorage.setItem("supplymind_refresh", payload.refresh_token || "");
      setToken(payload.access_token);
      setRefresh(payload.refresh_token || "");
      window.history.replaceState({}, "", window.location.pathname);
    } catch (error) {
      setInviteError(error instanceof Error ? error.message : "邀请接受失败");
    }
  }
  async function analyze(event: FormEvent) {
    event.preventDefault();
    if (!analysisSourceId || !analysisKnowledgeBaseId)
      return setNotice("请先选择真实数据源和知识库。");
    setBusy(true);
    const context = analysisMessages
      .slice(-8)
      .map((message) => `${message.role === "user" ? "用户" : "助手"}：${message.content}`);
    setAnalysisMessages((current) => [...current, { role: "user", content: question, created_at: new Date().toISOString() }]);
    setAnalysisResult(null);
    setEvents(["queued · 已排队，正在读取指标口径和数据结构..."]);
    let activeRunId = "";
    try {
      const idempotencyKey = crypto.randomUUID();
      const request = (accessToken: string) =>
        fetch(`${API}/analyses/stream`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
            "Idempotency-Key": idempotencyKey,
          },
          body: JSON.stringify({
            data_source_id: analysisSourceId,
            knowledge_base_id: analysisKnowledgeBaseId,
            question,
            context,
            conversation_id: analysisConversationId,
          }),
        });
      let response = await request(token);
      if (response.status === 401 && refresh) {
        const refreshed = await fetch(`${API}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (refreshed.ok) {
          const body = (await refreshed.json()) as {
            access_token: string;
            refresh_token?: string;
          };
          const nextRefresh = body.refresh_token || refresh;
          setToken(body.access_token);
          setRefresh(nextRefresh);
          localStorage.setItem("supplymind_token", body.access_token);
          localStorage.setItem("supplymind_refresh", nextRefresh);
          response = await request(body.access_token);
        }
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const trace = response.headers.get("x-trace-id");
        const detail = payload.detail;
        const message = typeof detail === "object" && detail ? String(detail.message || detail.hint || "分析请求被拒绝") : String(detail || "分析请求被拒绝");
        throw new Error(`${message}${trace ? `（Trace ID: ${trace}）` : ""}`);
      }
      const parsed = parseSseEvents(await readSseResponse(response, (chunk) => {
        const queued = chunk.find((item) => item.event === "queued");
        if (queued?.data.run_id) activeRunId = String(queued.data.run_id);
        if (queued?.data.conversation_id) setAnalysisConversationId(String(queued.data.conversation_id));
        if (chunk.length) setEvents((current) => [...current, ...chunk.map(({ event, data }) => `${event} · ${String(data.message || data.tool || data.run_id || "处理中")}`)].slice(-30));
      }));
      const completed = parsed.find(({ event }) => event === "completed");
      const draft = parsed.find(({ event }) => event === "sql_draft");
      const failed = parsed.find(({ event }) => event === "failed");
      if (completed) {
        const nextResult = { ...(completed.data as AnalysisResult), sql_draft: draft?.data.sql ? String(draft.data.sql) : undefined, guard_error: failed?.data.message ? String(failed.data.message) : undefined, trace_id: response.headers.get("x-trace-id") || undefined };
        setAnalysisResult(nextResult);
        setAnalysisMessages((current) => [...current, { role: "assistant", content: String(nextResult.result?.insight || "分析已完成"), created_at: new Date().toISOString() }]);
      }
      setEvents(
        parsed.map(
          ({ event, data }) =>
            `${event} · ${String(data.message || data.tool || data.run_id || (event === "completed" ? "分析完成" : "处理中"))}`,
        ),
      );
      await load();
    } catch (error) {
      if (activeRunId) {
        try {
          const recovered = await api<{
            run_id: string;
            status: string;
            steps: AgentStep[];
            result?: AnalysisResult;
            sql?: string;
            sql_draft?: string;
            guard_error?: string;
          }>(`/analyses/${activeRunId}/events`);
          setAnalysisSteps(recovered.steps || []);
          if (recovered.result) {
            setAnalysisResult({
              ...recovered.result,
              sql: recovered.sql,
              sql_draft: recovered.sql_draft,
              guard_error: recovered.guard_error,
            });
          }
          setEvents((current) => [...current, `reconnected · 已恢复运行 ${recovered.status}`]);
          await load();
        } catch {
          setEvents((current) => [...current, "分析连接中断，运行状态暂不可恢复"]);
        }
      } else {
        const message = error instanceof Error ? error.message : "分析失败";
        setEvents([message]);
        setAnalysisMessages((current) => [...current, { role: "assistant", content: `本次分析未执行：${message}`, created_at: new Date().toISOString() }]);
      }
    } finally {
      setBusy(false);
    }
  }
  function startNewAnalysisConversation() {
    setAnalysisConversationId(crypto.randomUUID());
    setAnalysisMessages([]);
    setAnalysisResult(null);
    setAnalysisSteps([]);
    setEvents([]);
    setSelectedAnalysis(null);
    setNotice("已创建新的分析会话");
  }
  async function switchOrganization(id: string) {
    if (!id || id === organization?.id) return;
    setBusy(true);
    try {
      const body = await api<{ access_token: string; refresh_token?: string }>(
        "/auth/switch-organization",
        { method: "POST", body: JSON.stringify({ organization_id: id }) },
      );
      const nextRefresh = body.refresh_token || refresh;
      localStorage.setItem("supplymind_token", body.access_token);
      localStorage.setItem("supplymind_refresh", nextRefresh);
      setToken(body.access_token);
      setRefresh(nextRefresh);
      workspaceLoadedRef.current = false;
      setDashboard(null);
      setSelectedAnalysis(null);
      setSelectedReport(null);
      setSources([]);
      setKnowledge([]);
      setMembers([]);
      setInvitations([]);
      setAuditEvents([]);
      setNotice("组织已切换");
      setProfileOpen(false);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "组织切换失败");
    } finally {
      setBusy(false);
    }
  }
  async function uploadDocument(
    event: FormEvent<HTMLFormElement>,
    knowledgeBaseId: string,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || !file.name)
      return setNotice("请选择 PDF、Markdown 或 TXT 文件");
    setBusy(true);
    try {
      const document = await api<Document>(
        `/knowledge-bases/${knowledgeBaseId}/documents`,
        {
          method: "POST",
          body: (() => {
            const payload = new FormData();
            payload.append("file", file);
            return payload;
          })(),
        },
      );
      setDocuments((current) => [
        document,
        ...current.filter((item) => item.id !== document.id),
      ]);
      event.currentTarget.reset();
      setNotice("文档已进入摄取队列");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "文档上传失败");
    } finally {
      setBusy(false);
    }
  }
  async function replaceDocument(document: Document, file: File) {
    setBusy(true);
    try {
      const payload = new FormData();
      payload.append("file", file);
      payload.append("replace_document_id", document.id);
      const updated = await api<Document>(`/knowledge-bases/${document.knowledge_base_id}/documents`, { method: "POST", body: payload });
      setDocuments((current) => [updated, ...current.filter((item) => item.id !== document.id)]);
      setNotice("文档新版本已进入摄取队列");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "文档替换失败");
    } finally {
      setBusy(false);
    }
  }
  async function createKnowledge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api("/knowledge-bases", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"),
          description: form.get("description") || "",
        }),
      });
      event.currentTarget.reset();
      setNotice("知识库已创建");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "创建失败");
    }
  }
  async function openKnowledge(id: string) {
    try {
      setSelectedKnowledge(
        await api<KnowledgeDetail>(`/knowledge-bases/${id}`),
      );
      setKnowledgeCitations([]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "知识库详情读取失败");
    }
  }
  async function toggleKnowledgeArchive() {
    if (!selectedKnowledge) return;
    try {
      const updated = await api<KnowledgeDetail>(
        `/knowledge-bases/${selectedKnowledge.id}/archive`,
        { method: "POST" },
      );
      setSelectedKnowledge(updated);
      setNotice(
        updated.is_archived
          ? "知识库已归档，新的分析不会选择它"
          : "知识库已恢复",
      );
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "知识库状态更新失败");
    }
  }
  async function updateKnowledge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedKnowledge) return;
    const form = new FormData(event.currentTarget);
    try {
      const updated = await api<KnowledgeDetail>(`/knowledge-bases/${selectedKnowledge.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: form.get("name"), description: form.get("description") || "" }),
      });
      setSelectedKnowledge(updated);
      setNotice("知识库信息已更新");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "知识库更新失败");
    }
  }
  async function deleteKnowledge() {
    if (!pendingKnowledgeDelete) return;
    const target = pendingKnowledgeDelete;
    try {
      await api(`/knowledge-bases/${target.id}`, { method: "DELETE" });
      setKnowledge((current) => current.filter((item) => item.id !== target.id));
      setDocuments((current) => current.filter((item) => item.knowledge_base_id !== target.id));
      setSelectedKnowledge(null);
      setPendingKnowledgeDelete(null);
      setNotice("知识库已删除");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "知识库删除失败");
    }
  }
  async function retryIngestion(taskId: string) {
    try {
      await api(`/ingestion-tasks/${taskId}/retry`, { method: "POST" });
      setNotice("摄取任务已重新排队");
      await load();
      if (selectedKnowledge) await openKnowledge(selectedKnowledge.id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "任务重试失败");
    }
  }
  async function cancelIngestion(taskId: string) {
    try {
      await api(`/ingestion-tasks/${taskId}/cancel`, { method: "POST" });
      setNotice("摄取任务已取消");
      await load();
      if (selectedKnowledge) await openKnowledge(selectedKnowledge.id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "任务取消失败");
    }
  }
  async function retryDeadLetter(taskId: string) {
    try {
      await api(`/ingestion-tasks/${taskId}/dead-letter/retry`, { method: "POST" });
      setFailedTasks((current) => current.filter((task) => task.id !== taskId));
      setNotice("死信任务已重新入队");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "死信任务重试失败");
    }
  }
  async function toggleDocumentArchive(document: Document) {
    try {
      await api(`/documents/${document.id}/archive`, { method: "POST" });
      setNotice(document.is_archived ? "文档已恢复" : "文档已归档");
      await load();
      if (selectedKnowledge) await openKnowledge(selectedKnowledge.id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "文档状态更新失败");
    }
  }
  async function deleteDocument(document: Document) {
    if (!window.confirm(`确认删除文档“${document.filename}”？`)) return;
    try {
      await api(`/documents/${document.id}`, { method: "DELETE" });
      setNotice("文档已删除");
      await load();
      if (selectedKnowledge) await openKnowledge(selectedKnowledge.id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "文档删除失败");
    }
  }
  async function updateDocumentMetadata(document: Document, metadata: Record<string, unknown>) {
    try {
      const updated = await api<Document>(`/documents/${document.id}/metadata`, { method: "PATCH", body: JSON.stringify(metadata) });
      setDocuments((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice("指标口径已保存");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "指标口径保存失败");
      throw error;
    }
  }
  async function openDocumentSource(document: Document) {
    try {
      setDocumentSource(await api<DocumentSource>(`/knowledge-bases/${document.knowledge_base_id}/documents/${document.id}/source`));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "文档原文读取失败");
    }
  }
  async function searchKnowledge(event: FormEvent) {
    event.preventDefault();
    if (!selectedKnowledge || !knowledgeQuery.trim()) return;
    try {
      const result = await api<{ results: Citation[] }>(
        `/knowledge-bases/${selectedKnowledge.id}/search`,
        {
          method: "POST",
          body: JSON.stringify({ query: knowledgeQuery, limit: 5 }),
        },
      );
      setKnowledgeCitations(result.results);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "检索失败");
    }
  }
  async function createSource(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/data-sources", {
        method: "POST",
        body: JSON.stringify({
          ...sourceDraft,
          port: Number(sourceDraft.port),
          allowed_tables: [],
          tls_required: sourceDraft.tls_required,
        }),
      });
      setNotice("数据源已创建");
      setSourceDraft({
        name: "",
        engine: "postgresql",
        host: "",
        port: "5432",
        database_name: "",
        username: "",
        password: "",
        allowed_tables: "",
        tls_required: true,
      });
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "数据源创建失败");
    } finally {
      setBusy(false);
    }
  }
  async function importDemoSources() {
    setBusy(true);
    try {
      const imported = await api<Source[]>("/data-sources/import-demo", { method: "POST" });
      setNotice(`演示数据源已导入，当前共 ${imported.length} 个数据源`);
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "一键导入失败");
    } finally {
      setBusy(false);
    }
  }
  async function testSource(id: string) {
    try {
      await api(`/data-sources/${id}/test`, { method: "POST" });
      setNotice("连接测试通过");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "连接测试失败");
    }
  }
  async function syncSource(id: string) {
    try {
      const result = await api<{ tables?: unknown[]; task_id?: string; status?: string }>(
        `/data-sources/${id}/sync`,
        { method: "POST" },
      );
      if (result.tables) {
        setNotice(`Schema 同步完成，共 ${result.tables.length} 张表`);
      } else if (result.task_id) {
        setNotice("Schema 同步已进入 Worker 队列");
        for (let attempt = 0; attempt < 20; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1500));
          const tasks = await api<{ id: string; status: string; error_message?: string }[]>(`/data-sources/${id}/sync-tasks`);
          const task = tasks.find((item) => item.id === result.task_id);
          if (task?.status === "completed") { setNotice("Schema 同步完成"); await openSource(id); break; }
          if (task?.status === "failed") { setNotice(`Schema 同步失败：${task.error_message || "未知原因"}`); break; }
        }
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Schema 同步失败");
    }
  }
  async function openSource(id: string) {
    try {
      const [source, schema, syncTasks] = await Promise.all([
        api<Source>(`/data-sources/${id}`),
        api<{
          tables: SchemaTable[];
          table_count: number;
          created_at: string;
        } | null>(`/data-sources/${id}/schema`),
        api<{ id: string; status: string; started_at?: string; finished_at?: string; error_message?: string; celery_task_id?: string }[]>(`/data-sources/${id}/sync-tasks`),
      ]);
      setSelectedSource(source);
      setSourceSchema(schema);
      setAllowlistDraft(source.allowed_tables);
      setSourceSyncTasks(syncTasks);
      setSelectedSchemaTable(null);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "数据源详情读取失败");
    }
  }
  async function saveAllowlist() {
    if (!selectedSource) return;
    try {
      const updated = await api<Source>(`/data-sources/${selectedSource.id}/allowlist`, { method: "PATCH", body: JSON.stringify({ allowed_tables: allowlistDraft }) });
      setSelectedSource(updated);
      setNotice("白名单已保存");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "白名单保存失败");
    }
  }
  async function toggleSource(id: string) {
    try {
      await api(`/data-sources/${id}/disable`, { method: "POST" });
      setNotice("数据源状态已更新");
      await load();
      if (selectedSource?.id === id) await openSource(id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "数据源状态更新失败");
    }
  }
  async function openAnalysis(id: string) {
    try {
      const [run, steps] = await Promise.all([
        api<AnalysisRun>(`/analyses/${id}`),
        api<AgentStep[]>(`/analyses/${id}/steps`),
      ]);
      setSelectedAnalysis(run);
      setAnalysisSteps(steps);
      setAnalysisResult(run.result ? { run_id: run.id, sql: run.sql, sql_draft: run.sql_draft, guard_error: run.guard_error, result: run.result as AnalysisResult["result"] } : null);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "分析详情读取失败");
    }
  }
  async function cancelAnalysis(id: string) {
    try {
      await api(`/analyses/${id}/cancel`, { method: "POST" });
      setNotice("分析已取消");
      await openAnalysis(id);
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "分析取消失败");
    }
  }
  async function retryAnalysis(id: string) {
    setBusy(true);
    setEvents(["retry · 正在重新执行分析..."]);
    try {
      const response = await fetch(`${API}/analyses/${id}/retry`, { method: "POST", headers });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(String(payload.detail || "分析重试被拒绝"));
      }
      const parsed = parseSseEvents(await response.text());
      const completed = parsed.find(({ event }) => event === "completed");
      const draft = parsed.find(({ event }) => event === "sql_draft");
      const failed = parsed.find(({ event }) => event === "failed");
      if (completed) setAnalysisResult({ ...(completed.data as AnalysisResult), sql_draft: draft?.data.sql ? String(draft.data.sql) : undefined, guard_error: failed?.data.message ? String(failed.data.message) : undefined, trace_id: response.headers.get("x-trace-id") || undefined });
      setEvents(parsed.map(({ event, data }) => `${event} · ${String(data.message || data.tool || data.run_id || (event === "completed" ? "分析完成" : "处理中"))}`));
      await load();
      if (completed?.data.run_id) await openAnalysis(String(completed.data.run_id));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "分析重试失败");
    } finally {
      setBusy(false);
    }
  }
  async function openReport(id: string) {
    try {
      const [report, exports] = await Promise.all([
        api<Report>(`/reports/${id}`),
        api<ReportExport[]>(`/reports/${id}/exports`),
      ]);
      setSelectedReport(report);
      setReportExports(exports);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "报告详情读取失败");
    }
  }
  async function refreshDashboard() {
    setRefreshingDashboard(true);
    try {
      const query = new URLSearchParams({
        ...(dashboardFilters.factory
          ? { factory: dashboardFilters.factory }
          : {}),
        ...(dashboardFilters.productLine
          ? { product_line: dashboardFilters.productLine }
          : {}),
        period: dashboardFilters.period,
      });
      const result = await api<{ status: string }>(
        `/dashboards/supply-chain/refresh?${query.toString()}`,
        { method: "POST" },
      );
      setNotice(
        result.status === "queued"
          ? "大屏刷新任务已排队，稍后点击刷新查看结果"
          : "大屏已刷新",
      );
      await load();
      if (result.status === "queued") {
        for (let attempt = 0; attempt < 10; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1500));
          await load();
          if (attempt === 9) setNotice("大屏刷新任务已完成或仍在后台处理，可继续查看最新缓存");
        }
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "大屏刷新失败");
    } finally {
      setRefreshingDashboard(false);
    }
  }
  async function runSourceQuery(event: FormEvent) {
    event.preventDefault();
    if (!selectedSource) return;
    setBusy(true);
    try {
      const result = await api<NonNullable<typeof sourceQueryResult>>(`/data-sources/${selectedSource.id}/query`, { method: "POST", body: JSON.stringify({ sql: sourceQuery }) });
      setSourceQueryResult(result);
      setNotice(`查询完成：${result.row_count} 行，耗时 ${result.elapsed_ms} ms`);
    } catch (error) {
      setSourceQueryResult(null);
      setNotice(error instanceof Error ? error.message : "查询试跑失败");
    } finally {
      setBusy(false);
    }
  }
  async function updateQuotas(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const saved = await api<Record<string, number>>("/organization/quotas", {
        method: "PATCH",
        body: JSON.stringify(quotaDraft),
      });
      setQuotaDraft({ ...quotaDraft, ...saved });
      setNotice("组织配额已保存");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "配额保存失败");
    } finally {
      setBusy(false);
    }
  }
  async function updateOwner(event: FormEvent) {
    event.preventDefault();
    if (!organization?.owner_user_id) return setNotice("请选择负责人");
    setBusy(true);
    try {
      const saved = await api<OrganizationSummary>("/organization/settings", {
        method: "PATCH",
        body: JSON.stringify({ owner_user_id: organization.owner_user_id }),
      });
      setOrganization(saved);
      setNotice("组织负责人已更新");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "负责人保存失败");
    } finally {
      setBusy(false);
    }
  }
  async function inviteMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const invitation = await api<Invitation>("/members/invitations", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          role: form.get("role"),
          expires_in_days: 7,
        }),
      });
      if (invitation.token) setInvitationLink(`${window.location.origin}${window.location.pathname}?invite=${encodeURIComponent(invitation.token)}`);
      setNotice("邀请已创建，请复制一次性邀请链接并通过安全渠道发送。");
      event.currentTarget.reset();
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "邀请创建失败");
    }
  }
  async function updateMemberRole(member: Member, role: string) {
    try {
      await api(`/members/${member.user_id}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      setNotice("成员角色已更新");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "角色更新失败");
    }
  }
  async function toggleMember(member: Member) {
    try {
      await api(`/members/${member.user_id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !member.is_active }),
      });
      setNotice("成员状态已更新");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "成员状态更新失败");
    }
  }
  async function resendInvitation(invitation: Invitation) {
    try {
      const updated = await api<Invitation>(
        `/members/invitations/${invitation.id}/resend`,
        { method: "POST" },
      );
      if (updated.token) setInvitationLink(`${window.location.origin}${window.location.pathname}?invite=${encodeURIComponent(updated.token)}`);
      setNotice("邀请已重发，请复制新的链接并通过安全渠道发送。旧链接已失效。");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "邀请重发失败");
    }
  }
  async function revokeInvitation(invitation: Invitation) {
    try {
      await api<Invitation>(`/members/invitations/${invitation.id}/revoke`, { method: "POST" });
      setNotice("邀请已撤销，历史记录已保留");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "邀请撤销失败");
    }
  }
  async function togglePlatformOrganization(item: PlatformOrganization) {
    if (!window.confirm(`确认${item.is_active ? "停用" : "启用"}${item.name}？停用后该企业用户将无法访问系统。`)) return;
    try {
      const updated = await api<PlatformOrganization>(`/platform/organizations/${item.id}/status`, { method: "POST", body: JSON.stringify({ is_active: !item.is_active }) });
      setPlatformOrganizations((current) => current.map((organization) => organization.id === updated.id ? updated : organization));
      setNotice(`企业已${updated.is_active ? "启用" : "停用"}`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "企业状态更新失败"); }
  }
  async function renamePlatformOrganization(item: PlatformOrganization, name: string) {
    try {
      const updated = await api<PlatformOrganization>(`/platform/organizations/${item.id}`, { method: "PATCH", body: JSON.stringify({ name }) });
      setPlatformOrganizations((current) => current.map((organization) => organization.id === updated.id ? updated : organization));
      setNotice("企业名称已更新");
    } catch (error) { setNotice(error instanceof Error ? error.message : "企业更新失败"); }
  }
  async function downloadReport(id: string) {
    try {
      let response = await fetch(`${API}/reports/${id}/exports/pdf/download`, { headers });
      if (!response.ok && response.status === 404) {
        await api(`/reports/${id}/exports/pdf`, { method: "POST" });
        setNotice("PDF 已进入导出队列，正在等待生成...");
        for (let attempt = 0; attempt < 20; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1500));
          const status = await api<ReportExport>(`/reports/${id}/exports/pdf`);
          setReportExports((current) => [status, ...current.filter((item) => item.id !== status.id)]);
          if (status.status === "failed") return setNotice(`PDF 导出失败：${status.error_message || "未知原因"}`);
          if (status.status === "completed") {
            response = await fetch(`${API}/reports/${id}/exports/pdf/download`, { headers });
            break;
          }
        }
        if (!response.ok) return setNotice("PDF 仍在生成中，请稍后在报告详情中重试");
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const trace = response.headers.get("x-trace-id");
        return setNotice(`${String(payload.detail || "PDF 下载失败，请稍后重试")}${trace ? `（Trace ID: ${trace}）` : ""}`);
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `${id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      setNotice("PDF 下载已开始");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "PDF 下载失败，请稍后重试");
    }
  }
  async function retryReportExport(reportId: string, exportId: string) {
    try {
      const updated = await api<ReportExport>(`/reports/${reportId}/exports/${exportId}/retry`, { method: "POST" });
      setReportExports((current) => [updated, ...current.filter((item) => item.id !== updated.id)]);
      setNotice("PDF 导出已重新排队");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "PDF 重试失败");
    }
  }
  async function logout() {
    if (refresh)
      await api("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      }).catch(() => undefined);
    localStorage.clear();
    workspaceLoadedRef.current = false;
    setToken("");
  }
  if (!token)
    return <AuthScreen inviteToken={inviteToken} loginEmail={loginEmail} loginPassword={loginPassword} loginOrganization={loginOrganization} showPassword={showLoginPassword} loginBusy={loginBusy} oidcBusy={oidcBusy} loginError={loginError} inviteError={inviteError} onLogin={login} onAcceptInvitation={acceptInvitation} onStartOidc={() => void startOidc()} onEmailChange={setLoginEmail} onPasswordChange={setLoginPassword} onOrganizationChange={setLoginOrganization} onTogglePassword={() => setShowLoginPassword((value) => !value)} />;
  function page() {
    if (nav === "企业管理") return <PlatformOrganizationsPage organizations={platformOrganizations} busy={busy} onToggle={(item) => void togglePlatformOrganization(item)} onRename={(item, name) => void renamePlatformOrganization(item, name)} />;
    if (nav === "大屏配置") return <DashboardConfigurationPage config={dashboardConfig} busy={busy} onSave={(seconds, widgets) => void saveDashboardConfig(seconds, widgets)} />;
    if (nav === "组织与审计") return <OrganizationAuditPage members={members} invitations={invitations} auditEvents={auditEvents} organization={organization} auditFilter={auditFilter} auditRunId={auditRunId} setAuditFilter={setAuditFilter} setAuditRunId={setAuditRunId} onInvite={inviteMember} onRoleChange={updateMemberRole} onToggle={toggleMember} onResend={resendInvitation} onRevoke={revokeInvitation} selectedAudit={selectedAudit} setSelectedAudit={setSelectedAudit} invitationLink={invitationLink} onDismissInvitationLink={() => setInvitationLink(null)} />;
    if (nav === "__legacy_org__")
      return (
        <DataView
          kicker="ORG / ACCESS CONTROL"
          title="组织与审计"
          copy="成员角色、邀请和访问状态。关键动作都会留下审计记录。"
        >
          <form
            className="inline-form member-invite-form"
            onSubmit={(event) => void inviteMember(event)}
          >
            <input
              required
              type="email"
              name="email"
              placeholder="成员邮箱"
              aria-label="成员邮箱"
            />
            <select name="role" defaultValue="viewer" aria-label="成员角色">
              <option value="viewer">只读成员</option>
              <option value="analyst">分析师</option>
              <option value="org_admin">组织管理员</option>
            </select>
            <button className="primary-button">发送邀请</button>
          </form>
          <section className="source-list">
            {members.length ? (
              members.map((m) => (
                <article className="list-row" key={m.user_id}>
                  <div>
                    <strong>{m.display_name}</strong>
                    <p>{m.email}</p>
                  </div>
                  <select
                    value={m.role}
                    onChange={(event) =>
                      void updateMemberRole(m, event.target.value)
                    }
                    aria-label={`${m.email}角色`}
                  >
                    <option value="viewer">只读成员</option>
                    <option value="analyst">分析师</option>
                    <option value="org_admin">组织管理员</option>
                  </select>
                  <span className={`status-chip ${m.is_active ? "" : "muted"}`}>
                    {m.is_active ? "启用" : "已停用"}
                  </span>
                  <button
                    className="text-button"
                    onClick={() => void toggleMember(m)}
                  >
                    {m.is_active ? "停用" : "启用"}
                  </button>
                </article>
              ))
            ) : (
              <Empty
                title="成员列表暂不可用"
                copy="需要组织管理员权限才能查看成员与审计数据。"
              />
            )}
          </section>
          <section className="source-list">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">INVITATIONS</p>
                <h3>待处理邀请</h3>
              </div>
              <span className="panel-meta">
                {invitations.filter((item) => item.status === "pending").length}{" "}
                条
              </span>
            </div>
            {invitations
              .filter((item) => item.status === "pending")
              .map((item) => (
                <article className="list-row" key={item.id}>
                  <div>
                    <strong>{item.email}</strong>
                    <p>
                      {item.role} · 截止{" "}
                      {new Date(item.expires_at).toLocaleDateString("zh-CN")}
                    </p>
                  </div>
                  <button
                    className="secondary-button"
                    onClick={() => void resendInvitation(item)}
                  >
                    重新发送
                  </button>
                </article>
              ))}
          </section>
          <section className="project-access">
            <div>
              <p className="section-kicker">QUOTA USAGE</p>
              <h3>组织配额使用量</h3>
            </div>
            <div className="access-list">
              <span>
                并发分析：{organization?.quota_usage.concurrent_analyses ?? 0} /{" "}
                {organization?.quota.max_concurrent_analyses ?? "—"}
              </span>
              <span>
                今日运行：{organization?.quota_usage.daily_analysis_runs ?? 0} /{" "}
                {organization?.quota.daily_analysis_runs ?? "—"}
              </span>
              <span>
                文档存储：
                {organization?.quota_usage.document_storage_bytes ?? 0} bytes
              </span>
              <span>
                报告文件：{organization?.quota_usage.report_storage_files ?? 0}
              </span>
            </div>
          </section>
          <section className="audit-section">
            <div className="audit-heading">
              <div>
                <p className="section-kicker">RECENT ACTIVITY</p>
                <h3>最近审计动作</h3>
              </div>
              <input
                className="audit-filter"
                value={auditFilter}
                onChange={(event) => setAuditFilter(event.target.value)}
                placeholder="筛选动作或资源"
                aria-label="筛选审计动作"
              />
              <input
                className="audit-filter"
                value={auditRunId}
                onChange={(event) => setAuditRunId(event.target.value)}
                placeholder="按运行 ID 筛选"
                aria-label="按运行 ID 筛选审计"
              />
            </div>
            {auditEvents
              .filter(
                (event) =>
                  !auditFilter ||
                  `${event.action} ${event.resource_type}`
                    .toLowerCase()
                    .includes(auditFilter.toLowerCase()),
              )
              .map((event) => (
                <article className="audit-row" key={event.id}>
                  <strong>{event.action}</strong>
                  <span>{event.resource_type}</span>
                  <time>
                    {new Date(event.occurred_at).toLocaleString("zh-CN")}
                  </time>
                </article>
              ))}
          </section>
        </DataView>
      );
    if (nav === "项目管理") return <ProjectManagementPage organization={organization} members={members} sources={sources} knowledgeBases={knowledge} reports={reports} permissions={permissions} quotas={quotaDraft} setQuotas={setQuotaDraft} busy={busy} onNavigate={selectNav} onUpdateOwner={(event) => void updateOwner(event)} onOwnerChange={(userId) => setOrganization(organization ? { ...organization, owner_user_id: userId, owner_name: members.find((member) => member.user_id === userId)?.display_name || null } : organization)} onUpdateQuotas={(event) => void updateQuotas(event)} />;
    if (nav === "__legacy_project_markup__")
      return (
        <DataView
          kicker="WORKSPACE / PROJECT CONTROL"
          title="项目管理"
          copy="统一查看组织资源、成员权限和运行配额。"
        >
          <section className="project-summary">
            <article>
              <span>成员</span>
              <strong>{organization?.member_count ?? "—"}</strong>
              <button
                className="text-button"
                onClick={() => selectNav("组织与审计")}
              >
                管理成员 →
              </button>
            </article>
            <article>
              <span>数据源</span>
              <strong>
                {organization?.data_source_count ?? sources.length}
              </strong>
              <button className="text-button" onClick={() => selectNav("数据源")}>
                查看数据源 →
              </button>
            </article>
            <article>
              <span>知识库</span>
              <strong>
                {organization?.knowledge_base_count ?? knowledge.length}
              </strong>
              <button className="text-button" onClick={() => selectNav("知识库")}>
                维护知识库 →
              </button>
            </article>
            <article>
              <span>报告</span>
              <strong>{organization?.report_count ?? reports.length}</strong>
              <button
                className="text-button"
                onClick={() => selectNav("报告中心")}
              >
                打开报告中心 →
              </button>
            </article>
          </section>
          <section className="project-access">
            <div>
              <p className="section-kicker">
                ORGANIZATION / {organization?.slug || "LOADING"}
              </p>
              <h3>{organization?.name || "组织概览"}</h3>
              <p>
                当前角色：{organization?.role || "—"}
                。资源统计和权限均来自组织接口。
              </p>
            </div>
            <div className="access-list">
              <span>
                <b className="access-dot allowed" />
                成员与角色
              </span>
              <span>
                <b className="access-dot allowed" />
                数据源配置
              </span>
              <span>
                <b className="access-dot allowed" />
                知识库摄取
              </span>
              <span>
                <b className="access-dot allowed" />
                审计查看
              </span>
            </div>
          </section>
          <section className="project-management-grid">
            <form className="quota-form" onSubmit={(event) => void updateOwner(event)}>
              <div className="panel-heading">
                <div><p className="section-kicker">ORGANIZATION / OWNER</p><h3>企业负责人</h3></div>
                <span className="panel-meta">仅组织管理员可修改</span>
              </div>
              <label>
                负责人
                <select
                  value={organization?.owner_user_id || ""}
                  disabled={(organization?.role !== "org_admin" && organization?.role !== "platform_admin") || busy}
                  onChange={(event) => setOrganization(organization ? { ...organization, owner_user_id: event.target.value, owner_name: members.find((member) => member.user_id === event.target.value)?.display_name || null } : organization)}
                >
                  <option value="">请选择组织成员</option>
                  {members.filter((member) => member.is_active).map((member) => <option key={member.user_id} value={member.user_id}>{member.display_name} · {member.email}</option>)}
                </select>
              </label>
              <button className="primary-button" disabled={(organization?.role !== "org_admin" && organization?.role !== "platform_admin") || busy}>保存负责人</button>
            </form>
            <form
              className="quota-form"
              onSubmit={(event) => void updateQuotas(event)}
            >
              <div className="panel-heading">
                <div>
                  <p className="section-kicker">QUOTA / ORGANIZATION POLICY</p>
                  <h3>组织配额</h3>
                </div>
                <span className="panel-meta">保存前请确认影响范围</span>
              </div>
              <label>
                分析并发数
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={quotaDraft.max_concurrent_analyses}
                  onChange={(event) =>
                    setQuotaDraft({
                      ...quotaDraft,
                      max_concurrent_analyses: Number(event.target.value),
                    })
                  }
                />
              </label>
              <label>
                每日分析次数
                <input
                  type="number"
                  min="1"
                  max="100000"
                  value={quotaDraft.daily_analysis_runs}
                  onChange={(event) =>
                    setQuotaDraft({
                      ...quotaDraft,
                      daily_analysis_runs: Number(event.target.value),
                    })
                  }
                />
              </label>
              <label>
                单文件大小（MB）
                <input
                  type="number"
                  min="1"
                  max="1024"
                  value={quotaDraft.max_document_size_mb}
                  onChange={(event) =>
                    setQuotaDraft({
                      ...quotaDraft,
                      max_document_size_mb: Number(event.target.value),
                    })
                  }
                />
              </label>
              <label>
                数据保留天数
                <input
                  type="number"
                  min="1"
                  max="3650"
                  value={quotaDraft.retention_days}
                  onChange={(event) =>
                    setQuotaDraft({
                      ...quotaDraft,
                      retention_days: Number(event.target.value),
                    })
                  }
                />
              </label>
              <button className="primary-button" disabled={busy}>
                保存配额
              </button>
            </form>
            <section className="permission-panel">
              <div className="panel-heading">
                <div>
                  <p className="section-kicker">ACCESS / ROLE MATRIX</p>
                  <h3>权限矩阵</h3>
                </div>
              </div>
              <div className="permission-table">
                {Object.entries(permissions?.roles ?? {}).map(([role, actions]) => (
                    <div className="permission-row" key={role}>
                      <strong>{role}</strong>
                      <span>
                        {Object.entries(actions)
                          .filter(([, allowed]) => allowed)
                          .map(([action]) => action.replaceAll("_", " "))
                          .join(" · ") || "仅查看授权资源"}
                      </span>
                    </div>
                  ))}
              </div>
            </section>
          </section>
        </DataView>
      );
    if (nav === "数据源") return <DataSourcesPage busy={busy} sources={sources} draft={sourceDraft} setDraft={setSourceDraft} onImportDemo={() => void importDemoSources()} onCreate={(event) => void createSource(event)} onOpen={(id) => void openSource(id)} onTest={(id) => void testSource(id)} onSync={(id) => void syncSource(id)} onToggle={(id) => void toggleSource(id)}>{selectedSource && <DataSourceDetail source={selectedSource} schema={sourceSchema} tasks={sourceSyncTasks} selectedTable={selectedSchemaTable} onSelectTable={(name) => void (async () => { try { setSelectedSchemaTable(await api<SchemaTable>(`/data-sources/${selectedSource.id}/schema/tables/${encodeURIComponent(name)}`)); } catch (error) { setNotice(error instanceof Error ? error.message : "无法读取表结构"); } })()} allowlist={allowlistDraft} setAllowlist={setAllowlistDraft} onSaveAllowlist={() => void saveAllowlist()} canManage={["org_admin", "platform_admin"].includes(organization?.role || "")} query={sourceQuery} setQuery={setSourceQuery} onRunQuery={(event) => void runSourceQuery(event)} result={sourceQueryResult} onClose={() => setSelectedSource(null)} />}</DataSourcesPage>;
    if (nav === "__legacy_data_source_markup__")
      return (
        <DataView
          kicker="DATA SOURCES / READ ONLY"
          title="数据源"
          copy="管理组织授权的数据连接与表白名单。"
        >
          <div className="source-page-actions"><div><p className="section-kicker">SOURCE / ONBOARDING</p><strong>先导入演示数据，或接入你的只读数据库</strong><small>导入后仍需测试连接并同步 Schema，分析只使用已启用且通过白名单校验的数据源。</small></div><button className="secondary-button" onClick={() => void importDemoSources()} disabled={busy}>一键导入演示数据</button></div>
          <form className="source-form" onSubmit={createSource}>
            <div className="source-wizard-steps" aria-label="数据源接入步骤"><span className="active">1 连接信息</span><span>2 TLS / 网络</span><span>3 Schema 同步</span><span>4 白名单确认</span></div>
            <input
              required
              placeholder="名称"
              aria-label="数据源名称"
              value={sourceDraft.name}
              onChange={(e) =>
                setSourceDraft({ ...sourceDraft, name: e.target.value })
              }
            />
            <select
              aria-label="数据库类型"
              value={sourceDraft.engine}
              onChange={(e) =>
                setSourceDraft({
                  ...sourceDraft,
                  engine: e.target.value,
                  port: e.target.value === "mysql" ? "3306" : "5432",
                })
              }
            >
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
            </select>
            <input
              required
              placeholder="主机"
              aria-label="数据库主机"
              value={sourceDraft.host}
              onChange={(e) =>
                setSourceDraft({ ...sourceDraft, host: e.target.value })
              }
            />
            <input
              required
              placeholder="端口"
              aria-label="数据库端口"
              value={sourceDraft.port}
              onChange={(e) =>
                setSourceDraft({ ...sourceDraft, port: e.target.value })
              }
            />
            <input
              required
              placeholder="数据库"
              aria-label="数据库名称"
              value={sourceDraft.database_name}
              onChange={(e) =>
                setSourceDraft({
                  ...sourceDraft,
                  database_name: e.target.value,
                })
              }
            />
            <input
              required
              placeholder="只读用户名"
              aria-label="只读用户名"
              value={sourceDraft.username}
              onChange={(e) =>
                setSourceDraft({ ...sourceDraft, username: e.target.value })
              }
            />
            <input
              required
              type="password"
              placeholder="密码"
              aria-label="只读密码"
              value={sourceDraft.password}
              onChange={(e) =>
                setSourceDraft({ ...sourceDraft, password: e.target.value })
              }
            />
            <p className="detail-hint source-form-hint">创建后先测试连接并同步 Schema，再从快照中勾选分析白名单。</p>
            <button className="primary-button" disabled={busy}>
              接入只读数据源
            </button>
          </form>
          <SourceList sources={sources} onOpen={(id) => void openSource(id)} onTest={(id) => void testSource(id)} onSync={(id) => void syncSource(id)} onToggle={(id) => void toggleSource(id)} />
          {selectedSource && (
            <section className="detail-panel">
              <div className="panel-heading">
                <div>
                  <p className="section-kicker">SOURCE / DETAIL</p>
                  <h3>{selectedSource.name}</h3>
                  <p>
                    {selectedSource.engine} · {selectedSource.host}:
                    {selectedSource.port} · {selectedSource.database_name}
                  </p>
                </div>
                <button
                  className="text-button"
                  onClick={() => setSelectedSource(null)}
                >
                  关闭
                </button>
              </div>
              <div className="detail-meta">
                <span>
                  状态：
                  {selectedSource.status === "disabled" ? "已停用" : "已启用"}
                </span>
                <span>允许表：{selectedSource.allowed_tables.join(" · ")}</span>
                <span>
                  最近同步：
                  {selectedSource.last_synced_at
                    ? new Date(selectedSource.last_synced_at).toLocaleString(
                        "zh-CN",
                      )
                    : "尚未同步"}
                </span>
              </div>
              <div className="allowlist-editor">
                <div className="panel-heading"><div><h4>分析白名单</h4><p className="detail-hint">只能选择最近一次 Schema 快照中的表。</p></div><button className="secondary-button" onClick={() => void saveAllowlist()} disabled={organization?.role !== "org_admin" && organization?.role !== "platform_admin"}>保存白名单</button></div>
                <div className="allowlist-grid">{(sourceSchema?.tables || []).map((table) => { const tableName = table.name || table.table_name || ""; return <label key={tableName}><input type="checkbox" checked={allowlistDraft.includes(tableName)} onChange={(event) => setAllowlistDraft((current) => event.target.checked ? [...new Set([...current, tableName])] : current.filter((item) => item !== tableName))} />{tableName}</label>; })}</div>
              </div>
              <section className="sync-task-panel"><div className="panel-heading"><div><h4>Schema 同步任务</h4><p className="detail-hint">记录最近任务状态、任务 ID 和失败原因。</p></div></div>{sourceSyncTasks.length ? sourceSyncTasks.slice(0, 5).map((task) => <div className="sync-task-row" key={task.id}><strong>{task.status}</strong><span>{task.celery_task_id || task.id}</span><time>{task.finished_at ? new Date(task.finished_at).toLocaleString("zh-CN") : task.started_at ? new Date(task.started_at).toLocaleString("zh-CN") : "等待开始"}</time>{task.error_message && <small>{task.error_message}</small>}</div>) : <p className="detail-hint">尚未发起 Schema 同步。</p>}</section>
              <h4>
                Schema 快照{" "}
                {sourceSchema ? `· ${sourceSchema.table_count} 张表` : ""}
              </h4>
              {sourceSchema ? (
                <div className="schema-browser">
                  <div className="schema-table-list">
                    {sourceSchema.tables.map((table) => {
                      const tableName = table.name || table.table_name || "未命名表";
                      return (
                        <button
                          className={`schema-table-item ${selectedSchemaTable === table ? "selected" : ""}`}
                          key={tableName}
                          onClick={() => void (async () => {
                            try {
                              const detail = await api<SchemaTable>(`/data-sources/${selectedSource.id}/schema/tables/${encodeURIComponent(tableName)}`);
                              setSelectedSchemaTable(detail);
                            } catch (error) {
                              setNotice(error instanceof Error ? error.message : "无法读取表结构");
                            }
                          })()}
                        >
                          <strong>{tableName}</strong>
                          <span>{table.columns?.length || 0} 列 · {table.primary_key?.length ? "含主键" : "无主键"}</span>
                        </button>
                      );
                    })}
                  </div>
                  {selectedSchemaTable ? (
                    <div className="schema-table-detail">
                      <div className="detail-meta">
                        <span>主键：{selectedSchemaTable.primary_key?.join(" · ") || "无"}</span>
                        <span>外键：{selectedSchemaTable.foreign_keys?.length || 0}</span>
                        <span>索引：{selectedSchemaTable.indexes?.length || 0}</span>
                        <span>采样上限：{selectedSchemaTable.sample_limit || 100} 行</span>
                      </div>
                      {selectedSchemaTable.comment && <p className="detail-hint">表注释：{selectedSchemaTable.comment}</p>}
                      <table className="result-table">
                        <thead><tr><th>列名</th><th>类型</th><th>可为空</th><th>注释</th></tr></thead>
                        <tbody>{(selectedSchemaTable.columns || []).map((column) => <tr key={column.name}><td>{column.name}</td><td>{column.type}</td><td>{column.nullable ? "是" : "否"}</td><td>{column.comment || "—"}</td></tr>)}</tbody>
                      </table>
                      {selectedSchemaTable.foreign_keys?.length ? <div className="schema-foreign-keys"><strong>外键关系</strong>{selectedSchemaTable.foreign_keys.map((key, index) => <span key={index}>{(key.constrained_columns || []).join(", ")} → {key.referred_table || "?"}.{(key.referred_columns || []).join(", ")}</span>)}</div> : null}
                    </div>
                  ) : <p className="detail-hint">选择一张表查看列、主键和外键。</p>}
                </div>
              ) : <p className="detail-hint">尚无快照，请先同步 Schema。</p>}
              <form className="knowledge-search" onSubmit={(event) => void runSourceQuery(event)}>
                <label>只读查询试跑<textarea value={sourceQuery} onChange={(event) => setSourceQuery(event.target.value)} rows={4} aria-label="只读查询 SQL" /></label>
                <button className="primary-button" disabled={busy || selectedSource.status === "disabled" || !["analyst", "org_admin", "platform_admin"].includes(organization?.role || "")}>执行 Guard 查询</button>
              </form>
              {sourceQueryResult && <section className="detail-panel">
                <div className="detail-meta"><span>耗时：{sourceQueryResult.elapsed_ms} ms</span><span>行数：{sourceQueryResult.row_count} / {sourceQueryResult.max_rows}</span><span>表：{sourceQueryResult.tables.join(" · ")}</span><span>脱敏：{sourceQueryResult.redacted ? "已启用" : "未启用"}</span></div>
                <pre className="sql-preview">{sourceQueryResult.sql}</pre>
                <pre className="schema-preview">{JSON.stringify(sourceQueryResult.rows, null, 2)}</pre>
              </section>}
            </section>
          )}
        </DataView>
      );
    if (nav === "系统状态") return <SystemStatusPage details={systemDetails as SystemStatusData | null} showDeadLetters={Boolean(organization && ["org_admin", "platform_admin"].includes(organization.role))} failedTasks={failedTasks} onRetry={(id) => void retryDeadLetter(id)} />;
    if (nav === "知识库") return <KnowledgeBasePage filter={knowledgeFilter} setFilter={setKnowledgeFilter} page={knowledgePage} pageSize={knowledgePageSize} hasMore={knowledgeHasMore} setPage={setKnowledgePage} setPageSize={setKnowledgePageSize} knowledgeBases={knowledge} documents={documents} busy={busy} onCreate={(event) => void createKnowledge(event)} onUpload={uploadDocument} onAnalyze={(name) => { setQuestion(`${name}中的指标口径与当前供应链风险`); selectNav("分析会话"); }} onManage={(id) => void openKnowledge(id)} selected={selectedKnowledge} onCloseDetail={() => setSelectedKnowledge(null)} onToggleArchive={() => void toggleKnowledgeArchive()} onRequestDelete={() => setPendingKnowledgeDelete(selectedKnowledge)} onUpdate={(event) => void updateKnowledge(event)} query={knowledgeQuery} setQuery={setKnowledgeQuery} onSearch={(event) => void searchKnowledge(event)} citations={knowledgeCitations} role={organization?.role} onSource={(document) => { const full = documents.find((item) => item.id === document.id); if (full) void openDocumentSource(full); }} onRetry={(id) => void retryIngestion(id)} onCancel={(id) => void cancelIngestion(id)} onArchiveDocument={(document) => { const full = documents.find((item) => item.id === document.id); if (full) void toggleDocumentArchive(full); }} onDeleteDocument={(document) => { const full = documents.find((item) => item.id === document.id); if (full) void deleteDocument(full); }} onReplace={(document, file) => { const full = documents.find((item) => item.id === document.id); return full ? replaceDocument(full, file) : Promise.reject(new Error("文档不存在")); }} onMetadata={(document, metadata) => { const full = documents.find((item) => item.id === document.id); return full ? updateDocumentMetadata(full, metadata) : Promise.reject(new Error("文档不存在")); }} source={documentSource} onCloseSource={() => setDocumentSource(null)} />;
    if (nav === "__legacy_knowledge_markup__")
      return (
        <DataView
          kicker="KNOWLEDGE / CITATIONS"
          title="知识库"
          copy="维护指标口径、制造规则与可追溯引用。"
        >
          <div className="report-filters knowledge-filters"><input value={knowledgeFilter.name} onChange={(event) => { setKnowledgePage(1); setKnowledgeFilter({ ...knowledgeFilter, name: event.target.value }); }} placeholder="按知识库名称筛选" aria-label="按知识库名称筛选" /><select value={knowledgeFilter.status} onChange={(event) => { setKnowledgePage(1); setKnowledgeFilter({ ...knowledgeFilter, status: event.target.value }); }} aria-label="按知识库状态筛选"><option value="">全部状态</option><option value="active">启用</option><option value="archived">已归档</option></select></div>
          <form
            className="inline-form knowledge-create"
            onSubmit={createKnowledge}
          >
            <div>
              <label htmlFor="knowledge-name">新建知识库</label>
              <input
                id="knowledge-name"
                name="name"
                required
                placeholder="例如：供应链演示口径"
                aria-label="知识库名称"
              />
            </div>
            <div>
              <label htmlFor="knowledge-description">用途说明</label>
              <input
                id="knowledge-description"
                name="description"
                placeholder="指标定义、制度或制造规则"
                aria-label="知识库描述"
              />
            </div>
            <button className="primary-button">
              创建知识库 <span>+</span>
            </button>
          </form>
          {knowledge.length ? (
            <div className="knowledge-grid">
              {knowledge.map((k) => (
                <KnowledgeCard
                  key={k.id}
                  knowledgeBase={k}
                  documents={documents.filter(
                    (document) => document.knowledge_base_id === k.id,
                  )}
                  busy={busy}
                  onUpload={uploadDocument}
                  onAnalyze={() => {
                    setQuestion(`${k.name}中的指标口径与当前供应链风险`);
                    selectNav("分析会话");
                  }}
                  onManage={() => void openKnowledge(k.id)}
                />
              ))}
            </div>
          ) : (
            <Empty
              title="从第一套口径开始"
              copy="创建知识库后上传 PDF、Markdown 或 TXT 文档。"
            />
          )}
          <Pagination page={knowledgePage} pageSize={knowledgePageSize} total={(knowledgePage - 1) * knowledgePageSize + knowledge.length + (knowledgeHasMore ? 1 : 0)} onPageChange={setKnowledgePage} onPageSizeChange={(size) => { setKnowledgePageSize(size); setKnowledgePage(1); }} />
          {selectedKnowledge && (
            <section className="knowledge-detail">
              <div className="panel-heading">
                <div>
                  <p className="section-kicker">KNOWLEDGE / DETAIL</p>
                  <h3>{selectedKnowledge.name}</h3>
                  <p>{selectedKnowledge.description || "暂无用途说明"}</p>
                </div>
                <div className="row-actions">
                  <button className="secondary-button" onClick={() => void toggleKnowledgeArchive()}>{selectedKnowledge.is_archived ? "恢复知识库" : "归档知识库"}</button>
                  {selectedKnowledge.is_archived && documents.filter((document) => document.knowledge_base_id === selectedKnowledge.id && !document.is_archived).length === 0 && <button className="text-button danger-action" onClick={() => setPendingKnowledgeDelete(selectedKnowledge)}>删除知识库</button>}
                </div>
              </div>
              <form className="knowledge-edit-form" onSubmit={(event) => void updateKnowledge(event)}><label>知识库名称<input name="name" defaultValue={selectedKnowledge.name} required /></label><label>用途说明<input name="description" defaultValue={selectedKnowledge.description} /></label><button className="secondary-button">保存信息</button></form>
              <form
                className="knowledge-search"
                onSubmit={(event) => void searchKnowledge(event)}
              >
                <input
                  value={knowledgeQuery}
                  onChange={(event) => setKnowledgeQuery(event.target.value)}
                  placeholder="预览检索，例如：生产达成率口径"
                  aria-label="知识库检索预览"
                />
                <button className="primary-button">检索引用</button>
              </form>
              {knowledgeCitations.length ? (
                <div className="citation-list">
                  {knowledgeCitations.map((citation, index) => (
                    <article
                      className="citation-item"
                      key={`${citation.document_id}-${index}`}
                    >
                      <strong>{citation.document_name || "文档片段"}</strong>
                      <span>
                        相似度{" "}
                        {typeof citation.score === "number"
                          ? citation.score.toFixed(3)
                          : "—"}
                      </span>
                      <p>{citation.text || "暂无片段文本"}</p>
                      <small>
                        {citation.location
                          ? JSON.stringify(citation.location)
                          : "未提供位置"}
                      </small>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="detail-hint">
                  检索结果会显示文档、片段、相似度和引用位置。
                </p>
              )}
              {false && <div className="knowledge-task-list">
                {documents
                  .filter(
                    (document) =>
                      document.knowledge_base_id === selectedKnowledge?.id,
                  )
                  .map((document) => (
                    <div className="knowledge-task-row" key={document.id}>
                      <span>{document.filename}</span>
                      <span className={`status-dot-label ${document.status}`}>
                        {document.is_archived ? "archived" : document.status}
                      </span>
                      <span className="document-meta">{document.category || "other"}{document.embedding_model ? ` · ${document.embedding_model} · ${document.embedding_dimension || "?"}d` : " · 未向量化"}</span>
                      {document.error_message && <small className="export-error">{document.error_message}</small>}
                      {document.status === "completed" && <button className="text-button" onClick={() => void openDocumentSource(document)}>查看原文</button>}
                      {document.ingestion_task_id &&
                        document.status === "failed" && (
                          <button
                            className="text-button"
                            onClick={() =>
                              void retryIngestion(document.ingestion_task_id!)
                            }
                          >
                            重试摄取
                          </button>
                        )}
                      {document.ingestion_task_id && ["queued", "processing"].includes(document.status) && <button className="text-button" onClick={() => void cancelIngestion(document.ingestion_task_id!)}>取消摄取</button>}
                      {organization && ["org_admin", "platform_admin"].includes(organization.role) && <>
                        <button className="text-button" onClick={() => void toggleDocumentArchive(document)}>{document.is_archived ? "恢复" : "归档"}</button>
                        {!["queued", "processing"].includes(document.status) && <button className="text-button" onClick={() => void deleteDocument(document)}>删除</button>}
                      </>}
                    </div>
                  ))}
              </div>}
              <DocumentTaskList
                documents={documents}
                knowledgeBaseId={selectedKnowledge?.id || ""}
                organizationRole={organization?.role}
                onSource={(document) => { const full = documents.find((item) => item.id === document.id); if (full) void openDocumentSource(full); }}
                onRetry={(taskId) => void retryIngestion(taskId)}
                onCancel={(taskId) => void cancelIngestion(taskId)}
                onArchive={(document) => { const full = documents.find((item) => item.id === document.id); if (full) void toggleDocumentArchive(full); }}
                onDelete={(document) => { const full = documents.find((item) => item.id === document.id); if (full) void deleteDocument(full); }}
                onReplace={(document, file) => { const full = documents.find((item) => item.id === document.id); return full ? replaceDocument(full, file) : Promise.reject(new Error("文档不存在")); }}
                onMetadata={(document, metadata) => { const full = documents.find((item) => item.id === document.id); return full ? updateDocumentMetadata(full, metadata) : Promise.reject(new Error("文档不存在")); }}
              />
              {documentSource && <section className="detail-panel document-source-panel"><div className="panel-heading"><div><p className="section-kicker">DOCUMENT / SOURCE</p><h3>{documentSource.filename} · v{documentSource.version}</h3><p>{documentSource.category || "other"} · {documentSource.chunks.length} 个分块</p></div><button className="text-button" onClick={() => setDocumentSource(null)}>关闭</button></div><div className="citation-list">{documentSource.chunks.map((chunk) => <article className="citation-item" key={chunk.id}><strong>#{chunk.ordinal + 1}</strong><p>{chunk.text}</p><small>{chunk.location ? JSON.stringify(chunk.location) : "未提供位置"}</small></article>)}</div></section>}
            </section>
          )}
        </DataView>
      );
    if (nav === "报告中心") return <ReportsPage reports={reports} selectedReport={selectedReport} exports={reportExports} sources={sources} knowledgeBases={knowledge} filters={reportFilter} setFilters={setReportFilter} onOpen={(id) => void openReport(id)} onClose={() => setSelectedReport(null)} onDownload={(id) => void downloadReport(id)} onRetryExport={(reportId, exportId) => void retryReportExport(reportId, exportId)} />;
    if (nav === "组织与审计") return <OrganizationAuditPage members={members} invitations={invitations} auditEvents={auditEvents} organization={organization} auditFilter={auditFilter} auditRunId={auditRunId} setAuditFilter={setAuditFilter} setAuditRunId={setAuditRunId} onInvite={inviteMember} onRoleChange={updateMemberRole} onToggle={toggleMember} onResend={resendInvitation} onRevoke={revokeInvitation} selectedAudit={selectedAudit} setSelectedAudit={setSelectedAudit} invitationLink={invitationLink} onDismissInvitationLink={() => setInvitationLink(null)} />;
    if (nav === "分析会话") return <AnalysisSessionPage conversationId={analysisConversationId} messages={analysisMessages} onClearContext={() => setAnalysisMessages([])} onNewConversation={startNewAnalysisConversation} question={question} setQuestion={setQuestion} events={events} result={analysisResult} busy={busy} onSubmit={analyze} onDownloadReport={downloadReport} sources={sources} knowledgeBases={knowledge} sourceId={analysisSourceId} knowledgeBaseId={analysisKnowledgeBaseId} setSourceId={setAnalysisSourceId} setKnowledgeBaseId={setAnalysisKnowledgeBaseId} runs={analyses} page={analysisPage} pageSize={analysisPageSize} hasMore={analysisHasMore} setPage={setAnalysisPage} setPageSize={setAnalysisPageSize} onOpenRun={(id) => void openAnalysis(id)} selectedRun={selectedAnalysis} steps={analysisSteps} onCloseRun={() => setSelectedAnalysis(null)} onCancelRun={(id) => void cancelAnalysis(id)} onRetryRun={(id) => void retryAnalysis(id)} />;
    return <OperationsOverviewPage dashboard={dashboard} dimensions={dashboardDimensions} filters={dashboardFilters} refreshing={refreshingDashboard} config={dashboardConfig} canConfigure={organization ? ["org_admin", "platform_admin"].includes(organization.role) : false} onChangeFilters={setDashboardFilters} onRefresh={() => void refreshDashboard()} onSaveConfig={(seconds) => void saveDashboardConfig(seconds)} onOpenAnalysis={(nextQuestion) => { if (nextQuestion) setQuestion(nextQuestion); selectNav("分析会话"); }} chartRef={chartRef} factoryChartRef={factoryChartRef} supplierChartRef={supplierChartRef} question={question} setQuestion={setQuestion} events={events} result={analysisResult} busy={busy} onSubmit={analyze} onDownloadReport={downloadReport} sources={sources} knowledgeBases={knowledge} sourceId={analysisSourceId} knowledgeBaseId={analysisKnowledgeBaseId} setSourceId={setAnalysisSourceId} setKnowledgeBaseId={setAnalysisKnowledgeBaseId} />;
  }
  return <AppShell nav={nav} items={visibleNavItems} organizationName={organization?.name} systemStatus={systemStatus} busy={busy} onNavigate={selectNav} onRefresh={() => void load()} onLogout={() => void logout()} topbarActions={<div className="profile-wrap" ref={profileMenuRef}>
              <button
                className="avatar avatar-button"
                onClick={() => setProfileOpen((open) => !open)}
                aria-expanded={profileOpen}
                aria-label="打开账户菜单"
              >
                管
              </button>
              {profileOpen && (
                <div className="profile-menu">
                  <strong>{loginEmail || "当前账户"}</strong>
                  <span>{organization?.name || "当前组织"} · {organization?.role || "—"}</span>
                  {organizations.length > 1 && (
                    <div className="organization-menu">
                      {organizations.map((item) => (
                        <button key={item.id} disabled={item.id === organization?.id || busy} onClick={() => void switchOrganization(item.id)}>
                          {item.name} · {item.role}{item.id === organization?.id ? "（当前）" : ""}
                        </button>
                      ))}
                    </div>
                  )}
                  {canManageOrganization && <button
                    onClick={() => {
                      setProfileOpen(false);
                      selectNav("项目管理");
                    }}
                  >项目设置</button>}
                  <button onClick={() => void logout()}>退出工作区</button>
                </div>
              )}
            </div>}>
        {notice && (
          <div className="notice" role="status">
            {notice}
          </div>
        )}
        {accessError && <section className="access-error-panel" role="alert"><strong>{accessError === "forbidden" ? "无权限" : accessError === "not-found" ? "资源不存在" : "登录已过期"}</strong><p>{accessError === "forbidden" ? "当前角色不能执行此操作，请联系组织管理员。" : accessError === "not-found" ? "资源可能已删除、归档或属于其他组织。" : "请重新登录后继续。"}</p>{accessError === "expired" && <button className="primary-button" onClick={() => { setToken(""); setRefresh(""); localStorage.removeItem("supplymind_token"); localStorage.removeItem("supplymind_refresh"); }}>返回登录</button>}</section>}
        {page()}
        {pendingKnowledgeDelete && (
          <div className="modal-backdrop" role="presentation" onClick={() => setPendingKnowledgeDelete(null)}>
            <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="knowledge-delete-title" onClick={(event) => event.stopPropagation()}>
              <span className="section-kicker">KNOWLEDGE BASE</span>
              <h3 id="knowledge-delete-title">删除这个空白知识库？</h3>
              <p>“{pendingKnowledgeDelete.name}”没有活动文档。确认后将立即从当前列表移除；已有文档的知识库只能归档，不能删除。</p>
              <div className="confirm-actions">
                <button className="secondary-button" onClick={() => setPendingKnowledgeDelete(null)}>取消</button>
                <button className="primary-button danger-button" onClick={() => void deleteKnowledge()}>确认删除</button>
              </div>
            </section>
          </div>
        )}
    </AppShell>;
}
