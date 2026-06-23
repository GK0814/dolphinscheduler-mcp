"""Workflow definition tools for DolphinScheduler MCP.

These tools target DolphinScheduler 3.2.x process-definition APIs and include a
small helper for creating a single-node DataX workflow from a reusable payload.
"""

import json
import time
from typing import Any, Dict, List

from ..client import DolphinSchedulerClient
from ..fastmcp_compat import FastMCPTool


def _parse_json(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _json_param(value: Any, default: Any) -> str:
    parsed = _parse_json(value, default)
    return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))


def _api_success(response: Dict[str, Any]) -> bool:
    return response.get("code") == 0 or response.get("success") is True


def _extract_response_data(response: Dict[str, Any]) -> Any:
    data = response.get("data")
    if isinstance(data, dict) and "data" in data and "code" in data:
        return data.get("data")
    return data


def _optional_query_params(**kwargs: Any) -> Dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value not in (None, "")}


async def _project_preferences(
    client: DolphinSchedulerClient, project_code: int
) -> Dict[str, Any]:
    response = await client.request(
        "GET", f"/projects/{int(project_code)}/project-preference"
    )
    if not _api_success(response):
        return {}
    data = _extract_response_data(response) or {}
    preferences = data.get("preferences") if isinstance(data, dict) else None
    if not preferences:
        return {}
    return _parse_json(preferences, {})


def _datax_task_definition(
    *,
    project_code: int,
    task_code: int,
    task_name: str,
    description: str,
    datax_json: Any,
    worker_group: str,
    environment_code: int,
    xms: int,
    xmx: int,
    task_priority: str,
    fail_retry_times: int,
    fail_retry_interval: int,
    timeout: int,
) -> Dict[str, Any]:
    task_params = {
        "localParams": [],
        "resourceList": [],
        "customConfig": 1,
        "json": _json_param(datax_json, {}),
        "xms": int(xms),
        "xmx": int(xmx),
    }
    return {
        "code": int(task_code),
        "name": task_name,
        "version": 0,
        "description": description,
        "projectCode": int(project_code),
        "taskType": "DATAX",
        "taskParams": task_params,
        "taskParamList": [],
        "taskParamMap": None,
        "flag": "YES",
        "isCache": "NO",
        "taskPriority": task_priority or "MEDIUM",
        "workerGroup": worker_group or "default",
        "environmentCode": int(environment_code or -1),
        "failRetryTimes": int(fail_retry_times or 0),
        "failRetryInterval": int(fail_retry_interval or 1),
        "timeoutFlag": "CLOSE",
        "timeoutNotifyStrategy": None,
        "timeout": int(timeout or 0),
        "delayTime": 0,
        "resourceIds": None,
        "taskGroupId": 0,
        "taskGroupPriority": 0,
        "cpuQuota": -1,
        "memoryMax": -1,
        "taskExecuteType": "BATCH",
        "dependence": "",
    }


def _single_node_relation(
    project_code: int, process_code: int, task_code: int
) -> Dict[str, Any]:
    return {
        "name": "",
        "processDefinitionVersion": 0,
        "projectCode": int(project_code),
        "processDefinitionCode": int(process_code),
        "preTaskCode": 0,
        "preTaskVersion": 0,
        "postTaskCode": int(task_code),
        "postTaskVersion": 0,
        "conditionType": "NONE",
        "conditionParams": {},
    }


