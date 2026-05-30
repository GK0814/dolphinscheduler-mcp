# DolphinScheduler MCP Tool Classification

This document records the tool categories agents should use when working with
DolphinScheduler 3.2.1. The same guidance is exposed to agents through the
`get_tool_usage_guide` MCP tool.

## Core ODS Integration Flow

Use these tools for the main loop: create or update a workflow, run it, inspect
results, read logs, and iterate until data lands in ODS.

- `list_projects_list`
- `get_projects_project_preference`
- `get_worker_groups_all`
- `list_process_definition_simple`
- `query_process_definition_list`
- `list_process_definitions`
- `query_process_definition_by_name`
- `query_schedule_list`
- `list_schedules`
- `get_schedule_by_process_definition`
- `preview_schedule`
- `list_process_definition_dependency_refs`
- `analyze_ads_ods_dependency_schedule`
- `gen_task_codes`
- `verify_process_definition_name`
- `create_datax_workflow`
- `create_process_definition`
- `get_process_definition_detail`
- `get_process_definition_tasks`
- `update_process_definition`
- `release_process_definition`
- `start_check_process_definition`
- `start_process_instance`
- `list_process_instances`
- `get_process_instance`
- `list_process_instance_tasks`
- `list_task_instances`
- `query_task_log`
- `download_task_log`
- `execute_process_instance`

Recommended order:

1. Find or create the test project.
2. Read project preferences, worker groups, and environment codes.
3. Use lightweight workflow-definition list tools to find existing workflows by name.
4. Preview or create the workflow definition.
5. Read back the definition and verify task JSON.
6. Release online, start a workflow instance, then inspect instance, task, and logs.
7. Update the definition and repeat until the ODS load succeeds.

## Read-Only Safe

These tools should not modify DolphinScheduler state. Some can still return
sensitive data and must be summarized carefully.

- Project and worker queries: `list_projects_list`, `get_projects`,
  `get_projects_created_and_authed`,
  `get_projects_project_preference`, `get_worker_groups_all`,
  `get_worker_groups`, `get_worker_groups_worker_address_list`
- Workflow and runtime queries: `get_process_definition_detail`,
  `list_process_definition_simple`, `query_process_definition_list`,
  `list_process_definitions`, `query_process_definition_by_name`,
  `get_process_definition_tasks`, `query_schedule_list`, `list_schedules`,
  `get_schedule_by_process_definition`, `preview_schedule`,
  `list_process_definition_dependency_refs`,
  `analyze_ads_ods_dependency_schedule`,
  `list_process_instances`, `get_process_instance`,
  `list_process_instance_tasks`, `list_task_instances`,
  `query_task_log`, `download_task_log`
- Data source queries: `get_datasources`, `list_datasources_list`,
  `list_datasources_databases`,
  `list_datasources_tables`, `list_datasources_tablecolumns`

## Protected Write Or Execution

These tools modify definitions or execute workflows. Use only in an approved test
project or after explicit user confirmation.

- Project and workflow writes: `create_projects`, `update_projects`,
  `create_process_definition`, `update_process_definition`,
  `release_process_definition`, `create_datax_workflow`
- Schedule writes: `create_schedule`, `update_schedule_by_id`,
  `update_schedule_by_process_definition`, `online_schedule`,
  `offline_schedule`
- Runtime operations: `start_process_instance`, `execute_process_instance`
- Project preference writes: `update_projects_project_preference`

Guardrails:

- Prefer names with a clear test prefix, such as `codex_mcp_test_`.
- Read existing workflow definitions before calling `update_process_definition`.
- Use `create_schedule` and `update_schedule_by_*` with `dryRun=true` before
  `confirm=CREATE` or `confirm=UPDATE`.
- `online_schedule` requires `confirm=ONLINE`.
- `offline_schedule` requires `confirm=OFFLINE`.
- `start_process_instance` requires `confirm=START`.
- `execute_process_instance` requires `confirm=EXECUTE`.
- Avoid deleting or taking workflows offline outside a disposable project.

## High-Risk Destructive

Destructive generated tools are not registered in the default profile.

## Sensitive Secret Exposure

These may return credentials, access tokens, JDBC URLs, or task JSON containing
passwords. Do not echo secrets back to the user.

- `get_datasources`
- `query_process_definition_by_name`
- `get_process_definition_tasks`
- `get_process_definition_detail`
- `query_task_log`
- `download_task_log`

## Known Problem Or Low Priority

These tool groups are intentionally not registered in the default profile to
reduce token overhead and avoid known noisy or risky generated endpoints.

- Azure DataFactory tools
- audit log tools
- k8s namespace tools
- access token tools
- legacy lineage tools
- project parameter tools
- process-task-relation tools
- environment check/update tools
- project worker-group tools

Re-enable a group only when there is a concrete use case and the endpoints have
been tested on DolphinScheduler 3.2.1.
