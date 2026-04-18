# dynawatermark

動態影片浮水印 CLI。MVP 支援輸入影片與一張或多張透明 PNG 浮水印，依設定產生隨機或指定時間的浮水印事件，輸出加水印影片與 metadata JSON。

每次 render 預設會輸出兩支影片：

- `output_watermarked.mp4`：實際透明浮水印版本。
- `inspection_red_boxes.mp4`：人工核對版，會用紅色實心區塊標出 metadata events 裡的浮水印範圍。

兩支影片會平行產生，因此預設會同時啟動兩個 FFmpeg 處理程序。

## 開發

安裝依賴：

```bash
uv sync
```

執行測試：

```bash
uv run pytest
```

## 使用

### 簡易模式

使用自己的浮水印檔案，例如 `watermark.jpeg`：

```bash
uv run dynawatermark render \
  --input demo1.mov \
  --config examples/config.random.json \
  --output-dir outputs/demo \
  --watermark watermark.jpeg
```

### 進階多圖片

圖片寫在 `assets[].path`，不需要 `--watermark`：

```bash
uv run dynawatermark render \
  --input demo1.mov \
  --config examples/config.advanced-random.json \
  --output-dir outputs/demo
```

### 低調浮水印

```bash
uv run dynawatermark render \
  --input demo1.mov \
  --config examples/config.subtle-random.json \
  --output-dir outputs/demo
```

### 指定時間

```bash
uv run dynawatermark render \
  --input demo1.mov \
  --config examples/config.scheduled.json \
  --output-dir outputs/demo
```

### 不輸出人工核對版

```bash
uv run dynawatermark render \
  --input demo1.mov \
  --config examples/config.subtle-random.json \
  --output-dir outputs/demo \
  --no-inspection
```

預設輸出位置：

```text
outputs/demo/wm_YYYYMMDD_HHMMSS/output_watermarked.mp4
outputs/demo/wm_YYYYMMDD_HHMMSS/inspection_red_boxes.mp4
outputs/demo/wm_YYYYMMDD_HHMMSS/metadata.json
```

## 設定重點

透明度優先順序：

1. `scheduled_events[].opacity`
2. `assets[].opacity` 或 `assets[].opacity_range`
3. 全域 `opacity_range`

random 模式可用 `assets[].frequency_weight` 控制每張圖片出現比例。scheduled 模式可用 `scheduled_events` 指定時間、位置、尺寸與透明度。

更多說明見：

- `docs/requirements.md`
- `docs/metadata-schema.md`
- `docs/config-reference.md`
