"""Tool usage guidance for DolphinScheduler MCP agents."""

from typing import Dict

from ..fastmcp_compat import FastMCPTool


TOOL_USAGE_GUIDE = {
    "core_data_integration_flow": {
        "purpose": "Primary workflow for building and debugging ODS data integration.",
        "tools": [
            "list_projects_list",
            "get_projects_project_preference",
            "get_worker_groups_all",
            "list_process_definition_simple",
            "query_process_definition_list",
            "list_process_definitions",
            "query_process_definition_by_name",
            "query_schedule_list",
            "list_schedules",
            "get_schedule_by_process_definition",
            "preview_schedule",
            "list_process_definition_dependency_refs",
            "analyze_ads_ods_dependency_schedule",
            "gen_task_codes",
            "verify_process_definition_name",
            "create_datax_workflow",
            "create_process_definition",
            "get_process_definition_detail",
            "get_process_definition_tasks",
            "update_process_definition",
            "release_process_definition",
            "start_check_process_definition",
            "start_process_instance",
            "list_process_instances",
            "get_process_instance",
            "list_process_instance_tasks",
            "list_task_instances",
            "query_task_log",
            "download_task_log",
            "execute_process_instance",
        ],
        "recommended_order": [
            "Find or create the test project.",
            "Read project preference, worker groups, and environment codes.",
            "Use lightweight workflow-definition list tools to find existing workflows by name.",
            "Preview or create the workflow definition.",
            "Read back the definition and verify task JSON.",
            "Release ONLINE, start a workflow instance, then inspect instance, task, and logs.",
            "Update the definition and repeat until the ODS load succeeds.",
        ],
    },
    "read_only_safe": {
        "purpose": "Safe for exploration; should not modify DolphinScheduler state.",
        "tools": [
            "list_projects_list",
            "get_projects",
            "get_projects_created_and_authed",
            "get_projects_project_preference",
            "get_worker_groups_all",
            "get_worker_groups",
            "get_worker_groups_worker_address_list",
            "list_dynamic_taskcategories",
            "list_dynamic_tasktypes",
            "list_process_definition_simple",
            "query_process_definition_list",
            "list_process_definitions",
            "query_process_definition_by_name",
            "get_process_definition_tasks",
            "query_schedule_list",
            "list_schedules",
            "get_schedule_by_process_definition",
            "preview_schedule",
            "list_process_definition_dependency_refs",
            "analyze_ads_ods_dependency_schedule",
            "get_process_definition_detail",
            "list_process_instances",
            "get_process_instance",
            "list_process_instance_tasks",
            "list_task_instances",
            "query_task_log",
            "download_task_log",
            "get_datasources",
            "list_datasources_list",
            "list_datasources_databases",
            "list_datasources_tables",
            "list_datasources_tablecolumns",
        ],
    },
    "protected_write_or_execution": {
        "purpose": "Modifies definitions or executes workflows; use only in an approved test project or after explicit user confirmation.",
        "tools": [
            "create_projects",
            "update_projects",
            "create_process_definition",
            "update_process_definition",
            "release_process_definition",
            "create_datax_workflow",
            "create_schedule",
            "update_schedule_by_id",
            "update_schedule_by_process_definition",
            "online_schedule",
            "offline_schedule",
            "start_process_instance",
            "execute_process_instance",
            "update_projects_project_preference",
        ],
        "guardrails": [
            "Prefer project names and workflow names with a clear test prefix, such as codex_mcp_test_.",
            "Read existing definitions before update_process_definition.",
            "Use create_schedule/update_schedule_by_* with dryRun=true before confirm=CREATE or confirm=UPDATE.",
            "online_schedule requires confirm=ONLINE.",
            "offline_schedule requires confirm=OFFLINE.",
            "start_process_instance requires confirm=START.",
            "execute_process_instance requires confirm=EXECUTE.",
            "Avoid deleting or taking workflows offline outside a disposable project.",
        ],
    },
    "high_risk_destructive": {
        "purpose": "Destructive generated tools are not registered in the default profile.",
        "tools": [],
    },
    "sensitive_secret_exposure": {
        "purpose": "Read-only, but may return credentials, access tokens, JDBC URLs, or task JSON containing passwords.",
        "tools": [
            "get_datasources",
            "query_process_definition_by_name",
            "get_process_definition_tasks",
            "get_process_definition_detail",
            "download_task_log",
            "query_task_log",
        ],
        "handling": [
            "Do not echo passwords, tokens, or full connection strings back to the user.",
            "Summarize sensitive responses with ids, names, state, and non-secret metadata only.",
        ],
    },
    "known_problem_or_low_priority": {
        "purpose": "Observed as failing, slow, environment-specific, or outside the current ODS integration goal.",
        "tools": [
            "Azure DataFactory tools",
            "audit log tools",
            "k8s namespace tools",
            "access token tools",
            "legacy lineage tools",
            "project parameter tools",
            "process-task-relation tools",
            "environment check/update tools",
            "project worker-group tools",
        ],
        "notes": [
            "These tool groups are intentionally not registered in the default profile to reduce token overhead and avoid known noisy or risky generated endpoints.",
            "Re-enable a group only when there is a concrete use case and the endpoints have been tested on DolphinScheduler 3.2.1.",
        ],
    },
}


class GetToolUsageGuide(FastMCPTool):
    name = "get_tool_usage_guide"
    description = (
        "Return DolphinScheduler MCP tool categories, safety levels, known issues, "
        "and the recommended agent workflow for ODS data integration."
    )
    is_async = True

    async def _run(self) -> Dict:
        return {"success": True, "data": TOOL_USAGE_GUIDE}


def register_tool_guidance_tools(mcp):
    GetToolUsageGuide.register(mcp)
