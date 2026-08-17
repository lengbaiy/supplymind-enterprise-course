# SupplyMind 课程交付包

## 课程目标

学员从空环境启动 SupplyMind，完成一个多租户、只读、可审计的供应链自然语言分析闭环。课程强调边界设计和可验证的工程实现，不把演示代码包装成生产 SLA。

## 章节与产出

| 章节 | 学员完成内容 | 验收产出 |
| --- | --- | --- |
| 1. 领域与架构 | 组织、数据源、分析运行和报告模型 | 领域模型图与 API 清单 |
| 2. 身份与租户 | JWT、刷新令牌、角色矩阵、RLS | 越权测试通过 |
| 3. 数据接入 | 只读账号、白名单、Schema 快照 | MySQL/PostgreSQL 连接测试 |
| 4. 知识库与 RAG | 文档解析、分块、Embedding、引用 | 检索结果含文档、分数、位置 |
| 5. MCP 与 Agent | 五个工具契约和八阶段状态机 | SSE 展示每个阶段及失败原因 |
| 6. 异步与报告 | Celery 幂等任务、Markdown/PDF、下载权限 | 报告导出和审计记录 |
| 7. 控制台与大屏 | 分析会话、引用、图表、预置指标卡 | 浏览器完成核心流程 |
| 8. 交付与运维 | Compose、Prometheus、Helm、CI | 健康检查、回滚和验收清单 |

## 讲师执行顺序

1. 课前准备：安装 Docker Desktop、Git、Node 22、Python 3.12 和 Helm；复制 `.env.example` 为 `.env`，填入模型配置。
2. 启动基线：执行 `docker compose up -d --build`，确认 API、Worker、前端、PostgreSQL、Redis、MinIO 健康。
3. 分组开发：每组按章节提交一个独立 commit，提交信息使用 `feat: sXX ...`，便于回滚和对照起止代码。
4. 课堂验收：使用演示库提问“近 30 天各工厂生产达成率与缺料风险”，检查 SQL、图表、引用、报告和审计。
5. 结课答辩：学员解释租户边界、SQL Guard 拒绝路径、Celery 重试策略和 Helm 外部依赖接入方式。

## 作业与评分

- 作业 1（20%）：为一个新指标补充知识库口径和检索引用。
- 作业 2（25%）：增加一个只读业务问题，补充 SQL Guard 和集成测试。
- 作业 3（25%）：实现一个 MCP 工具的输入/输出 Schema，并记录审计事件。
- 项目答辩（30%）：完成核心 E2E，说明失败、超时、越权和回滚处理。

## 学员复现命令

```powershell
Copy-Item .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build api worker frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api pytest -q
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api ruff check app scripts tests
```

前端地址为 `http://localhost:5173`，API 文档为 `http://localhost:8000/docs`，Prometheus 指标为 `http://localhost:8000/api/v1/metrics`。
