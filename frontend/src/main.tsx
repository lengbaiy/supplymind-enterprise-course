import { FormEvent, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
type Card = { label: string; value: string; change: string };
type Dashboard = { cards: Card[]; trend: { month: string; rate: number }[] };
const navItems = ["运营总览", "分析会话", "数据源", "知识库", "报告中心", "组织与审计"];

function App() {
  const [token, setToken] = useState(localStorage.getItem("supplymind_token") || "");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dataSourceId, setDataSourceId] = useState("");
  const [question, setQuestion] = useState("近30天各工厂生产达成率与缺料风险");
  const [events, setEvents] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [activeNav, setActiveNav] = useState("运营总览");
  const chartRef = useRef<HTMLDivElement>(null);
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : {};

  async function loadWorkspace() {
    if (!token) return;
    setRefreshing(true);
    try {
      const [dashboardResponse, sourcesResponse] = await Promise.all([fetch(`${API}/dashboards/supply-chain`, { headers }), fetch(`${API}/data-sources`, { headers })]);
      if (!dashboardResponse.ok || !sourcesResponse.ok) throw new Error("服务暂时不可用");
      setDashboard(await dashboardResponse.json());
      const sources = (await sourcesResponse.json()) as { id: string }[];
      setDataSourceId(sources[0]?.id || "");
    } catch (error) { setEvents([error instanceof Error ? error.message : "无法读取运营数据"]); }
    finally { setRefreshing(false); }
  }
  useEffect(() => { void loadWorkspace(); }, [token]);
  useEffect(() => {
    if (!dashboard || !chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    chart.setOption({ animationDuration: 450, grid: { left: 12, right: 12, top: 20, bottom: 18, containLabel: true }, tooltip: { trigger: "axis", backgroundColor: "#14352c", borderWidth: 0, textStyle: { color: "#fff" } }, xAxis: { type: "category", boundaryGap: false, data: dashboard.trend.map((x) => x.month), axisLine: { lineStyle: { color: "#d9e5df" } }, axisLabel: { color: "#73847c" } }, yAxis: { type: "value", min: 80, max: 100, splitLine: { lineStyle: { color: "#edf2ef" } }, axisLabel: { color: "#73847c", formatter: "{value}%" } }, series: [{ type: "line", data: dashboard.trend.map((x) => x.rate), smooth: 0.25, symbol: "circle", symbolSize: 7, lineStyle: { width: 3, color: "#15966d" }, itemStyle: { color: "#15966d", borderColor: "#fff", borderWidth: 2 }, areaStyle: { color: "rgba(21,150,109,0.10)" } }] });
    const resize = () => chart.resize(); window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); chart.dispose(); };
  }, [dashboard]);
  async function login(event: FormEvent) {
    event.preventDefault(); setLoginError("");
    const response = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "admin@demo.local", password: "ChangeMe123!", organization_slug: "demo-factory" }) });
    const body = await response.json();
    if (!response.ok) return setLoginError(body.detail || "登录失败，请稍后重试");
    localStorage.setItem("supplymind_token", body.access_token); setToken(body.access_token);
  }
  async function analyze(event: FormEvent) {
    event.preventDefault();
    if (!dataSourceId) return setEvents(["当前组织没有可用数据源，请由组织管理员先完成接入。"]);
    setLoading(true); setEvents(["已排队，正在读取指标口径和数据结构..."]);
    try {
      const response = await fetch(`${API}/analyses/stream`, { method: "POST", headers, body: JSON.stringify({ data_source_id: dataSourceId, question }) });
      if (!response.ok) throw new Error("分析请求被拒绝，请检查模型配置或数据源权限。");
      const text = await response.text();
      const steps = text.split("\n\n").flatMap((block) => { const eventName = block.match(/^event: (.+)$/m)?.[1]; const data = block.match(/^data: (.+)$/m)?.[1]; return eventName && data ? [`${eventName} · ${JSON.parse(data).message || "已完成"}`] : []; });
      setEvents(steps.length ? steps : ["分析已完成，可在分析会话中查看详情。"]);
    } catch (error) { setEvents([error instanceof Error ? error.message : "分析失败，请稍后重试"]); }
    finally { setLoading(false); }
  }
  function logout() { localStorage.removeItem("supplymind_token"); setToken(""); setDashboard(null); }
  if (!token) return <main className="login-page"><section className="login-panel"><div className="wordmark"><span className="wordmark-mark">S</span><span>SupplyMind</span></div><p className="section-kicker">MANUFACTURING OPERATIONS / 01</p><h1>把供应链的<br /><em>下一步</em>看清楚。</h1><p className="login-copy">面向制造团队的安全数据分析工作台。连接数据源，追踪异常，并让每个结论都有依据。</p><form onSubmit={login} className="login-form"><button className="primary-button" type="submit">进入示范工作区 <span aria-hidden="true">→</span></button>{loginError && <p className="form-error" role="alert">{loginError}</p>}</form><div className="login-meta"><span>示范制造集团</span><span>admin@demo.local</span></div></section><div className="login-aside"><div className="aside-grid" /><div className="aside-caption"><span>LIVE SYSTEM</span><strong>供应链运营<br />数据分析助手</strong><small>实时监测 · 安全查询 · 可追溯洞察</small></div></div></main>;
  return <main className="app-shell"><aside className="sidebar"><div className="sidebar-top"><div className="wordmark"><span className="wordmark-mark">S</span><span>SupplyMind</span></div><span className="environment-badge">DEMO</span></div><div className="workspace-switch"><span className="workspace-dot" /><span><small>当前组织</small><strong>示范制造集团</strong></span><span className="chevron">⌄</span></div><nav aria-label="主导航">{navItems.map((label, index) => <button key={label} className={`nav-item ${activeNav === label ? "active" : ""}`} onClick={() => setActiveNav(label)}><span>{label}</span><small>{index ? `0${index}` : "TODAY"}</small></button>)}</nav><div className="sidebar-footer"><div className="status-line"><span className="status-dot" />所有系统正常</div><button className="logout-button" onClick={logout}>退出工作区</button></div></aside><section className="workspace"><header className="topbar"><div><p className="section-kicker">{activeNav === "运营总览" ? "OPERATIONS / OVERVIEW" : `WORKSPACE / ${activeNav.toUpperCase()}`}</p><h2>{activeNav}</h2></div><div className="topbar-actions"><span className="last-sync">最后同步 <strong>刚刚</strong></span><button className="icon-button" onClick={() => void loadWorkspace()} disabled={refreshing} aria-label="刷新数据" title="刷新数据">↻</button><div className="avatar">管</div></div></header>{activeNav !== "运营总览" ? <section className="placeholder-view"><span className="placeholder-index">0{navItems.indexOf(activeNav)}</span><h3>{activeNav}正在准备中</h3><p>该模块将接入组织级数据和权限控制，当前可先从运营总览发起分析。</p><button className="secondary-button" onClick={() => setActiveNav("运营总览")}>返回运营总览</button></section> : <><section className="hero-row"><div><p className="section-kicker">MONDAY · 08:42 CST</p><h1>早上好，管理员。</h1><p className="hero-copy">这里是今天的供应链运行快照。优先关注下方标记的两项风险。</p></div><div className="hero-stamp"><span>数据覆盖</span><strong>4</strong><small>个运营指标</small></div></section><section className="metric-grid" aria-label="关键指标">{dashboard?.cards.map((card) => <article className="metric" key={card.label}><div className="metric-label"><span className="metric-pip" />{card.label}</div><strong>{card.value}</strong><span className="metric-change">{card.change}<small>较上期</small></span></article>) || Array.from({ length: 4 }, (_, index) => <article className="metric skeleton" key={index}><span /><span /><span /></article>)}</section><section className="main-grid"><article className="panel chart-panel"><div className="panel-heading"><div><p className="section-kicker">PERFORMANCE / 30 DAYS</p><h3>生产达成率趋势</h3></div><span className="panel-meta">目标线 90%</span></div><div ref={chartRef} className="chart-canvas" /></article><article className="panel risk-panel"><div className="panel-heading"><div><p className="section-kicker">ATTENTION REQUIRED</p><h3>待处置风险</h3></div><span className="risk-count">02</span></div><div className="risk-list"><div className="risk-item"><span className="risk-mark high">!</span><div><strong>控制器缺料</strong><p>成都工厂库存低于安全库存 64%</p></div><span className="risk-arrow">→</span></div><div className="risk-item"><span className="risk-mark medium">△</span><div><strong>生产达成偏低</strong><p>成都工厂较目标低 7.4%</p></div><span className="risk-arrow">→</span></div></div><button className="text-button">查看全部风险 <span>→</span></button></article></section><section className="analyst-panel"><div className="analyst-intro"><div className="analyst-icon">✦</div><div><p className="section-kicker">ANALYSIS ASSISTANT</p><h3>问一个供应链问题</h3><p>系统会检索指标口径，生成受限 SQL，并保留每一步依据。</p></div></div><form onSubmit={analyze} className="analyst-form"><input value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="供应链问题" /><button className="primary-button" type="submit" disabled={loading}>{loading ? "分析中..." : "开始分析"}<span aria-hidden="true">↗</span></button></form>{events.length > 0 && <div className="event-log" aria-live="polite">{events.map((item, index) => <p key={`${item}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span>{item}</p>)}</div>}</section></>}</section></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
