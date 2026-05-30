"""Runtime, instance, task-instance, and log tools for DolphinScheduler 3.2.x."""

from typing import Any, Dict, Optional

from ..client import DolphinSchedulerClient
from ..fastmcp_compat import FastMCPTool


def _api_success(response: Dict[str, Any]) -> bool:
    return response.get("code") == 0 or response.get("success") is True


def _put_if_value(params: Dict[str, Any], key: str, value: Any) -> None:
    if value is not None and value != "":
        params[key] = value


class StartCheckProcessDefinition(FastMCPTool):
    name = "start_check_process_definition"
    description = "Check whether a workflow definition can be started."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
        },
        "required": ["projectCode", "processDefinitionCode"],
    }

    async def _run(self, projectCode, processDefinitionCode) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "POST",
                f"/projects/{int(projectCode)}/executors/start-check",
                params={"processDefinitionCode": int(processDefinitionCode)},
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class StartProcessInstance(FastMCPTool):
    name = "start_process_instance"
    description = (
        "Start a workflow instance. For a real start, pass confirm=START; "
        "otherwise the tool returns the request payload only."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
            "scheduleTime": {
                "type": "string",
                "description": "Empty string means start now.",
            },
            "failureStrategy": {"type": "string", "description": "END or CONTINUE"},
            "warningType": {"type": "string", "description": "NONE, SUCCESS, FAILURE, ALL, GLOBAL"},
            "processInstancePriority": {"type": "string", "description": "MEDIUM by default"},
            "workerGroup": {"type": "string"},
            "tenantCode": {"type": "string"},
            "environmentCode": {"type": "integer", "format": "int64"},
            "startParams": {"type": "string", "description": "JSON string, optional"},
            "dryRun": {"type": "integer", "format": "int32", "description": "1 for DS dry run, 0 for real run"},
            "confirm": {"type": "string", "description": "Must be START to execute"},
        },
        "required": [
            "projectCode",
            "processDefinitionCode",
            "scheduleTime",
            "failureStrategy",
            "warningType",
            "processInstancePriority",
            "workerGroup",
            "tenantCode",
            "environmentCode",
            "startParams",
            "dryRun",
            "confirm",
        ],
    }

    async def _run(
        self,
        projectCode,
        processDefinitionCode,
        scheduleTime,
        failureStrategy,
        warningType,
        processInstancePriority,
        workerGroup,
        tenantCode,
        environmentCode,
        startParams,
        dryRun,
        confirm,
    ) -> Dict:
        params: Dict[str, Any] = {
            "processDefinitionCode": int(processDefinitionCode),
            "scheduleTime": scheduleTime or "",
            "failureStrategy": failureStrategy or "END",
            "warningType": warningType or "NONE",
            "processInstancePriority": processInstancePriority or "MEDIUM",
            "execType": "START_PROCESS",
            "runMode": "RUN_MODE_SERIAL",
            "dryRun": int(dryRun or 0),
        }
        _put_if_value(params, "workerGroup", workerGroup)
        _put_if_value(params, "tenantCode", tenantCode)
        if environmentCode not in (None, "", "-1", -1):
            params["environmentCode"] = int(environmentCode)
        _put_if_value(params, "startParams", startParams)

        if confirm != "START":
            return {
                "success": False,
                "executed": False,
                "error": "confirm must be START to start a workflow instance",
                "params": params,
            }

        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "POST",
                f"/projects/{int(projectCode)}/executors/start-process-instance",
                params=params,
            )
            return {"success": _api_success(response), "executed": True, "data": response}
        finally:
            await client.close()


class ExecuteProcessInstance(FastMCPTool):
    name = "execute_process_instance"
    description = (
        "Execute an operation on a workflow instance, such as STOP, PAUSE, "
        "REPEAT_RUNNING, or START_FAILURE_TASK_PROCESS. Requires confirm=EXECUTE."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processInstanceId": {"type": "integer", "format": "int32"},
            "executeType": {"type": "string"},
            "confirm": {"type": "string", "description": "Must be EXECUTE"},
        },
        "required": ["projectCode", "processInstanceId", "executeType", "confirm"],
    }

    async def _run(self, projectCode, processInstanceId, executeType, confirm) -> Dict:
        params = {
            "processInstanceId": int(processInstanceId),
            "executeType": executeType,
        }
        if confirm != "EXECUTE":
            return {
                "success": False,
                "executed": False,
                "error": "confirm must be EXECUTE to operate a workflow instance",
                "params": params,
            }

        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "POST",
                f"/projects/{int(projectCode)}/executors/execute",
                params=params,
            )
            return {"success": _api_success(response), "executed": True, "data": response}
        finally:
            await client.close()