class GetProcessDefinitionDetail(FastMCPTool):
    name = "get_process_definition_detail"
    description = (
        "Get full workflow definition detail, including task definitions and "
        "task relations."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
            "processDefinitionCode": {
                "type": "integer",
                "format": "int64",
                "description": "Workflow definition code",
            },
        },
        "required": ["projectCode", "processDefinitionCode"],
    }

    async def _run(self, projectCode, processDefinitionCode) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                (
                    f"/projects/{int(projectCode)}/process-definition/"
                    f"{int(processDefinitionCode)}"
                ),
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class ListProcessDefinitionSimple(FastMCPTool):
    name = "list_process_definition_simple"
    description = (
        "List workflow definitions with lightweight fields: id, code, name, "
        "and projectCode."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
        },
        "required": ["projectCode"],
    }

    async def _run(self, projectCode) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-definition/simple-list",
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class QueryProcessDefinitionList(FastMCPTool):
    name = "query_process_definition_list"
    description = (
        "List workflow definitions with minimal code, name, and version fields."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
        },
        "required": ["projectCode"],
    }

    async def _run(self, projectCode) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                (
                    f"/projects/{int(projectCode)}/process-definition/"
                    "query-process-definition-list"
                ),
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class ListProcessDefinitions(FastMCPTool):
    name = "list_process_definitions"
    description = (
        "List workflow definitions with paging and optional searchVal filter. "
        "Pass empty strings for optional userId and otherParamsJson."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
            "pageNo": {
                "type": "integer",
                "format": "int32",
                "description": "Page number, starting at 1",
            },
            "pageSize": {
                "type": "integer",
                "format": "int32",
                "description": "Page size",
            },
            "searchVal": {
                "type": "string",
                "description": "Optional workflow name search value",
            },
            "userId": {
                "type": "integer",
                "format": "int32",
                "description": "Optional user id filter; pass empty string if unused",
            },
            "otherParamsJson": {
                "type": "string",
                "description": "Optional JSON object string; pass empty string if unused",
            },
        },
        "required": [
            "projectCode",
            "pageNo",
            "pageSize",
            "searchVal",
            "userId",
            "otherParamsJson",
        ],
    }

    async def _run(
        self, projectCode, pageNo, pageSize, searchVal, userId, otherParamsJson
    ) -> Dict:
        client = DolphinSchedulerClient()
        try:
            params = {
                "pageNo": int(pageNo or 1),
                "pageSize": int(pageSize or 20),
                "searchVal": searchVal or "",
            }
            optional = _optional_query_params(
                userId=int(userId) if userId not in (None, "") else "",
                otherParamsJson=otherParamsJson,
            )
            params.update(optional)
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-definition",
                params=params,
            )
            return {"success": _api_success(response), "data": response, "params": params}
        finally:
            await client.close()


class QueryProcessDefinitionByName(FastMCPTool):
    name = "query_process_definition_by_name"
    description = (
        "Query a workflow definition by exact name. Returns found=false when "
        "DolphinScheduler reports the definition does not exist."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
            "name": {
                "type": "string",
                "description": "Exact workflow definition name",
            },
        },
        "required": ["projectCode", "name"],
    }

    async def _run(self, projectCode, name) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-definition/query-by-name",
                params={"name": name},
            )
            if response.get("code") == 50003:
                return {"success": True, "found": False, "data": response}
            return {
                "success": _api_success(response),
                "found": _api_success(response) and response.get("data") is not None,
                "data": response,
            }
        finally:
            await client.close()


class GetProcessDefinitionTasks(FastMCPTool):
    name = "get_process_definition_tasks"
    description = (
        "Get full task definitions for a workflow definition, including "
        "taskType, workerGroup, environmentCode, and taskParams."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
            "processDefinitionCode": {
                "type": "integer",
                "format": "int64",
                "description": "Workflow definition code",
            },
        },
        "required": ["projectCode", "processDefinitionCode"],
    }

    async def _run(self, projectCode, processDefinitionCode) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                (
                    f"/projects/{int(projectCode)}/process-definition/"
                    f"{int(processDefinitionCode)}/tasks"
                ),
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class GenTaskCodes(FastMCPTool):
    name = "gen_task_codes"
    description = "Generate DolphinScheduler task codes for new task definitions."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
            "genNum": {
                "type": "integer",
                "format": "int32",
                "description": "Number of task codes to generate",
            },
        },
        "required": ["projectCode", "genNum"],
    }

    async def _run(self, projectCode, genNum) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/task-definition/gen-task-codes",
                params={"genNum": int(genNum)},
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class VerifyProcessDefinitionName(FastMCPTool):
    name = "verify_process_definition_name"
    description = (
        "Verify whether a workflow definition name is available. Use code=0 "
        "for new workflows."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {
                "type": "integer",
                "format": "int64",
                "description": "Project code",
            },
            "name": {"type": "string", "description": "Workflow name"},
            "code": {
                "type": "integer",
                "format": "int64",
                "description": "Existing workflow code, or 0 for create",
            },
        },
        "required": ["projectCode", "name", "code"],
    }

    async def _run(self, projectCode, name, code) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-definition/verify-name",
                params={"name": name, "code": int(code or 0)},
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class CreateProcessDefinition(FastMCPTool):
    name = "create_process_definition"
    description = (
        "Create a workflow definition from taskDefinitionJson, "
        "taskRelationJson, and locations JSON."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "globalParams": {
                "type": "string",
                "description": "JSON array string, usually []",
            },
            "locations": {
                "type": "string",
                "description": "JSON array string of task node coordinates",
            },
            "timeout": {"type": "integer", "format": "int32"},
            "taskRelationJson": {
                "type": "string",
                "description": "JSON array string of task relations",
            },
            "taskDefinitionJson": {
                "type": "string",
                "description": "JSON array string of task definitions",
            },
            "otherParamsJson": {
                "type": "string",
                "description": "JSON object string, usually {}",
            },
            "executionType": {
                "type": "string",
                "description": "PARALLEL or SERIAL",
            },
        },
        "required": [
            "projectCode",
            "name",
            "description",
            "globalParams",
            "locations",
            "timeout",
            "taskRelationJson",
            "taskDefinitionJson",
            "otherParamsJson",
            "executionType",
        ],
    }

    async def _run(
        self,
        projectCode,
        name,
        description,
        globalParams,
        locations,
        timeout,
        taskRelationJson,
        taskDefinitionJson,
        otherParamsJson,
        executionType,
    ) -> Dict:
        client = DolphinSchedulerClient()
        try:
            params = {
                "name": name,
                "description": description or "",
                "globalParams": _json_param(globalParams, []),
                "locations": _json_param(locations, []),
                "timeout": int(timeout or 0),
                "taskRelationJson": _json_param(taskRelationJson, []),
                "taskDefinitionJson": _json_param(taskDefinitionJson, []),
                "otherParamsJson": _json_param(otherParamsJson, {}),
                "executionType": executionType or "PARALLEL",
            }
            response = await client.request_form(
                "POST",
                f"/projects/{int(projectCode)}/process-definition",
                data=params,
            )
            return {"success": _api_success(response), "data": response, "params": params}
        finally:
            await client.close()


