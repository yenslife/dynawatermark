"""FastAPI web application for DynaWatermark GUI."""
from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from dynawatermark.config import WatermarkConfig, WatermarkAssetConfig
from dynawatermark.service import render_job, RenderCancelToken
from dynawatermark.errors import DynawatermarkError

# 全域任務儲存
active_jobs: dict[str, dict[str, Any]] = {}

UPLOAD_DIR = Path(tempfile.gettempdir()) / "dynawatermark_uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "dynawatermark_outputs"


def _ensure_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_dirs()
    yield
    # 清理舊檔案可在此處理


app = FastAPI(
    title="DynaWatermark",
    description="動態可追溯影片浮水印工具",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態檔案
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """提供主頁面。"""
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/jobs")
async def create_job(
    video: UploadFile = File(..., description="影片檔案"),
    watermark: UploadFile = File(..., description="浮水印圖片"),
    mode: str = Form("random", description="random 或 scheduled"),
    max_events: int = Form(25, ge=1, le=500),
    opacity_min: float = Form(0.2, ge=0, le=1),
    opacity_max: float = Form(0.4, ge=0, le=1),
    duration_min: float = Form(0.8, gt=0),
    duration_max: float = Form(2.0, gt=0),
    size_min: float = Form(0.08, gt=0),
    size_max: float = Form(0.15, gt=0),
    margin_ratio: float = Form(0.03, ge=0, lt=0.5),
    inspection: bool = Form(True),
) -> JSONResponse:
    """建立新的浮水印處理任務。"""
    job_id = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # 儲存上傳檔案
    video_path = job_dir / video.filename
    watermark_path = job_dir / watermark.filename

    with video_path.open("wb") as f:
        shutil.copyfileobj(video.file, f)
    with watermark_path.open("wb") as f:
        shutil.copyfileobj(watermark.file, f)

    # 建立設定檔
    config = WatermarkConfig(
        mode=mode,  # type: ignore
        max_events=max_events,
        opacity_range=(opacity_min, opacity_max),
        duration_range_sec=(duration_min, duration_max),
        size_range_ratio=(size_min, size_max),
        margin_ratio=margin_ratio,
        assets=[WatermarkAssetConfig(asset_id="logo_01", path=watermark_path)],
    )
    config_path = job_dir / "config.json"
    config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    # 初始化任務狀態
    active_jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "等待處理...",
        "output_video": None,
        "inspection_video": None,
        "metadata_path": None,
        "error": None,
        "cancel_token": None,
    }

    # 啟動背景處理
    asyncio.create_task(
        _process_job(
            job_id=job_id,
            video_path=video_path,
            config_path=config_path,
            watermark_path=watermark_path,
            inspection=inspection,
        )
    )

    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "任務已建立",
    })


def _update_job_progress(job_id: str, percent: float, message: str) -> None:
    """更新任務進度的回呼函式。"""
    job = active_jobs.get(job_id)
    if job is not None:
        job["progress"] = percent
        job["message"] = message


async def _process_job(
    job_id: str,
    video_path: Path,
    config_path: Path,
    watermark_path: Path,
    inspection: bool,
) -> None:
    """背景處理任務。"""
    job = active_jobs.get(job_id)
    if job is None:
        return

    job["status"] = "running"
    job["message"] = "正在初始化..."
    job["cancel_token"] = RenderCancelToken()

    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)

    # 建立進度回呼（使用 partial 綁定 job_id）
    from functools import partial
    progress_callback = partial(_update_job_progress, job_id)

    try:
        # 在執行緒池中執行 CPU 密集型工作
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: render_job(
                input_video=video_path,
                config_path=config_path,
                output_dir=job_output_dir,
                watermark_path=watermark_path,
                inspection=inspection,
                show_progress=False,  # Web 端自己顯示進度
                cancel_token=job["cancel_token"],
                progress_callback=progress_callback,
            ),
        )

        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = f"完成！產生 {result.events_count} 個浮水印事件"
        job["output_video"] = str(result.output_video)
        job["inspection_video"] = str(result.inspection_video) if result.inspection_video else None
        job["metadata_path"] = str(result.metadata_path)

    except DynawatermarkError as e:
        job["status"] = "failed"
        job["message"] = f"處理失敗：{e}"
        job["error"] = str(e)
    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"內部錯誤：{e}"
        job["error"] = str(e)


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    """取得任務狀態。"""
    job = active_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    return JSONResponse({
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "error": job.get("error"),
    })


@app.get("/api/jobs/{job_id}/download/{file_type}")
async def download_file(job_id: str, file_type: str) -> FileResponse:
    """下載完成的檔案。"""
    job = active_jobs.get(job_id)
    if job is None or job["status"] != "completed":
        raise HTTPException(status_code=404, detail="找不到完成的檔案")

    if file_type == "video" and job["output_video"]:
        file_path = Path(job["output_video"])
    elif file_type == "inspection" and job["inspection_video"]:
        file_path = Path(job["inspection_video"])
    elif file_type == "metadata" and job["metadata_path"]:
        file_path = Path(job["metadata_path"])
    else:
        raise HTTPException(status_code=404, detail="找不到檔案")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="檔案已過期或已被刪除")

    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str) -> JSONResponse:
    """取消任務。"""
    job = active_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    if job["status"] == "running" and job.get("cancel_token"):
        job["cancel_token"].cancel()
        job["status"] = "canceled"
        job["message"] = "使用者取消"

    return JSONResponse({"job_id": job_id, "status": job["status"]})


@app.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    """WebSocket 即時進度更新。"""
    await websocket.accept()

    try:
        while True:
            job = active_jobs.get(job_id)
            if job is None:
                await websocket.send_json({"error": "任務不存在"})
                break

            await websocket.send_json({
                "status": job["status"],
                "progress": job["progress"],
                "message": job["message"],
            })

            if job["status"] in ("completed", "failed", "canceled"):
                break

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


@app.get("/api/preview-config")
async def preview_config(
    opacity_min: float = 0.2,
    opacity_max: float = 0.4,
    size_min: float = 0.08,
    size_max: float = 0.15,
) -> JSONResponse:
    """預覽設定效果（回傳範例設定）。"""
    config = WatermarkConfig(
        opacity_range=(opacity_min, opacity_max),
        size_range_ratio=(size_min, size_max),
    )
    return JSONResponse(json.loads(config.model_dump_json()))
