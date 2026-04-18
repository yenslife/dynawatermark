# 實作計畫

## 目標

先完成可用的 CLI MVP，建立後續 Web UI、簽章與進階 fingerprint 功能的核心基礎。

## 模組

- `cli.py`：Typer CLI 入口，提供 `render`。
- `config.py`：設定模型與 JSON 載入。
- `video_probe.py`：呼叫 ffprobe 讀取影片資訊。
- `hashing.py`：檔案 SHA-256 與 canonical JSON SHA-256。
- `event_generator.py`：依影片資訊與設定產生 watermark events。
- `watermark_asset.py`：建立每個事件使用的暫存 PNG。
- `ffmpeg_renderer.py`：建立 FFmpeg filter graph 並輸出影片。
- `metadata.py`：建立 metadata JSON，計算完整性資訊。

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

## FFmpeg 策略

MVP 採用暫存 PNG 策略：

1. 用 Pillow 依每個事件產生已縮放、已套用透明度的 PNG。
2. 將每張 PNG 作為 FFmpeg input。
3. 對每個事件建立 `overlay` filter，使用 `enable='between(t,start,end)'` 控制顯示時間。

這個策略比把所有縮放與 alpha 都塞入 filter graph 更容易 debug，也方便未來加入旋轉。

## 測試

單元測試優先：

- hashing：hash 與 canonical JSON 穩定。
- config：預設值與驗證。
- event generator：seed 穩定、邊界正確。
- metadata：metadata hash 計算不遞迴。
目前不實作獨立 verifier 測試，metadata 仍會保存 hash 作為紀錄。

End-to-end smoke test 等核心模組穩定後再加，並需要確認執行環境有 ffmpeg。

## 後續版本

- 文字浮水印。
- 多素材輪替。
- 指定時間事件的 UI 編輯器。
- owner_id / distribution_id。
- Ed25519 JSON 簽章。
- 驗證報告。
- Web UI 與預覽。