class UpdateProcessDefinition(FastMCPTool):
    name = "update_process_definition"
    description = (
        "Update a workflow definition. Read existing detail first, modify JSON, "
        "then call this tool."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "globalParams": {"type": "string"},
            "locations": {"type": "string"},
            "timeout": {"type": "integer", "format": "int32"},
            "taskRelationJson": {"type": "string"},
            "taskDefinitionJson": {"type": "string"},
            "executionType": {"type": "string"},
            "releaseState": {"type": "string"},
            "otherParamsJson": {"type": "string"},
        },
        "required": [
            "projectCode",
            "processDefinitionCode",
            "name",
            "description",
            "globalParams",
            "locations",
            "timeout",
            "taskRelationJson",
            "taskDefinitionJson",
            "executionType",
            "releaseState",
            "otherParamsJson",
        ],
    }

    async def _run(
        self,
        projectCode,
        processDefinitionCode,
        name,
        description,
        globalParams,
        locations,
        timeout,
        taskRelationJson,
        taskDefinitionJson,
        executionType,
        releaseState,
        otherParamsJson,
    ) -> Dict:
        client = DolphinSchedulerClient()
        try:
            params = {
                "name": name,
                "description": description or "",
                "globalParams": _json_param(globalParams, []),
                "locations": _json_param(locations, []),
                "timeout": int(timeout or 0),
                "taskRelationJson": _json_param(taskRelationJson, []),
                "taskDefinitionJson": _json_param(taskDefinitionJson, []),
                "executionType": executionType or "PARALLEL",
                "releaseState": releaseState or "OFFLINE",
                "otherParamsJson": _json_param(otherParamsJson, {}),
            }
            response = await client.request_form(
                "PUT",
                (
                    f"/projects/{int(projectCode)}/process-definition/"
                    f"{int(processDefinitionCode)}"
                ),
                data=params,
            )
            return {"success": _api_success(response), "data": response, "params": params}
        finally:
            await client.close()


