# SupplyMind 最终验收记录

更新时间：2026-08-20

## 原型与前端

- 已交付可点击的现代工业运营台原型：登录/OIDC、运营总览、项目管理、数据源、知识库、分析会话、报告、大屏配置、组织审计和系统状态。
- 桌面端使用完整侧边导航；移动端将运营总览、项目、分析、数据源、知识库固定为高频入口，其余企业功能收纳到“更多”。
- 页面使用真实 URL、组织/角色可见性规则、深链权限重定向、加载/空/错误/无权限状态与 Trace ID 错误提示。

## 真实业务闭环

- 数据源：PostgreSQL/MySQL 连接、Schema 快照、白名单与只读 Guard 查询。
- 知识库：真实 Embedding、分块检索、引用位置、版本与摄取任务生命周期。
- 分析：真实 Chat/Embedding Provider、SSE、SQL 草案与 Guard、结果行、洞察、ECharts 规格、引用和报告。
- 2026-08-20 实测问题“近30天各工厂生产达成率与缺料风险”：返回 3 个工厂聚合行、4 条引用、柱状图规格和报告 ID；SQL 仅访问当前数据源白名单表。
- 报告、审计、系统状态与大屏均保持多租户边界；跨组织资源继续按 `404` 处理。

## 工程与验证

- 前端：Vite + React + TypeScript、React Router、React Query、内部设计系统、Vitest、Testing Library、MSW 和 Playwright。
- 后端：Docker Compose、pytest、Ruff、Alembic、Helm lint/template。
- 已验证：后端 25 项测试、前端单元测试、前端生产构建、Playwright 主路径、OIDC 回调、SSE 恢复与真实模型端到端分析。

## 运行前安全事项

- `.env` 中的模型服务密钥不得提交；完成本地验收后应轮换已使用的服务密钥。
- 生产部署必须配置独立的 OIDC Issuer、密钥管理、对象存储凭据与 Kubernetes Context；本地 `host.docker.internal` 仅用于 Windows Docker 的 OIDC mock 验证。
