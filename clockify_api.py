from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests as rq

API_BASE = "https://api.clockify.me/api/v1"
PAGE_SIZE = 1000


class ClockifyAPIError(Exception):
    pass


def _headers(api_key: str) -> dict:
    return {"X-Api-Key": api_key}


def _check_response(response: rq.Response) -> None:
    if response.status_code == 429:
        raise ClockifyAPIError(
            "Clockify API rate limit reached (30 requests/hour on the Free plan). "
            "Try again later."
        )
    if response.status_code == 401:
        raise ClockifyAPIError("Invalid Clockify API key.")
    try:
        response.raise_for_status()
    except rq.HTTPError as exc:
        raise ClockifyAPIError(f"Clockify API error: {response.status_code}") from exc


def get_current_user(api_key: str) -> dict:
    response = rq.get(f"{API_BASE}/user", headers=_headers(api_key), timeout=30)
    _check_response(response)
    return response.json()


def _duration_hours(start: str, end: str) -> float:
    start_dt = pd.to_datetime(start, utc=True)
    end_dt = pd.to_datetime(end, utc=True)
    return (end_dt - start_dt).total_seconds() / 3600


def _entry_to_row(entry: dict, timezone: str) -> dict | None:
    interval = entry.get("timeInterval") or {}
    end = interval.get("end")
    start = interval.get("start")
    if not end or not start:
        return None

    project = entry.get("project") or {}
    task = entry.get("task") or {}
    project_name = project.get("name", "") if isinstance(project, dict) else ""
    task_name = task.get("name", "") if isinstance(task, dict) else ""

    tz = ZoneInfo(timezone or "UTC")
    end_dt = pd.to_datetime(end, utc=True).tz_convert(tz)

    return {
        "Project": project_name,
        "Task": task_name,
        "Description": entry.get("description") or "",
        "Date": end_dt.date(),
        "Duration (decimal)": _duration_hours(start, end),
    }


def _date_range_iso(start_date: date, end_date: date, timezone: str) -> tuple[str, str]:
    tz = ZoneInfo(timezone or "UTC")
    range_start = datetime.combine(start_date, time.min).replace(tzinfo=tz).isoformat()
    range_end = datetime.combine(end_date, time(23, 59, 59)).replace(tzinfo=tz).isoformat()
    return range_start, range_end


def fetch_time_entries(
    api_key: str,
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, int]:
    if start_date > end_date:
        raise ClockifyAPIError("Start date must be on or before end date.")

    user = get_current_user(api_key)
    user_id = user["id"]
    workspace_id = user.get("activeWorkspace") or user.get("defaultWorkspace")
    if not workspace_id:
        raise ClockifyAPIError("Could not determine Clockify workspace from API key.")

    settings = user.get("settings") or {}
    timezone = settings.get("timeZone", "UTC")
    range_start, range_end = _date_range_iso(start_date, end_date, timezone)

    url = f"{API_BASE}/workspaces/{workspace_id}/user/{user_id}/time-entries"
    all_entries = []
    page = 1

    while True:
        params = {
            "hydrated": "true",
            "start": range_start,
            "end": range_end,
            "page-size": PAGE_SIZE,
            "page": page,
        }
        response = rq.get(url, headers=_headers(api_key), params=params, timeout=60)
        _check_response(response)
        batch = response.json()
        if not batch:
            break
        all_entries.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1

    rows = []
    skipped_in_progress = 0
    for entry in all_entries:
        row = _entry_to_row(entry, timezone)
        if row is None:
            skipped_in_progress += 1
            continue
        rows.append(row)

    if not rows:
        return pd.DataFrame(
            columns=["Project", "Task", "Description", "Date", "Duration (decimal)"]
        ), skipped_in_progress

    return pd.DataFrame(rows), skipped_in_progress


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def recent_month_options(count: int = 12) -> list[tuple[str, tuple[int, int]]]:
    today = date.today()
    year, month = today.year, today.month
    options = []
    for _ in range(count):
        label = date(year, month, 1).strftime("%B %Y")
        options.append((label, (year, month)))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return options
