"""Read-only schedule and workflow dependency analysis tools."""

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..client import DolphinSchedulerClient
from ..fastmcp_compat import FastMCPTool


def _api_success(response: Dict[str, Any]) -> bool:
    return response.get("code") == 0 or response.get("success") is True


def _optional_query_params(**kwargs: Any) -> Dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value not in (None, "")}


def _is_true(value: Any) -> bool:
    return str(value).lower() in ("1", "true", "yes", "y")


def _to_int_or_none(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _workflow_data_by_code(workflows: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    result: Dict[int, Dict[str, Any]] = {}
    for workflow in workflows:
        definition = workflow.get("processDefinition") or {}
        code = _to_int_or_none(definition.get("code"))
        if code is not None:
            result[code] = definition
    return result


def _schedule_by_workflow_code(schedules: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    result: Dict[int, Dict[str, Any]] = {}
    for schedule in schedules:
        code = _to_int_or_none(schedule.get("processDefinitionCode"))
        if code is not None:
            result[code] = schedule
    return result


def _parse_cron(crontab: Any) -> Dict[str, Any]:
    if not crontab:
        return {"raw": crontab, "kind": "missing"}
    parts = str(crontab).split()
    if len(parts) < 6:
        return {"raw": crontab, "kind": "unknown"}

    second, minute, hour = parts[0], parts[1], parts[2]

    def fixed_int(value: str) -> Optional[int]:
        return int(value) if re.fullmatch(r"\d+", value or "") else None

    sec = fixed_int(second)
    minute_value = fixed_int(minute)
    hour_value = fixed_int(hour)
    if sec is None or minute_value is None:
        return {"raw": crontab, "kind": "complex"}
    if hour_value is None and hour == "*":
        return {
            "raw": crontab,
            "kind": "hourly",
            "minute": minute_value,
            "second": sec,
            "minuteSecondRank": minute_value * 60 + sec,
            "display": f"every hour {minute_value:02d}:{sec:02d}",
        }
    if hour_value is not None:
        return {
            "raw": crontab,
            "kind": "daily",
            "hour": hour_value,
            "minute": minute_value,
            "second": sec,
            "daySecondRank": hour_value * 3600 + minute_value * 60 + sec,
            "minuteSecondRank": minute_value * 60 + sec,
            "display": f"{hour_value:02d}:{minute_value:02d}:{sec:02d}",
        }
    return {"raw": crontab, "kind": "complex"}


def _compare_schedule_order(
    runner_cron: Dict[str, Any], dependent_cron: Dict[str, Any]
) -> Dict[str, Any]:
    runner_kind = runner_cron.get("kind")
    dependent_kind = dependent_cron.get("kind")
    if runner_kind == "missing" or dependent_kind == "missing":
        return {"status": "unknown_missing_schedule"}
    if runner_kind == "complex" or dependent_kind == "complex":
        return {"status": "unknown_complex_cron"}
    if runner_kind == dependent_kind == "hourly":
        ok = dependent_cron["minuteSecondRank"] > runner_cron["minuteSecondRank"]
        return {"status": "ok_after_runner" if ok else "bad_not_after_runner"}
    if runner_kind == dependent_kind == "daily":
        ok = dependent_cron["daySecondRank"] > runner_cron["daySecondRank"]
        return {"status": "ok_after_runner" if ok else "bad_not_after_runner"}
    if runner_kind == "hourly" and dependent_kind == "daily":
        ok = dependent_cron["minuteSecondRank"] > runner_cron["minuteSecondRank"]
        return {
            "status": "ok_after_runner_same_hour" if ok else "unknown_mixed_schedule_frequency",
            "note": "Runner is hourly and dependent is daily; comparison uses the dependent hour.",
        }
    return {
        "status": "unknown_mixed_schedule_frequency",
        "note": f"Runner schedule is {runner_kind}, dependent schedule is {dependent_kind}.",
    }


def _walk_dependence_refs(value: Any, refs: List[Dict[str, Any]]) -> None:
    if isinstance(value, dict):
        code = (
            value.get("definitionCode")
            or value.get("depWorkflowCode")
            or value.get("processDefinitionCode")
        )
        if code not in (None, ""):
            refs.append(
                {
                    "refType": "DEPENDENT",
                    "definitionCode": _to_int_or_none(code),
                    "projectCode": _to_int_or_none(value.get("projectCode")),
                    "cycle": value.get("cycle"),
                    "dateValue": value.get("dateValue"),
                    "state": value.get("state"),
                }
            )
        for child in value.values():
            _walk_dependence_refs(child, refs)
    elif isinstance(value, list):
        for item in value:
            _walk_dependence_refs(item, refs)


def _dependency_refs_from_tasks(
    tasks: List[Dict[str, Any]], workflow_names: Optional[Dict[int, str]] = None
) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for task in tasks:
        task_type = task.get("taskType")
        task_params = task.get("taskParams") or {}
        task_base = {
            "taskCode": task.get("code"),
            "taskName": task.get("name"),
            "taskType": task_type,
        }
        task_refs: List[Dict[str, Any]] = []
        if task_type == "SUB_PROCESS":
            code = _to_int_or_none(task_params.get("processDefinitionCode"))
            if code is not None:
                task_refs.append({"refType": "SUB_PROCESS", "definitionCode": code})
        elif task_type == "DEPENDENT":
            _walk_dependence_refs(task_params.get("dependence") or task_params, task_refs)

        for ref in task_refs:
            code = ref.get("definitionCode")
            refs.append(
                {
                    **task_base,
                    **ref,
                    "definitionName": workflow_names.get(code) if workflow_names else None,
                }
            )
    return refs


def _schedule_write_params(
    *,
    schedule: str,
    warningType: str,
    warningGroupId: Any,
    failureStrategy: str,
    workerGroup: str,
    tenantCode: str,
    environmentCode: Any,
    processInstancePriority: str,
    processDefinitionCode: Any = None,
) -> Dict[str, Any]:
    params = {"schedule": schedule}
    if processDefinitionCode not in (None, ""):
        params["processDefinitionCode"] = int(processDefinitionCode)
    params.update(
        _optional_query_params(
            warningType=warningType,
            warningGroupId=_to_int_or_none(warningGroupId),
            failureStrategy=failureStrategy,
            workerGroup=workerGroup,
            tenantCode=tenantCode,
            environmentCode=_to_int_or_none(environmentCode),
            processInstancePriority=processInstancePriority,
        )
    )
    return params


class QueryScheduleList(FastMCPTool):
    name = "query_schedule_list"
    description = "List all schedules in a project. Read-only wrapper for DS schedule list."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
        },
        "required": ["projectCode"],
    }

    async def _run(self, projectCode) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "POST", f"/projects/{int(projectCode)}/schedules/list"
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class ListSchedules(FastMCPTool):
    name = "list_schedules"
    description = (
        "List schedules with paging and optional workflow filters. Pass empty "
        "strings for optional searchVal, processDefinitionCode, and processDefinitionId."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "pageNo": {"type": "integer", "format": "int32"},
            "pageSize": {"type": "integer", "format": "int32"},
            "searchVal": {"type": "string"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
            "processDefinitionId": {"type": "integer", "format": "int32"},
        },
        "required": [
            "projectCode",
            "pageNo",
            "pageSize",
            "searchVal",
            "processDefinitionCode",
            "processDefinitionId",
        ],
    }

    async def _run(
        self,
        projectCode,
        pageNo,
        pageSize,
        searchVal,
        processDefinitionCode,
        processDefinitionId,
    ) -> Dict:
        client = DolphinSchedulerClient()
        try:
            params = {
                "pageNo": int(pageNo or 1),
                "pageSize": int(pageSize or 20),
                "searchVal": searchVal or "",
            }
            params.update(
                _optional_query_params(
                    processDefinitionCode=_to_int_or_none(processDefinitionCode),
                    processDefinitionId=_to_int_or_none(processDefinitionId),
                )
            )
            response = await client.request(
                "GET", f"/projects/{int(projectCode)}/schedules", params=params
            )
            return {"success": _api_success(response), "data": response, "params": params}
        finally:
            await client.close()


class GetScheduleByProcessDefinition(FastMCPTool):
    name = "get_schedule_by_process_definition"
    description = "Get schedules for one workflow definition code."
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
            params = {
                "pageNo": 1,
                "pageSize": 20,
                "searchVal": "",
                "processDefinitionCode": int(processDefinitionCode),
                "processDefinitionId": 0,
            }
            response = await client.request(
                "GET", f"/projects/{int(projectCode)}/schedules", params=params
            )
            return {"success": _api_success(response), "data": response, "params": params}
        finally:
            await client.close()


class ListProcessDefinitionDependencyRefs(FastMCPTool):
    name = "list_process_definition_dependency_refs"
    description = (
        "Return only SUB_PROCESS and DEPENDENT workflow references for one "
        "workflow definition. Does not return SQL or taskParams."
    )
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
            project_code = int(projectCode)
            definition_code = int(processDefinitionCode)
            detail_response = await client.request(
                "GET",
                f"/projects/{project_code}/process-definition/{definition_code}",
            )
            if not _api_success(detail_response):
                return {"success": False, "data": detail_response}

            list_response = await client.request(
                "GET",
                f"/projects/{project_code}/process-definition/query-process-definition-list",
            )
            workflow_names = {
                int(item["code"]): item["name"]
                for item in (list_response.get("data") or [])
                if item.get("code") is not None
            }
            detail = detail_response.get("data") or {}
            definition = detail.get("processDefinition") or {}
            refs = _dependency_refs_from_tasks(
                detail.get("taskDefinitionList") or [], workflow_names
            )
            return {
                "success": True,
                "data": {
                    "processDefinitionCode": definition.get("code"),
                    "processDefinitionName": definition.get("name"),
                    "releaseState": definition.get("releaseState"),
                    "refs": refs,
                },
            }
        finally:
            await client.close()


class PreviewSchedule(FastMCPTool):
    name = "preview_schedule"
    description = "Preview upcoming schedule fire times from a DolphinScheduler schedule JSON string."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "schedule": {
                "type": "string",
                "description": "Schedule JSON string, usually containing startTime, endTime, crontab, and timezoneId.",
            },
        },
        "required": ["projectCode", "schedule"],
    }

    async def _run(self, projectCode, schedule) -> Dict:
        client = DolphinSchedulerClient()
        try:
            response = await client.request(
                "POST",
                f"/projects/{int(projectCode)}/schedules/preview",
                params={"schedule": schedule},
            )
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class CreateSchedule(FastMCPTool):
    name = "create_schedule"
    description = (
        "Create a workflow schedule. Use dryRun=true to preview the exact request; "
        "for a real create pass dryRun=false and confirm=CREATE."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
            "schedule": {"type": "string"},
            "warningType": {"type": "string"},
            "warningGroupId": {"type": "integer", "format": "int32"},
            "failureStrategy": {"type": "string"},
            "workerGroup": {"type": "string"},
            "tenantCode": {"type": "string"},
            "environmentCode": {"type": "integer", "format": "int64"},
            "processInstancePriority": {"type": "string"},
            "dryRun": {"type": "boolean"},
            "confirm": {"type": "string"},
        },
        "required": [
            "projectCode",
            "processDefinitionCode",
            "schedule",
            "warningType",
            "warningGroupId",
            "failureStrategy",
            "workerGroup",
            "tenantCode",
            "environmentCode",
            "processInstancePriority",
            "dryRun",
            "confirm",
        ],
    }

    async def _run(
        self,
        projectCode,
        processDefinitionCode,
        schedule,
        warningType,
        warningGroupId,
        failureStrategy,
        workerGroup,
        tenantCode,
        environmentCode,
        processInstancePriority,
        dryRun,
        confirm,
    ) -> Dict:
        params = _schedule_write_params(
            processDefinitionCode=processDefinitionCode,
            schedule=schedule,
            warningType=warningType,
            warningGroupId=warningGroupId,
            failureStrategy=failureStrategy,
            workerGroup=workerGroup,
            tenantCode=tenantCode,
            environmentCode=environmentCode,
            processInstancePriority=processInstancePriority,
        )
        path = f"/projects/{int(projectCode)}/schedules"
        if _is_true(dryRun) or confirm != "CREATE":
            return {
                "success": True,
                "dryRun": True,
                "requiresConfirm": "CREATE",
                "method": "POST",
                "path": path,
                "params": params,
            }

        client = DolphinSchedulerClient()
        try:
            response = await client.request("POST", path, params=params)
            return {"success": _api_success(response), "dryRun": False, "data": response}
        finally:
            await client.close()


