# Web GUI 使用說明

DynaWatermark 提供瀏覽器操作介面，讓影片創作者不需要使用命令列就能處理影片浮水印。

## 啟動 Web GUI

### 基本啟動

```bash
uv run python -m dynawatermark.web
```

啟動後會在終端看到：

```text
🚀 啟動 DynaWatermark Web GUI
📍 網址: http://127.0.0.1:8080
⚙️  按 Ctrl+C 停止伺服器
```

接著開啟瀏覽器進入 <http://127.0.0.1:8080> 即可。

### 自訂埠號與監聽位址

```bash
# 改用 9000 埠
uv run python -m dynawatermark.web --port 9000

# 允許區網其他電腦連線
uv run python -m dynawatermark.web --host 0.0.0.0

# 開發模式：程式碼變更時自動重載
uv run python -m dynawatermark.web --reload
```

### 所有可用參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 監聽位址 |
| `--port` | `8080` | 監聽埠號 |
| `--reload` | `False` | 開發模式，檔案變更自動重載 |

## 操作流程

介面採用四步驟流程：

1. **上傳** - 拖曳或點擊上傳影片檔案（MP4、MOV、AVI 等）與浮水印圖片（PNG 建議透明背景）。
2. **設定** - 調整浮水印數量、透明度範圍、顯示時間範圍、尺寸比例範圍等參數。
3. **處理** - 顯示即時進度環，可隨時取消並重新開始。
4. **下載** - 下載加浮水印的最終影片、人工核對版（含紅框標示）。

## API 端點

如果你需要程式化呼叫，以下是可用的 REST API：

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/jobs` | 建立新的處理任務（multipart 上傳） |
| `GET` | `/api/jobs/{job_id}` | 查詢任務狀態與進度 |
| `DELETE` | `/api/jobs/{job_id}` | 取消進行中的任務 |
| `GET` | `/api/jobs/{job_id}/download/{file_type}` | 下載結果，`file_type` 為 `video`、`inspection`、`metadata` |
| `WS` | `/ws/jobs/{job_id}` | WebSocket 即時進度推送 |

### 範例：查詢任務狀態

```bash
curl http://127.0.0.1:8080/api/jobs/a1b2c3d4
```

回應：

```json
{
  "job_id": "a1b2c3d4",
  "status": "running",
  "progress": 42.5,
  "message": "正在處理 Watermark...",
  "error": null
}
```

## 檔案儲存位置

- **上傳檔案**：`$TMPDIR/dynawatermark_uploads/{job_id}/`
- **輸出檔案**：`$TMPDIR/dynawatermark_outputs/{job_id}/`

任務完成後仍會保留檔案供下載，建議定期清理系統暫存目錄。

## 疑難排解

### 連線被拒絕

確認伺服器已啟動，且防火牆允許該埠號。若要從其他裝置存取，啟動時加上 `--host 0.0.0.0`。

### 找不到 ffmpeg

Web GUI 依賴系統安裝的 FFmpeg。請先確認：

```bash
ffmpeg -version
```

若找不到，請透過系統套件管理器安裝（macOS：`brew install ffmpeg`）。

### 處理卡住或無進度

進度每 5% 更新一次，若影片很短可能看不到明顯變化。若長時間無反應可點擊「取消」並重新開始。
