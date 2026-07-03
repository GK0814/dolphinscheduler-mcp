# DolphinScheduler MCP Server

这是一个面向 Apache DolphinScheduler 3.2.x 的 MCP Server，用于让 Claude Code、Codex、OpenCode 等 Agent 通过 MCP 协议查询和操作 DolphinScheduler。

本项目目前主要按“源码部署”的方式使用，没有发布到 PyPI，因此不要使用 `pip install dolphinscheduler-mcp` 安装。

## 当前定位

本项目不是 DolphinScheduler 官方完整 OpenAPI 的无差别封装，而是针对数据集成和调度运维场景整理过的一组 MCP 工具，重点覆盖：

- 项目、数据源、Worker Group 查询与管理
- 工作流定义查询、创建、更新、上下线
- DataX 单节点工作流创建
- 工作流实例、任务实例、日志查询
- 定时任务查询、创建、更新、上下线
- ADS/ODS 依赖和调度分析辅助工具

创建/更新工作流时，`taskDefinitionJson`、`taskRelationJson` 等大字段会以 `application/x-www-form-urlencoded` form body 发送到 DolphinScheduler，避免把长 DataX JSON 放到 URL query 里导致 `URI Too Long`。

## 运行环境

- Python 3.9+
- DolphinScheduler 3.2.x
- MCP 客户端或 MCP Gateway，例如 MetaMCP

依赖见 [pyproject.toml](./pyproject.toml)。

## 从源码安装

```bash
git clone https://github.com/GK0814/dolphinscheduler-mcp.git
cd dolphinscheduler-mcp

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip setuptools wheel
pip install -e .
```

Windows 本地开发可使用：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip setuptools wheel
pip install -e .
```

安装后会生成命令：

```bash
ds-mcp --help
```

## 配置项

常用环境变量：

| 变量 | 说明 |
| --- | --- |
| `DOLPHINSCHEDULER_API_URL` | DolphinScheduler API 地址，例如 `http://host:12345/dolphinscheduler` |
| `DOLPHINSCHEDULER_API_KEY` | DolphinScheduler API token |
| `DOLPHINSCHEDULER_MCP_HOST` | HTTP 模式监听地址，默认 `0.0.0.0` |
| `DOLPHINSCHEDULER_MCP_PORT` | HTTP 模式监听端口，默认 `8089` |
| `DOLPHINSCHEDULER_MCP_PATH` | Streamable HTTP endpoint，默认 `/mcp` |
| `DOLPHINSCHEDULER_MCP_TRANSPORT` | `stdio`、`sse` 或 `streamable-http`，默认 `stdio` |
| `DOLPHINSCHEDULER_MCP_LOG_LEVEL` | 日志级别，默认 `INFO` |

生产环境建议把环境变量放到独立 env 文件，例如：

```text
/srv/BigData/mcp/env/dolphinscheduler-mcp.env
```

示例：

```bash
DOLPHINSCHEDULER_API_URL=http://10.10.93.xxx:12345/dolphinscheduler
DOLPHINSCHEDULER_API_KEY=your_token
DOLPHINSCHEDULER_MCP_LOG_LEVEL=INFO
```

## 启动方式

### stdio 模式

适合 MCP 客户端直接拉起本地进程：

```bash
ds-mcp \
  --transport stdio \
  --api-url http://10.10.93.xxx:12345/dolphinscheduler \
  --api-key your_token
```

### Streamable HTTP 模式

适合部署到服务器后接入 MetaMCP：

```bash
set -a
source /srv/BigData/mcp/env/dolphinscheduler-mcp.env
set +a

/srv/BigData/mcp/dolphinscheduler-mcp/.venv/bin/ds-mcp \
  --transport streamable-http \
  --host 0.0.0.0 \
  --port 8089 \
  --path /mcp
```

服务地址：

```text
http://服务器IP:8089/mcp
```

## systemd 托管示例

```ini
[Unit]
Description=DolphinScheduler MCP Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/srv/BigData/mcp/dolphinscheduler-mcp
EnvironmentFile=/srv/BigData/mcp/env/dolphinscheduler-mcp.env
ExecStart=/srv/BigData/mcp/dolphinscheduler-mcp/.venv/bin/ds-mcp --transport streamable-http --host 0.0.0.0 --port 8089 --path /mcp
Restart=always
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
```

保存为：

```text
/etc/systemd/system/dolphinscheduler-mcp.service
```

启动：

```bash
systemctl daemon-reload
systemctl enable --now dolphinscheduler-mcp
systemctl status dolphinscheduler-mcp
```

查看日志：

```bash
journalctl -u dolphinscheduler-mcp -f
```

## 接入 MetaMCP

在 MetaMCP 中添加 MCP Server：