class UpdateScheduleById(FastMCPTool):
    name = "update_schedule_by_id"
    description = (
        "Update a schedule by schedule id. Use dryRun=true to preview; for a real "
        "update pass dryRun=false and confirm=UPDATE."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "id": {"type": "integer", "format": "int32"},
            "schedule": {"type": "string"},
            "warningType": {"type": "string"},
            "warningGroupId": {"type": "integer", "format": "int32"},
            "failureStrategy": {"type": "string"},
            "workerGroup": {"type": "string"},
            "tenantCode": {"type": "string"},
            "environmentCode": {"type": "integer", "format": "int64"},
            "processInstancePriority": {"type": "string"},
            "dryRun": {"type": "boolean"},
            "confirm": {"type": "string"},
        },
        "required": [
            "projectCode",
            "id",
            "schedule",
            "warningType",
            "warningGroupId",
            "failureStrategy",
            "workerGroup",
            "tenantCode",
            "environmentCode",
            "processInstancePriority",
            "dryRun",
            "confirm",
        ],
    }

    async def _run(
        self,
        projectCode,
        id,
        schedule,
        warningType,
        warningGroupId,
        failureStrategy,
        workerGroup,
        tenantCode,
        environmentCode,
        processInstancePriority,
        dryRun,
        confirm,
    ) -> Dict:
        params = _schedule_write_params(
            schedule=schedule,
            warningType=warningType,
            warningGroupId=warningGroupId,
            failureStrategy=failureStrategy,
            workerGroup=workerGroup,
            tenantCode=tenantCode,
            environmentCode=environmentCode,
            processInstancePriority=processInstancePriority,
        )
        path = f"/projects/{int(projectCode)}/schedules/{int(id)}"
        if _is_true(dryRun) or confirm != "UPDATE":
            return {
                "success": True,
                "dryRun": True,
                "requiresConfirm": "UPDATE",
                "method": "PUT",
                "path": path,
                "params": params,
            }

        client = DolphinSchedulerClient()
        try:
            response = await client.request("PUT", path, params=params)
            return {"success": _api_success(response), "dryRun": False, "data": response}
        finally:
            await client.close()


