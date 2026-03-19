"""API 路由"""

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _storage(request: Request):
    return request.app.state.storage


def _trend_analyzer(request: Request):
    return request.app.state.trend_analyzer


def _activity_analyzer(request: Request):
    return request.app.state.activity_analyzer


@router.get("/summary")
async def get_summary(request: Request):
    """获取总体概览统计"""
    storage = _storage(request)
    recent = storage.get_recent_scans(days=30)

    if not recent:
        return {
            "total_scans": 0,
            "total_new_files": 0,
            "total_new_size": 0,
            "latest_scan_time": None,
            "folders_monitored": 0,
        }

    latest = recent[0]
    total_new_files = sum(s["total_new_files"] for s in recent)
    total_new_size = sum(s["total_new_size"] for s in recent)

    # 统计唯一文件夹数（从最新一次扫描的 folder_growth_history 中查）
    with storage.db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(DISTINCT folder_path) FROM folder_growth_history WHERE scan_id = ?",
            (latest["id"],),
        )
        folders_monitored = cursor.fetchone()[0]

    return {
        "total_scans": len(recent),
        "total_new_files": total_new_files,
        "total_new_size": total_new_size,
        "latest_scan_time": latest["scan_time"],
        "folders_monitored": folders_monitored,
    }


@router.get("/scans")
async def get_scans(request: Request, days: int = 30):
    """获取最近扫描历史列表"""
    storage = _storage(request)
    scans = storage.get_recent_scans(days=days)
    return {"scans": scans}


@router.get("/scans/{scan_id}")
async def get_scan_detail(scan_id: int, request: Request):
    """获取单次扫描详情"""
    storage = _storage(request)
    detail = storage.get_scan_by_id(scan_id)
    if not detail:
        raise HTTPException(status_code=404, detail="扫描记录不存在")
    return detail


@router.get("/scans/{scan_id}/folders")
async def get_scan_folders(scan_id: int, request: Request):
    """获取某次扫描的文件夹增长数据"""
    storage = _storage(request)
    if not storage.get_scan_by_id(scan_id):
        raise HTTPException(status_code=404, detail="扫描记录不存在")
    with storage.db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM folder_growth_history WHERE scan_id = ? ORDER BY composite_score DESC",
            (scan_id,),
        )
        folders = [dict(row) for row in cursor.fetchall()]
    return {"folders": folders}


@router.get("/scans/{scan_id}/file-types")
async def get_scan_file_types(scan_id: int, request: Request):
    """获取某次扫描的文件类型分布"""
    storage = _storage(request)
    rows = storage.get_file_type_distribution(scan_id)
    return {"file_types": rows}


@router.get("/scans/{scan_id}/large-files")
async def get_scan_large_files(scan_id: int, request: Request, limit: int = 10):
    """获取某次扫描的大文件列表"""
    storage = _storage(request)
    rows = storage.get_large_files(scan_id, limit=limit)
    return {"large_files": rows}


@router.get("/folders")
async def get_all_folders(request: Request, days: int = 30):
    """获取所有监控文件夹路径列表"""
    storage = _storage(request)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with storage.db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT fgh.folder_path
            FROM folder_growth_history fgh
            JOIN scan_history sh ON fgh.scan_id = sh.id
            WHERE sh.scan_time >= ?
            ORDER BY fgh.folder_path
        """, (cutoff,))
        folders = [row[0] for row in cursor.fetchall()]
    return {"folders": folders}


@router.get("/folders/trend")
async def get_folder_trend(request: Request, folder_path: str, days: int = 14):
    """获取文件夹增长趋势数据"""
    trend_analyzer = _trend_analyzer(request)
    activity_analyzer = _activity_analyzer(request)
    path = Path(folder_path)

    trend = trend_analyzer.analyze_folder_trend(path, days=days)
    anomalies = trend_analyzer.detect_anomalies(path, days=days)
    hourly = activity_analyzer.get_hourly_heatmap(path, days=days)
    weekday = activity_analyzer.get_weekday_heatmap(path, days=days)
    daily = activity_analyzer.get_daily_heatmap(path, days=days)

    trend_data = None
    if trend:
        trend_data = {
            "avg_daily_growth": trend.avg_daily_growth,
            "trend_direction": trend.trend_direction,
            "growth_rate": trend.growth_rate,
            "daily_growth": [
                {"date": str(d), "count": c} for d, c in trend.daily_growth
            ],
        }

    return {
        "trend": trend_data,
        "anomalies": [
            {
                "date": str(a.date),
                "value": a.value,
                "severity": a.severity,
                "expected_min": a.expected_range[0],
                "expected_max": a.expected_range[1],
            }
            for a in anomalies
        ],
        "hourly_heatmap": [hourly.get(h, 0) for h in range(24)],
        "weekday_heatmap": [weekday.get(w, 0) for w in range(1, 8)],
        "daily_heatmap": [
            {"date": str(d), "count": c} for d, c in daily
        ],
    }
