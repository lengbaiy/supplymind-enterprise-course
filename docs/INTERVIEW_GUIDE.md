# 简历与面试要点

## 简历项目描述

SupplyMind 是一个基于 FastAPI、React、PostgreSQL/pgvector、Celery 和 Redis 的多租户供应链数据分析平台。项目实现 JWT/OIDC、PostgreSQL RLS、只读数据源、SQL AST Guard、RAG/MCP、八阶段 Agent 追踪、Markdown/PDF 报告、Prometheus 指标和 Helm 部署。

## 高频问题

**为什么采用模块化单体？**

首期把领域边界和接口固定在一个部署单元内，降低分布式事务与本地教学成本；Worker、API、前端仍可独立扩容，后续按真实瓶颈拆分。

**如何防止跨租户访问？**

请求从 JWT/OIDC 解析组织上下文，服务层强制 `tenant_id` 过滤，PostgreSQL RLS 通过事务级配置二次限制；缺失组织上下文直接拒绝。

**为什么不能只靠 Prompt 防止 SQL 注入？**

模型输出不可信，所有 SQL 必须经过方言感知 AST、对象白名单、危险函数、超时和成本策略；不通过时最多重写两次，最终失败可审计。

**Celery 如何保证幂等？**

任务以业务对象和版本生成幂等键，状态机记录 queued/processing/completed/failed，重复投递复用已有任务，失败使用退避重试并保留错误原因。

**RAG 如何让结论可追溯？**

每个检索结果保存文档、chunk、分数和位置；Insight/Report 阶段只引用带来源的片段，SSE 和报告同时返回引用。
