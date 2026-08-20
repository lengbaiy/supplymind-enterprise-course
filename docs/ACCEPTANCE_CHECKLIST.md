# 企业课程案例验收清单

## 环境

- [x] 16 GB 内存 Docker Desktop 可启动 Compose 核心服务。
- [x] API `/api/v1/health/live` 返回 `ok`，`/api/v1/health/ready` 返回 `ready`。
- [x] 前端首页可打开，MinIO 控制台可登录。
- [x] `pytest`、Ruff、前端 build、`docker compose config` 和容器化 `helm lint` 通过。

测试模式约定：后端单元/集成测试显式使用 `SUPPLYMIND_INGESTION_MODE=eager`；Compose 验收必须使用 `broker` 并检查 Worker 将任务推进到 `completed`。

## 功能

- [ ] 管理员可登录、刷新令牌、退出并管理成员角色。
- [ ] 组织管理员可创建 MySQL/PostgreSQL 数据源并执行连接测试、Schema 同步。
- [ ] 只读账号、主机/CIDR、Schema/表白名单和 SQL AST 规则均生效。
- [ ] 文档上传后完成分块、Embedding，检索返回引用位置和分数。
- [x] 分析运行产生八阶段轨迹、受限 SQL、结构化结果、ECharts 规格和报告。
- [ ] PDF 下载校验组织和角色，另一个组织收到 `404`。
- [ ] 大屏显示五类预置指标，并支持时间、工厂、产品线筛选。
- [ ] 大屏刷新返回任务 ID，任务详情能显示 queued/running/completed/failed、失败原因和最近完成时间。
- [ ] 大屏异常项可带入分析模板和工厂上下文。

## 安全与可靠性

- [ ] JWT 过期、刷新令牌重放、OIDC state 重放均被拒绝。
- [ ] 多语句、写操作、系统表、危险函数、越权表和超配额请求均被拒绝。
- [ ] Celery 任务重复投递不会产生重复文档块或报告文件。
- [ ] API、Worker、模型、MCP、SQL 和任务错误可在审计或日志中追踪。
- [x] Prometheus 可抓取 `/api/v1/metrics`，异常状态包含 HTTP 状态标签；API 响应带 `X-Trace-Id`。
- [x] 系统状态显示 Worker 节点数、活动任务数、失败/死信任务、最近错误、MCP 和数据源状态。
- [x] 审计支持动作、资源、操作者、时间区间、分页和运行 ID筛选，详情不泄露密钥，并提供单条详情接口。
- [x] SSE 断线后通过 `/analyses/{id}/events` 恢复运行轨迹；恢复步骤、SQL 与结果均按组织隔离返回。

## 当前统一验收记录

- [x] Docker Compose、Alembic `0020_document_metric_metadata`、健康检查。
- [x] 容器内 pytest `23 passed`。
- [x] 前端生产构建通过。
- [x] 无效登录返回 `401`，只读用户访问成员管理返回 `403`。
- [x] 大屏组织级配置管理员可写，分析师拒绝。
- [x] 文档指标元数据 API、重复文件标记和前端编辑入口。
- [x] Playwright 浏览器主路径：深链登录、桌面导航、移动端“更多”导航和只读成员受限深链已验证。
- [x] 本地 OIDC mock Provider 授权码回调、ID Token 校验和令牌签发已实测；Compose 覆盖使用 `host.docker.internal:8081` 供 Windows Docker 与浏览器共同访问。

## 核心 E2E

组织管理员接入演示库后，分析师提问“近 30 天各工厂生产达成率与缺料风险”。验收记录必须包含运行 ID、SQL 草案、Guard 结果、查询行数、图表、RAG 引用、Markdown/PDF 报告和审计事件；其他组织成员无法读取其中任何资源。

该路径已使用真实 Chat/Embedding Provider 在 2026-08-20 完成，详细证据见 `docs/FINAL_ACCEPTANCE.md`。
