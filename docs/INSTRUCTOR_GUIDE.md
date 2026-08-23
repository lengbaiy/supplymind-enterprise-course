# SupplyMind 讲师手册

本手册用于把 SupplyMind 作为企业级开发课程交付。讲师应强调真实工程边界，而不是把系统包装成生产 SLA。

## 课程定位

SupplyMind 适合中高级学员学习以下能力：

- 多租户 SaaS 后端边界。
- 只读企业数据接入和 SQL 安全。
- RAG、MCP 与 Agent 的工程化落地。
- 异步任务、幂等、失败恢复和审计。
- React 企业控制台和浏览器回归测试。
- Docker Compose、Helm、CI、安全扫描和回滚。

不适合把它讲成：

- 通用 BI 平台。
- 大规模生产压测项目。
- 任意数据库写入平台。
- 完整 DB-GPT 复刻。

## 推荐课时

| 阶段 | 时长 | 讲师重点 | 学员产出 |
| --- | ---: | --- | --- |
| 课前准备 | 1 小时 | 环境、账号、模型配置、安全约束 | 本地服务健康 |
| L01-L02 | 4 小时 | 架构、身份、组织和权限 | 架构图、权限测试 |
| L03-L04 | 6 小时 | 数据源安全、知识库、RAG | SQL Guard 测试、指标文档 |
| L05-L06 | 6 小时 | MCP、Agent、Celery、失败恢复 | 工具契约测试、故障记录 |
| L07 | 4 小时 | 前端状态、权限态、E2E | 页面改动和浏览器回归 |
| L08 | 4 小时 | CI、Helm、验收、回滚 | 验收报告和发布说明 |
| 答辩 | 2 小时 | 工程取舍和风险意识 | 演示和问答 |

## 课前检查

讲师在开课前必须完成：

```powershell
docker compose up -d --build
docker compose ps
docker compose exec -T api pytest -q
docker compose exec -T api ruff check app scripts tests
npm --prefix frontend test
npm --prefix frontend run build
$env:PLAYWRIGHT_BASE_URL="http://localhost:5173"; npm --prefix frontend run test:e2e
```

如果模型服务未配置，仍可讲授架构、权限、数据源、任务和前端路径，但真实 RAG/Agent 结论必须明确标记为待外部依赖验收。

## 课堂节奏

1. 先演示完整业务闭环：登录、数据源、知识库、分析、报告、审计。
2. 再回到代码拆解：API 合约、服务层、仓储、任务、前端状态。
3. 每个实验只允许修改一个领域，避免课堂变成大范围重构。
4. 每次提交前运行对应最小测试，再在阶段末运行统一验收。
5. 每组必须保留失败记录：错误现象、Trace ID、定位路径和修复方式。

## 讲解重点

### 多租户

强调两层边界：服务层 `tenant_id` 过滤是第一道，PostgreSQL RLS 是第二道。跨组织资源统一返回 `404`，避免泄露资源存在性。

### SQL Guard

模型输出永远不可信。必须通过方言 AST、单语句限制、只读限制、表白名单、危险函数拦截、行数限制和超时控制。

### RAG 引用

结论必须能追溯到文档、chunk、位置和相似度。Embedding 或 Chat 不可用时必须 fail-closed，不能返回假结论。

### 异步任务

用状态机讲清楚 queued、processing、completed、failed、dead-letter。外部副作用任务要有幂等键、尝试次数、错误摘要和人工重试入口。

### 前端控制台

企业控制台要服务高频操作：扫描、筛选、定位、确认和恢复。每个页面都要考虑 loading、empty、error、forbidden、success。

### 交付

CI 不是摆设。后端测试、ruff、前端构建、E2E、Helm、依赖扫描、镜像扫描、Compose config 都是发布闸门。

## 常见故障

| 故障 | 可能原因 | 处理方式 |
| --- | --- | --- |
| API ready 失败 | PostgreSQL 或 Redis 未健康 | 查看 `docker compose ps` 和 API 日志 |
| e2e 无法启动 Chromium | Playwright 浏览器未安装 | 宿主机运行 `npx playwright install chromium`，CI 使用 `--with-deps` |
| 分析无结论 | Chat/Embedding 未配置或数据源/知识库不可用 | 检查系统状态页和 Trace ID |
| 文档摄取卡住 | Worker 或 Redis 异常 | 查看任务状态和 `worker` 日志 |
| PDF 下载失败 | MinIO、导出任务或权限问题 | 查看报告导出状态和审计事件 |
| 第二组织看到第一组织数据 | 严重权限缺陷 | 停止继续开发，先补测试并修复 tenant 过滤 |

## 讲师验收口径

一个小组只有在下面内容都能说明时才算完成：

- 改了哪个领域，为什么不改其他边界。
- 新增或修改了哪些测试。
- 浏览器怎么证明角色和组织隔离仍然正确。
- 失败时用户能看到什么，运维能查到什么。
- 如果发布失败，如何回滚代码、数据库和对象文件。

评分细则见 [ASSESSMENT_RUBRIC.md](ASSESSMENT_RUBRIC.md)。
