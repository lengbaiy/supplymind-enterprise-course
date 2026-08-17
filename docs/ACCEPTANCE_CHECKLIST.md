# 企业课程案例验收清单

## 环境

- [ ] 16 GB 内存 Docker Desktop 可启动 Compose 核心服务。
- [ ] API `/api/v1/health/live` 返回 `ok`，`/api/v1/health/ready` 返回 `ready`。
- [ ] 前端首页可打开，MinIO 控制台可登录。
- [ ] `pytest`、Ruff、前端 build、`docker compose config` 和 `helm lint` 通过。

## 功能

- [ ] 管理员可登录、刷新令牌、退出并管理成员角色。
- [ ] 组织管理员可创建 MySQL/PostgreSQL 数据源并执行连接测试、Schema 同步。
- [ ] 只读账号、主机/CIDR、Schema/表白名单和 SQL AST 规则均生效。
- [ ] 文档上传后完成分块、Embedding，检索返回引用位置和分数。
- [ ] 分析运行产生八阶段轨迹、受限 SQL、结构化结果、ECharts 规格和报告。
- [ ] PDF 下载校验组织和角色，另一个组织收到 `404`。
- [ ] 大屏显示五类预置指标，并支持时间、工厂、产品线筛选。

## 安全与可靠性

- [ ] JWT 过期、刷新令牌重放、OIDC state 重放均被拒绝。
- [ ] 多语句、写操作、系统表、危险函数、越权表和超配额请求均被拒绝。
- [ ] Celery 任务重复投递不会产生重复文档块或报告文件。
- [ ] API、Worker、模型、MCP、SQL 和任务错误可在审计或日志中追踪。
- [ ] Prometheus 可抓取 `/api/v1/metrics`，异常状态包含 HTTP 状态标签。

## 核心 E2E

组织管理员接入演示库后，分析师提问“近 30 天各工厂生产达成率与缺料风险”。验收记录必须包含运行 ID、SQL 草案、Guard 结果、查询行数、图表、RAG 引用、Markdown/PDF 报告和审计事件；其他组织成员无法读取其中任何资源。
