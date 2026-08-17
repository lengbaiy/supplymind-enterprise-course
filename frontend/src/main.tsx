import { FormEvent, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
type Card = { label: string; value: string; change: string };
type Dashboard = { cards: Card[]; trend: { month: string; rate: number }[] };

function App() {
  const [token, setToken] = useState(localStorage.getItem("supplymind_token") || "");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dataSourceId, setDataSourceId] = useState("");
  const [question, setQuestion] = useState("近30天各工厂生产达成率与缺料风险");
  const [events, setEvents] = useState<string[]>([]);
  const chartRef = useRef<HTMLDivElement>(null);

  const headers: HeadersInit = token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : {};
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/dashboards/supply-chain`, { headers }).then(r => r.json()).then(setDashboard).catch(() => setDashboard(null));
    fetch(`${API}/data-sources`, { headers })
      .then(r => r.json())
      .then((sources: { id: string }[]) => setDataSourceId(sources[0]?.id || ""));
  }, [token]);
  useEffect(() => {
    if (!dashboard || !chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    chart.setOption({ tooltip: {}, xAxis: { type: "category", data: dashboard.trend.map(x => x.month) }, yAxis: { type: "value", min: 80, max: 100 }, series: [{ type: "line", data: dashboard.trend.map(x => x.rate), smooth: true, areaStyle: {} }] });
    return () => chart.dispose();
  }, [dashboard]);

  async function login(event: FormEvent) {
    event.preventDefault();
    const response = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "admin@demo.local", password: "ChangeMe123!", organization_slug: "demo-factory" }) });
    const body = await response.json();
    if (!response.ok) return setEvents([body.detail || "登录失败"]);
    localStorage.setItem("supplymind_token", body.access_token); setToken(body.access_token);
  }

  async function analyze(event: FormEvent) {
    event.preventDefault();
    if (!dataSourceId) return setEvents(["当前组织没有可用数据源。请由组织管理员创建数据源。"]);
    setEvents(["正在启动多 Agent 分析..."]);
    const response = await fetch(`${API}/analyses/stream`, { method: "POST", headers, body: JSON.stringify({ data_source_id: dataSourceId, question }) });
    if (!response.ok) return setEvents(["分析请求被拒绝，请检查权限或数据源配置。"]);
    const text = await response.text();
    const steps = text.split("\n\n").flatMap(block => {
      const eventName = block.match(/^event: (.+)$/m)?.[1];
      const data = block.match(/^data: (.+)$/m)?.[1];
      return eventName && data ? [`${eventName}: ${JSON.parse(data).message || "已完成"}`] : [];
    });
    setEvents(steps);
  }

  if (!token) return <main className="login"><section><p className="eyebrow">SUPPLYMIND / 教学环境</p><h1>制造供应链<br/>数据分析助手</h1><p>安全的多 Agent 数据洞察、报告与运营大屏。</p><form onSubmit={login}><button>使用演示组织登录</button></form><small>demo-factory · admin@demo.local</small></section></main>;
  return <main className="shell"><aside><div className="brand">Supply<span>Mind</span></div><nav><a className="active">运营总览</a><a>分析会话</a><a>数据源</a><a>知识库</a><a>报告中心</a><a>组织与审计</a></nav><button className="logout" onClick={() => { localStorage.removeItem("supplymind_token"); setToken(""); }}>退出</button></aside><section className="content"><header><div><p className="eyebrow">示范制造集团 / 供应链运营</p><h2>运营态势总览</h2></div><button className="secondary">刷新数据</button></header><div className="cards">{dashboard?.cards.map(card => <article key={card.label}><p>{card.label}</p><strong>{card.value}</strong><small>{card.change} 较上期</small></article>) || <p>正在连接平台服务...</p>}</div><section className="grid"><article className="panel chart"><h3>生产达成率趋势</h3><div ref={chartRef} className="chart-canvas" /></article><article className="panel alert"><h3>待处置风险</h3><p><b>控制器缺料</b><br/>成都工厂库存低于安全库存 64%</p><p><b>生产达成偏低</b><br/>成都工厂较目标低 7.4%</p></article></section><section className="panel analyst"><div><p className="eyebrow">分析助手</p><h3>提出一个供应链问题</h3></div><form onSubmit={analyze}><input value={question} onChange={e => setQuestion(e.target.value)} /><button>开始分析</button></form>{events.map((item, index) => <p className="notice" key={index}>{item}</p>)}</section></section></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