class ReleaseProcessDefinition(FastMCPTool):
    name = "release_process_definition"
    description = "Set a workflow definition release state to ONLINE or OFFLINE."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
            "releaseState": {
                "type": "string",
                "description": "ONLINE or OFFLINE",
            },
            "name": {
                "type": "string",
                "description": "Workflow name, required by some DS versions",
            },
        },
        "required": ["projectCode", "processDefinitionCode", "releaseState", "name"],
    }

    async def _run(self, projectCode, processDefinitionCode, releaseState, name) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "POST",
                (
                    f"/projects/{int(projectCode)}/process-definition/"
                    f"{int(processDefinitionCode)}/release"
                ),
                params={"releaseState": releaseState, "name": name},
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class CreateDataxWorkflow(FastMCPTool):
    name = "create_datax_workflow"
    description = (
        "Create or preview a single-node DATAX workflow. Set dryRun=true to "
        "return the exact process-definition payload without writing to "
        "DolphinScheduler."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "workflowName": {"type": "string"},
            "taskName": {"type": "string"},
            "dataxJson": {"type": "string", "description": "DataX job JSON string"},
            "description": {"type": "string"},
            "workerGroup": {"type": "string"},
            "environmentCode": {"type": "integer", "format": "int64"},
            "xms": {"type": "integer", "format": "int32"},
            "xmx": {"type": "integer", "format": "int32"},
            "taskPriority": {"type": "string"},
            "failRetryTimes": {"type": "integer", "format": "int32"},
            "failRetryInterval": {"type": "integer", "format": "int32"},
            "timeout": {"type": "integer", "format": "int32"},
            "executionType": {"type": "string"},
            "dryRun": {"type": "boolean"},
        },
        "required": [
            "projectCode",
            "workflowName",
            "taskName",
            "dataxJson",
            "description",
            "workerGroup",
            "environmentCode",
            "xms",
            "xmx",
            "taskPriority",
            "failRetryTimes",
            "failRetryInterval",
            "timeout",
            "executionType",
            "dryRun",
        ],
    }

    async def _run(
        self,
        projectCode,
        workflowName,
        taskName,
        dataxJson,
        description,
        workerGroup,
        environmentCode,
        xms,
        xmx,
        taskPriority,
        failRetryTimes,
        failRetryInterval,
        timeout,
        executionType,
        dryRun,
    ) -> Dict:
        client = DolphinSchedulerClient()
        try:
            project_code = int(projectCode)
            is_dry_run = str(dryRun).lower() == "true"
            task_code = int(time.time() * 1000) if is_dry_run else None
            preferences: Dict[str, Any] = {}

            if int(environmentCode or -1) == -1 or not workerGroup:
                preferences = await _project_preferences(client, project_code)
            resolved_worker_group = workerGroup or preferences.get("workerGroup") or "default"
            resolved_environment_code = int(environmentCode or -1)
            if resolved_environment_code == -1 and preferences.get("environmentCode"):
                resolved_environment_code = int(preferences["environmentCode"])

            if not is_dry_run:
                code_response = await client.request(
                    "GET",
                    f"/projects/{project_code}/task-definition/gen-task-codes",
                    params={"genNum": 1},
                )
                if not _api_success(code_response):
                    return {
                        "success": False,
                        "error": "failed to generate task code",
                        "data": code_response,
                    }
                codes = code_response.get("data") or []
                if not codes:
                    return {
                        "success": False,
                        "error": "DolphinScheduler returned no task code",
                        "data": code_response,
                    }
                task_code = int(codes[0])

            task = _datax_task_definition(
                project_code=project_code,
                task_code=task_code,
                task_name=taskName,
                description=description or "",
                datax_json=dataxJson,
                worker_group=resolved_worker_group,
                environment_code=resolved_environment_code,
                xms=int(xms or 1),
                xmx=int(xmx or 1),
                task_priority=taskPriority or "MEDIUM",
                fail_retry_times=int(failRetryTimes or 0),
                fail_retry_interval=int(failRetryInterval or 1),
                timeout=int(timeout or 0),
            )
            relation = _single_node_relation(project_code, 0, task_code)
            locations: List[Dict[str, Any]] = [{"taskCode": task_code, "x": 500, "y": 100}]
            params = {
                "name": workflowName,
                "description": description or "",
                "globalParams": "[]",
                "locations": _json_param(locations, []),
                "timeout": int(timeout or 0),
                "taskRelationJson": _json_param([relation], []),
                "taskDefinitionJson": _json_param([task], []),
                "otherParamsJson": "{}",
                "executionType": executionType or "PARALLEL",
            }

            if is_dry_run:
                return {
                    "success": True,
                    "dryRun": True,
                    "projectCode": project_code,
                    "payload": params,
                    "taskDefinition": task,
                    "taskRelation": relation,
                    "locations": locations,
                    "resolvedPreferences": preferences,
                }

            response = await client.request_form(
                "POST",
                f"/projects/{project_code}/process-definition",
                data=params,
            )
            return {
                "success": _api_success(response),
                "dryRun": False,
                "taskCode": task_code,
                "data": response,
                "payload": params,
            }
        finally:
            await client.close()


def register_process_definition_tools(mcp):
    GetProcessDefinitionDetail.register(mcp)
    ListProcessDefinitionSimple.register(mcp)
    QueryProcessDefinitionList.register(mcp)
    ListProcessDefinitions.register(mcp)
    QueryProcessDefinitionByName.register(mcp)
    GetProcessDefinitionTasks.register(mcp)
    GenTaskCodes.register(mcp)
    VerifyProcessDefinitionName.register(mcp)
    CreateProcessDefinition.register(mcp)
    UpdateProcessDefinition.register(mcp)
    ReleaseProcessDefinition.register(mcp)
    CreateDataxWorkflow.register(mcp)
