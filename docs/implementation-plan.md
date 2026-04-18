# 實作計畫

## 目標

先完成可用的 CLI MVP，建立後續 Web UI、簽章與進階 fingerprint 功能的核心基礎。

## 模組

- `cli.py`：Typer CLI 入口，提供 `render`。
- `service.py`：渲染作業服務層，提供 `render_job()` 給 CLI 或未來 GUI 呼叫。
- `errors.py`：集中定義使用者可讀的錯誤型別。
- `config.py`：設定模型與 JSON 載入。
- `video_probe.py`：呼叫 ffprobe 讀取影片資訊。
- `event_generator.py`：依影片資訊與設定產生 watermark events。
- `watermark_asset.py`：建立每個事件使用的暫存 PNG。
- `ffmpeg_renderer.py`：建立 FFmpeg filter graph 並輸出影片。
- `ffmpeg_renderer.py` 也負責依 events 產生紅色區塊人工核對版影片。
- `metadata.py`：建立 metadata JSON。

## CLI

Render：

```bash
uv run dynawatermark render \
  --input input.mp4 \
  --config examples/config.random.json \
  --output-dir outputs/demo \
  --watermark watermark.png
```

若 config 內有 `assets[].path`，可以省略 `--watermark`。

CLI 只負責參數解析、呼叫 `render_job()`、顯示進度與輸出路徑。核心流程放在 `service.py`，未來 GUI 可以直接呼叫同一個 service function。

## Service API

核心服務入口：

```python
from pathlib import Path
from dynawatermark.service import render_job

result = render_job(
    input_video=Path("input.mp4"),
    config_path=Path("examples/config.subtle-random.json"),
    output_dir=Path("outputs/demo"),
    watermark_path=None,
    inspection=True,
)
```

回傳結果包含：

- `job_id`
- `output_video`
- `inspection_video`
- `metadata_path`
- `events_count`

GUI 若需要取消功能，可以建立 `RenderCancelToken` 並傳入 `render_job()`：

```python
from dynawatermark.service import RenderCancelToken, render_job

cancel_token = RenderCancelToken()

result = render_job(
    input_video=Path("input.mp4"),
    config_path=Path("examples/config.subtle-random.json"),
    output_dir=Path("outputs/demo"),
    inspection=True,
    cancel_token=cancel_token,
)

# 另一個 UI thread / request handler 可以呼叫：
cancel_token.cancel()
```

`service.py` 也提供 GUI 可使用的狀態列舉：

- `queued`
- `running`
- `completed`
- `failed`
- `canceled`

## 錯誤處理

常見錯誤會轉成使用者可讀的 exception：

- `FfmpegNotFoundError`：找不到 `ffmpeg` 或 `ffprobe`。
- `VideoProbeError`：`ffprobe` 無法讀取影片、影片沒有 video stream，或無法取得 duration。
- `FfmpegRenderError`：FFmpeg render 失敗。
- `ConfigError`：config JSON 格式或欄位驗證失敗。
- `AssetError`：缺少 watermark asset 或 asset 路徑不存在。
- `RenderCanceledError`：使用者取消處理。

## FFmpeg 策略

MVP 採用暫存 PNG 策略：

1. 用 Pillow 依每個事件產生已縮放、已套用透明度的 PNG。
2. 將每張 PNG 作為 FFmpeg input。
3. 對每個事件建立 `overlay` filter，使用 `enable='between(t,start,end)'` 控制顯示時間。
4. 另外用同一批 events 建立 `drawbox` filter，輸出紅色實心區塊人工核對版影片。
5. 預設以兩個 FFmpeg process 平行輸出透明浮水印版與紅色區塊人工核對版。

這個策略比把所有縮放與 alpha 都塞入 filter graph 更容易 debug，也方便未來加入旋轉。

## 測試

單元測試優先：

- config：預設值與驗證。
- event generator：seed 穩定、邊界正確。
- metadata：metadata 可序列化與回讀。
- service：asset path 錯誤、缺少 watermark、取消 token。
- end-to-end：有 ffmpeg/ffprobe 時，產生短測試影片與 PNG，確認 normal video、inspection video、metadata 都能輸出。

End-to-end 測試會在缺少 ffmpeg 或 ffprobe 時自動略過。

## 後續版本

- 文字浮水印。
- 多素材輪替。
- 指定時間事件的 UI 編輯器。
- owner_id / distribution_id。
- SHA-256 檔案摘要。
- Ed25519 JSON 簽章。
- 驗證報告。
- Web UI 與預覽。