class UpdateScheduleByProcessDefinition(FastMCPTool):
    name = "update_schedule_by_process_definition"
    description = (
        "Update a schedule by workflow definition code. Use dryRun=true to preview; "
        "for a real update pass dryRun=false and confirm=UPDATE."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "processDefinitionCode": {"type": "integer", "format": "int64"},
            "schedule": {"type": "string"},
            "warningType": {"type": "string"},
            "warningGroupId": {"type": "integer", "format": "int32"},
            "failureStrategy": {"type": "string"},
            "workerGroup": {"type": "string"},
            "tenantCode": {"type": "string"},
            "environmentCode": {"type": "integer", "format": "int64"},
            "processInstancePriority": {"type": "string"},
            "dryRun": {"type": "boolean"},
            "confirm": {"type": "string"},
        },
        "required": [
            "projectCode",
            "processDefinitionCode",
            "schedule",
            "warningType",
            "warningGroupId",
            "failureStrategy",
            "workerGroup",
            "tenantCode",
            "environmentCode",
            "processInstancePriority",
            "dryRun",
            "confirm",
        ],
    }

    async def _run(
        self,
        projectCode,
        processDefinitionCode,
        schedule,
        warningType,
        warningGroupId,
        failureStrategy,
        workerGroup,
        tenantCode,
        environmentCode,
        processInstancePriority,
        dryRun,
        confirm,
    ) -> Dict:
        params = _schedule_write_params(
            processDefinitionCode=processDefinitionCode,
            schedule=schedule,
            warningType=warningType,
            warningGroupId=warningGroupId,
            failureStrategy=failureStrategy,
            workerGroup=workerGroup,
            tenantCode=tenantCode,
            environmentCode=environmentCode,
            processInstancePriority=processInstancePriority,
        )
        path = (
            f"/projects/{int(projectCode)}/schedules/update/"
            f"{int(processDefinitionCode)}"
        )
        if _is_true(dryRun) or confirm != "UPDATE":
            return {
                "success": True,
                "dryRun": True,
                "requiresConfirm": "UPDATE",
                "method": "PUT",
                "path": path,
                "params": params,
            }

        client = DolphinSchedulerClient()
        try:
            response = await client.request("PUT", path, params=params)
            return {"success": _api_success(response), "dryRun": False, "data": response}
        finally:
            await client.close()


