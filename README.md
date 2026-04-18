# dynawatermark

動態影片浮水印 CLI。MVP 支援輸入影片與一張或多張透明 PNG 浮水印，依設定產生隨機或指定時間的浮水印事件，輸出加水印影片與 metadata JSON。

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

Render：

```bash
uv run dynawatermark render \
  --input input.mp4 \
  --config examples/config.random.json \
  --output-dir outputs/demo \
  --watermark watermark.png
```

若使用進階 config，圖片可寫在 `assets[].path`，不需要 `--watermark`：

```bash
uv run dynawatermark render \
  --input input.mp4 \
  --config examples/config.advanced-random.json \
  --output-dir outputs/demo
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