```json
{
  "name": "dolphinscheduler-mcp",
  "type": "STREAMABLE_HTTP",
  "url": "http://host.docker.internal:8089/mcp"
}
```

如果 MetaMCP 不在 Docker 中，或可以直接访问宿主机 IP：

```json
{
  "name": "dolphinscheduler-mcp",
  "type": "STREAMABLE_HTTP",
  "url": "http://服务器IP:8089/mcp"
}
```

建议在 MetaMCP 中按权限拆分 namespace：

- `ds-readonly`：只开放查询、日志、定义查看类工具
- `ds-operator`：开放启动实例、定时上下线等运维工具
- `ds-admin`：谨慎开放工作流更新、删除等高风险工具

Agent 只连接 MetaMCP endpoint，不直接持有 DolphinScheduler token。

## 当前注册工具

当前实际注册工具来自 [src/dolphinscheduler_mcp/tools_generated/__init__.py](./src/dolphinscheduler_mcp/tools_generated/__init__.py)，不是 `tools_generated` 目录下所有历史文件都会注册。

### 项目管理

- `list_projects_list`
- `get_projects`
- `get_projects36`
- `create_projects`
- `update_projects`
- `delete_projects`
- `get_projects_unauth_project`
- `get_projects_project_with_authorized_level`
- `get_projects_project_with_authorized_level_list_paging`
- `get_projects_list_dependent`
- `get_projects_created_and_authed`
- `get_projects_authed_user`
- `get_projects_authed_project`

### Worker Group

- `get_worker_groups`
- `create_worker_groups`
- `delete_worker_groups`
- `get_worker_groups_all`
- `get_worker_groups_worker_address_list`

### 数据源

- `get_datasources`
- `get_datasources2`
- `create_datasources`
- `update_datasources`
- `delete_datasources`
- `create_datasources_connect`
- `get_datasources_connect_test`
- `get_datasources_verify_name`
- `get_datasources_unauth_datasource`
- `get_datasources_authed_datasource`
- `get_datasources_kerberos_startup_state`
- `list_datasources_list`
- `list_datasources_databases`
- `list_datasources_tables`
- `list_datasources_tablecolumns`

### 动态任务类型

- `list_dynamic_taskcategories`
- `list_dynamic_tasktypes`

### 项目偏好

- `get_projects_project_preference`
- `update_projects_project_preference`
- `create_projects_project_preference`

### 工作流定义

- `query_process_definition_list`
- `list_process_definition_simple`
- `list_process_definitions`
- `query_process_definition_by_name`
- `get_process_definition_detail`
- `get_process_definition_tasks`
- `gen_task_codes`
- `verify_process_definition_name`
- `create_process_definition`
- `update_process_definition`
- `release_process_definition`
- `create_datax_workflow`

说明：

- `create_datax_workflow` 用于创建单节点 DataX 工作流。
- `create_process_definition`、`update_process_definition` 适合传完整的 `taskDefinitionJson`、`taskRelationJson`、`locations`。
- 工作流定义大字段使用 form body 发送，避免 URL 长度限制。

### 工作流运行与日志

- `start_check_process_definition`
- `start_process_instance`
- `execute_process_instance`
- `list_process_instances`
- `get_process_instance`
- `list_process_instance_tasks`
- `list_task_instances`
- `query_task_log`
- `download_task_log`

### 定时与依赖分析

- `query_schedule_list`
- `list_schedules`
- `get_schedule_by_process_definition`
- `preview_schedule`
- `create_schedule`
- `update_schedule_by_id`
- `update_schedule_by_process_definition`
- `online_schedule`
- `offline_schedule`
- `list_process_definition_dependency_refs`
- `analyze_ads_ods_dependency_schedule`

### 工具使用指南

- `get_tool_usage_guide`

## 安全建议

- 不要把 `DOLPHINSCHEDULER_API_KEY` 暴露给 Agent。
- HTTP 模式的 `8089` 端口不要直接暴露公网。
- 推荐通过 MetaMCP 做统一鉴权、工具过滤和 endpoint 管理。
- `update_process_definition`、`release_process_definition`、`delete_*`、`execute_process_instance` 等工具应只开放给可信 namespace。
- 生产环境建议使用低权限 DolphinScheduler token。

## 开发与验证

基础语法检查：

```bash
python -m py_compile src/dolphinscheduler_mcp/client.py
python -m py_compile src/dolphinscheduler_mcp/tools_generated/process_definition_tools.py
```

运行单元测试：

```bash
pytest
```

本项目包含部分集成测试脚本，真实调用 DolphinScheduler 前请确认目标项目、token 和环境变量，避免误操作生产工作流。

## 许可证

Apache License 2.0