class ListProcessInstances(FastMCPTool):
    name = "list_process_instances"
    description = "List workflow instances with paging and optional filters."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "pageNo": {"type": "integer", "format": "int32"},
            "pageSize": {"type": "integer", "format": "int32"},
            "processDefineCode": {"type": "integer", "format": "int64"},
            "searchVal": {"type": "string"},
            "stateType": {"type": "string"},
            "startDate": {"type": "string"},
            "endDate": {"type": "string"},
        },
        "required": [
            "projectCode",
            "pageNo",
            "pageSize",
            "processDefineCode",
            "searchVal",
            "stateType",
            "startDate",
            "endDate",
        ],
    }

    async def _run(
        self,
        projectCode,
        pageNo,
        pageSize,
        processDefineCode,
        searchVal,
        stateType,
        startDate,
        endDate,
    ) -> Dict:
        params: Dict[str, Any] = {"pageNo": int(pageNo), "pageSize": int(pageSize)}
        if processDefineCode not in (None, "", "0", 0):
            params["processDefineCode"] = int(processDefineCode)
        _put_if_value(params, "searchVal", searchVal)
        _put_if_value(params, "stateType", stateType)
        _put_if_value(params, "startDate", startDate)
        _put_if_value(params, "endDate", endDate)

        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-instances",
                params=params,
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class GetProcessInstance(FastMCPTool):
    name = "get_process_instance"
    description = "Get a workflow instance by id."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processInstanceId": {"type": "integer", "format": "int32"},
        },
        "required": ["projectCode", "processInstanceId"],
    }

    async def _run(self, projectCode, processInstanceId) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-instances/{int(processInstanceId)}",
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class ListProcessInstanceTasks(FastMCPTool):
    name = "list_process_instance_tasks"
    description = "List task instances under a workflow instance."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processInstanceId": {"type": "integer", "format": "int32"},
        },
        "required": ["projectCode", "processInstanceId"],
    }

    async def _run(self, projectCode, processInstanceId) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/process-instances/{int(processInstanceId)}/tasks",
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class ListTaskInstances(FastMCPTool):
    name = "list_task_instances"
    description = "List task instances with paging and optional filters."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "pageNo": {"type": "integer", "format": "int32"},
            "pageSize": {"type": "integer", "format": "int32"},
            "processInstanceId": {"type": "integer", "format": "int32"},
            "taskName": {"type": "string"},
            "taskCode": {"type": "integer", "format": "int64"},
            "stateType": {"type": "string"},
            "startDate": {"type": "string"},
            "endDate": {"type": "string"},
        },
        "required": [
            "projectCode",
            "pageNo",
            "pageSize",
            "processInstanceId",
            "taskName",
            "taskCode",
            "stateType",
            "startDate",
            "endDate",
        ],
    }

    async def _run(
        self,
        projectCode,
        pageNo,
        pageSize,
        processInstanceId,
        taskName,
        taskCode,
        stateType,
        startDate,
        endDate,
    ) -> Dict:
        params: Dict[str, Any] = {"pageNo": int(pageNo), "pageSize": int(pageSize)}
        if processInstanceId not in (None, "", "0", 0):
            params["processInstanceId"] = int(processInstanceId)
        _put_if_value(params, "taskName", taskName)
        if taskCode not in (None, "", "0", 0):
            params["taskCode"] = int(taskCode)
        _put_if_value(params, "stateType", stateType)
        _put_if_value(params, "startDate", startDate)
        _put_if_value(params, "endDate", endDate)

        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/projects/{int(projectCode)}/task-instances",
                params=params,
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class QueryTaskLog(FastMCPTool):
    name = "query_task_log"
    description = "Query task instance log lines."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "taskInstanceId": {"type": "integer", "format": "int32"},
            "skipLineNum": {"type": "integer", "format": "int32"},
            "limit": {"type": "integer", "format": "int32"},
        },
        "required": ["projectCode", "taskInstanceId", "skipLineNum", "limit"],
    }

    async def _run(self, projectCode, taskInstanceId, skipLineNum, limit) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "GET",
                f"/log/{int(projectCode)}/detail",
                params={
                    "taskInstanceId": int(taskInstanceId),
                    "skipLineNum": int(skipLineNum or 0),
                    "limit": int(limit or 200),
                },
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class DownloadTaskLog(FastMCPTool):
    name = "download_task_log"
    description = "Download the full task instance log as text."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "taskInstanceId": {"type": "integer", "format": "int32"},
        },
        "required": ["projectCode", "taskInstanceId"],
    }

    async def _run(self, projectCode, taskInstanceId) -> Dict:
        client = DolphinSchedulerClient()
        try:
            raw = await client.request_raw(
                "GET",
                f"/log/{int(projectCode)}/download-log",
                params={"taskInstanceId": int(taskInstanceId)},
            )
            return {
                "success": True,
                "taskInstanceId": int(taskInstanceId),
                "log": raw.decode("utf-8", errors="replace"),
            }
        finally:
            await client.close()


def register_process_runtime_tools(mcp):
    StartCheckProcessDefinition.register(mcp)
    StartProcessInstance.register(mcp)
    ExecuteProcessInstance.register(mcp)
    ListProcessInstances.register(mcp)
    GetProcessInstance.register(mcp)
    ListProcessInstanceTasks.register(mcp)
    ListTaskInstances.register(mcp)
    QueryTaskLog.register(mcp)
    DownloadTaskLog.register(mcp)