class OnlineSchedule(FastMCPTool):
    name = "online_schedule"
    description = "Set a schedule ONLINE. Requires confirm=ONLINE."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "id": {"type": "integer", "format": "int32"},
            "confirm": {"type": "string"},
        },
        "required": ["projectCode", "id", "confirm"],
    }

    async def _run(self, projectCode, id, confirm) -> Dict:
        path = f"/projects/{int(projectCode)}/schedules/{int(id)}/online"
        if confirm != "ONLINE":
            return {
                "success": True,
                "dryRun": True,
                "requiresConfirm": "ONLINE",
                "method": "POST",
                "path": path,
            }
        client = DolphinSchedulerClient()
        try:
            response = await client.request("POST", path)
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class OfflineSchedule(FastMCPTool):
    name = "offline_schedule"
    description = "Set a schedule OFFLINE. Requires confirm=OFFLINE."
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "id": {"type": "integer", "format": "int32"},
            "confirm": {"type": "string"},
        },
        "required": ["projectCode", "id", "confirm"],
    }

    async def _run(self, projectCode, id, confirm) -> Dict:
        path = f"/projects/{int(projectCode)}/schedules/{int(id)}/offline"
        if confirm != "OFFLINE":
            return {
                "success": True,
                "dryRun": True,
                "requiresConfirm": "OFFLINE",
                "method": "POST",
                "path": path,
            }
        client = DolphinSchedulerClient()
        try:
            response = await client.request("POST", path)
            return {"success": _api_success(response), "data": response}
        finally:
            await client.close()


