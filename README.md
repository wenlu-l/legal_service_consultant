# 法律课程咨询客服（legal-service-consultant）

仿照尚硅谷智能客服仓库（`bj260812-customer-service`）的整体架构与技术栈实现的「法硕研途」法律课程咨询客服。

- 技术栈：FastAPI + uvicorn、SQLAlchemy[asyncio] + aiomysql、langchain + langchain-openai（通义千问）、pydantic-settings、jinja2、httpx、loguru
- 分层架构：`web → service → engine → plan/task/knowledge/chitchat/clarify`，对话状态持久化到 MySQL

## 目录结构

```
consultant/
├── conf/         # pydantic-settings 配置（读取 .env）
├── clients/      # llm / database / http 客户端
├── models/       # SQLAlchemy 模型（dialogue_states 表）
├── repository/   # 对话状态持久层
├── domain/       # 领域数据类（状态、命令、流程、计划、知识等）
├── engine/       # 对话引擎 + 组装器
├── plan/         # LLM 轮次规划 + 校验
├── task/         # 命令处理 / 流程执行 / 动作 / 生命周期
├── knowledge/    # 知识检索  ├── chitchat/  ├── clarify/
├── prompts/      # jinja2 提示词模板
├── service/      # 业务层
└── web/          # 路由 / 依赖 / 请求响应模型
user_flows.yml    # 业务流程（7 个：课程咨询/订单/进度/退款/工单/转人工等）
system_flows.yml  # 系统流程（7 个：任务启动/切换/取消/追问等）
```

## 端口规划（已避开 18081 / 18083 / 3306 / 3307）

| 服务 | 端口 |
|---|---|
| FastAPI 应用 | 18085 |
| MySQL（docker） | 宿主机 3308 → 容器内 3306 |

## 快速启动

1. 启动 MySQL：

   ```bash
   docker compose up -d
   ```

2. 准备 `.env`：

   项目根目录已提供 `.env` 文件（内含各字段的示例值）。请直接编辑它，填写你自己的 `LLM_API_KEY`（必填）。
   其余字段（`LLM_MODEL` / `LLM_BASE_URL` / `DATABASE_URL` / `APP_PORT`）已有默认值，通常无需改动。

3. 安装依赖并启动：

   ```bash
   uv sync           # 若网络慢可先配置国内 PyPI 镜像
   python main.py    # 或 uv run python main.py
   ```

## 接口

- `POST /api/chat`：对话
- `GET /api/chat/history?sender_id=xxx`：查询历史对话

## 说明

- 5 个业务动作（查课程 / 查订单 / 查进度 / 提交退款 / 提交工单）当前返回**演示数据**，代码中已留 TODO，后续可替换为真实后端接口。
- 任务生命周期提示（启动/切换/取消/恢复）与槽位追问由 `system_flows.yml` 驱动。