class AnalyzeAdsOdsDependencySchedule(FastMCPTool):
    name = "analyze_ads_ods_dependency_schedule"
    description = (
        "Analyze ADS workflows that reference the same ODS workflows through "
        "SUB_PROCESS or DEPENDENT, and compare their schedule order. Read-only."
    )
    is_async = True
    schema = {
        "type": "object",
        "properties": {
            "projectCode": {"type": "integer", "format": "int64"},
            "adsNamePrefix": {
                "type": "string",
                "description": "ADS workflow name prefix, usually ads",
            },
            "odsNameContains": {
                "type": "string",
                "description": "ODS workflow name marker, usually _to_ods_",
            },
        },
        "required": ["projectCode", "adsNamePrefix", "odsNameContains"],
    }

    async def _run(self, projectCode, adsNamePrefix, odsNameContains) -> Dict:
        client = DolphinSchedulerClient()
        try:
            project_code = int(projectCode)
            ads_prefix = (adsNamePrefix or "ads").lower()
            ods_marker = (odsNameContains or "_to_ods_").lower()

            workflow_response = await client.request(
                "GET", f"/projects/{project_code}/process-definition/list"
            )
            if not _api_success(workflow_response):
                return {"success": False, "data": workflow_response}
            schedule_response = await client.request(
                "POST", f"/projects/{project_code}/schedules/list"
            )
            if not _api_success(schedule_response):
                return {"success": False, "data": schedule_response}

            workflows = workflow_response.get("data") or []
            workflow_by_code = _workflow_data_by_code(workflows)
            workflow_names = {
                code: definition.get("name")
                for code, definition in workflow_by_code.items()
            }
            schedules = schedule_response.get("data") or []
            schedule_by_code = _schedule_by_workflow_code(schedules)
            refs_by_ods: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

            for workflow in workflows:
                definition = workflow.get("processDefinition") or {}
                workflow_name = definition.get("name") or ""
                workflow_code = _to_int_or_none(definition.get("code"))
                if workflow_code is None or not workflow_name.lower().startswith(ads_prefix):
                    continue

                refs = _dependency_refs_from_tasks(
                    workflow.get("taskDefinitionList") or [], workflow_names
                )
                schedule = schedule_by_code.get(workflow_code)
                cron = _parse_cron(schedule.get("crontab") if schedule else None)
                for ref in refs:
                    ods_code = _to_int_or_none(ref.get("definitionCode"))
                    ods_name = workflow_names.get(ods_code)
                    if ods_code is None or not ods_name:
                        continue
                    if ods_marker not in ods_name.lower():
                        continue
                    refs_by_ods[ods_code].append(
                        {
                            "adsWorkflowCode": workflow_code,
                            "adsWorkflowName": workflow_name,
                            "adsReleaseState": definition.get("releaseState"),
                            "scheduleReleaseState": (
                                schedule.get("releaseState") if schedule else None
                            ),
                            "crontab": schedule.get("crontab") if schedule else None,
                            "schedule": cron.get("display") or cron.get("raw"),
                            "cronKind": cron.get("kind"),
                            "taskCode": ref.get("taskCode"),
                            "taskName": ref.get("taskName"),
                            "refType": ref.get("refType"),
                            "depCycle": ref.get("cycle"),
                            "depDateValue": ref.get("dateValue"),
                            "_cron": cron,
                        }
                    )

            groups: List[Dict[str, Any]] = []
            for ods_code, refs in refs_by_ods.items():
                ads_codes = {ref["adsWorkflowCode"] for ref in refs}
                if len(ads_codes) < 2:
                    continue

                runners = [ref for ref in refs if ref["refType"] == "SUB_PROCESS"]
                dependents = [ref for ref in refs if ref["refType"] == "DEPENDENT"]
                findings: List[Dict[str, Any]] = []
                if not runners:
                    findings.append({"status": "no_sub_process_runner"})
                if len(runners) > 1:
                    findings.append({"status": "multiple_sub_process_runners"})
                if len(runners) == 1:
                    runner = runners[0]
                    for dependent in dependents:
                        findings.append(
                            {
                                **_compare_schedule_order(
                                    runner["_cron"], dependent["_cron"]
                                ),
                                "dependentAdsWorkflowName": dependent["adsWorkflowName"],
                                "runnerAdsWorkflowName": runner["adsWorkflowName"],
                            }
                        )

                clean_refs = []
                for ref in refs:
                    clean_ref = {key: value for key, value in ref.items() if key != "_cron"}
                    clean_refs.append(clean_ref)
                clean_refs.sort(
                    key=lambda item: (
                        item["refType"] != "SUB_PROCESS",
                        item.get("schedule") or "",
                        item["adsWorkflowName"],
                    )
                )
                groups.append(
                    {
                        "odsWorkflowCode": ods_code,
                        "odsWorkflowName": workflow_names.get(ods_code),
                        "runnerCount": len(runners),
                        "dependentCount": len(dependents),
                        "findings": findings,
                        "refs": clean_refs,
                    }
                )

            groups.sort(key=lambda item: item["odsWorkflowName"] or "")
            return {
                "success": True,
                "data": {
                    "projectCode": project_code,
                    "workflowCount": len(workflows),
                    "scheduleCount": len(schedules),
                    "multiAdsOdsCount": len(groups),
                    "groups": groups,
                },
            }
        finally:
            await client.close()


def register_schedule_tools(mcp):
    QueryScheduleList.register(mcp)
    ListSchedules.register(mcp)
    GetScheduleByProcessDefinition.register(mcp)
    PreviewSchedule.register(mcp)
    CreateSchedule.register(mcp)
    UpdateScheduleById.register(mcp)
    UpdateScheduleByProcessDefinition.register(mcp)
    OnlineSchedule.register(mcp)
    OfflineSchedule.register(mcp)
    ListProcessDefinitionDependencyRefs.register(mcp)
    AnalyzeAdsOdsDependencySchedule.register(mcp)
