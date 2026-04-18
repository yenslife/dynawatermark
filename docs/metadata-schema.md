# Metadata JSON 規格

## 設計原則

metadata JSON 用來記錄一次浮水印處理作業的輸入、輸出、設定與事件資訊。格式需穩定、清楚、可重現。

## 頂層欄位

- `version`：metadata 格式版本，MVP 使用 `1.0`。
- `job_id`：作業 ID，例如 `wm_20260419_001`。
- `created_at`：ISO 8601 時間字串。
- `input_video`：輸入影片資訊。
- `output_video`：輸出影片資訊。
- `inspection_video`：紅色區塊人工核對版影片資訊，若未輸出則為 `null`。
- `watermark_assets`：浮水印素材資訊列表。
- `config`：實際使用的設定。
- `events`：浮水印事件列表。

## 影片資訊

`input_video`：

- `filename`
- `duration_sec`
- `width`
- `height`
- `fps`

`output_video`：

- `filename`

`inspection_video`：

- `filename`

`inspection_video` 是依同一批 `events` 產生的人工核對版影片。每個事件會以紅色實心區塊填滿原本浮水印的座標與尺寸，方便直接觀看影片確認浮水印出現的位置與時間。

## 浮水印素材資訊

`watermark_assets[]`：

- `asset_id`
- `filename`
- `type`
- `width`
- `height`

`type` 會依副檔名推測，例如 `image/png` 或 `image/jpeg`。

## 設定資訊

`config` 應保存實際使用值，而不是只保存使用者輸入片段。若使用者省略選項，metadata 中應寫入預設值。

## 事件資訊

每個 event 包含：

- `event_id`
- `start_time_sec`
- `end_time_sec`
- `duration_sec`
- `x`
- `y`
- `width`
- `height`
- `opacity`
- `rotation_deg`
- `asset_id`

事件必須符合：

- `start_time_sec >= 0`
- `end_time_sec <= input_video.duration_sec`
- `duration_sec = end_time_sec - start_time_sec`
- `x >= 0`
- `y >= 0`
- `x + width <= input_video.width`
- `y + height <= input_video.height`
- `0 <= opacity <= 1`

## 範例

```json
{
  "version": "1.0",
  "job_id": "wm_20260419_001",
  "created_at": "2026-04-19T15:30:00+08:00",
  "input_video": {
    "filename": "input.mp4",
    "duration_sec": 120.53,
    "width": 1920,
    "height": 1080,
    "fps": 30.0
  },
  "output_video": {
    "filename": "output_watermarked.mp4"
  },
  "inspection_video": {
    "filename": "inspection_red_boxes.mp4"
  },
  "watermark_assets": [
    {
      "asset_id": "logo_01",
      "filename": "watermark.png",
      "type": "image/png",
      "width": 500,
      "height": 200
    }
  ],
  "config": {
    "mode": "random",
    "seed": 12345,
    "max_events": 25,
    "opacity_range": [0.2, 0.4],
    "duration_range_sec": [0.8, 2.0],
    "size_range_ratio": [0.08, 0.15],
    "position_strategy": "random",
    "margin_ratio": 0.03,
    "allow_rotation": false,
    "assets": [
      {
        "asset_id": "logo_01",
        "path": "assets/watermark.png",
        "frequency_weight": 1,
        "opacity_range": [0.2, 0.4],
        "size_range_ratio": [0.08, 0.15]
      }
    ],
    "scheduled_events": []
  },
  "events": [
    {
      "event_id": "evt_0001",
      "start_time_sec": 3.42,
      "end_time_sec": 4.87,
      "duration_sec": 1.45,
      "x": 1432,
      "y": 820,
      "width": 180,
      "height": 72,
      "opacity": 0.31,
      "rotation_deg": 0.0,
      "asset_id": "logo_01"
    }
  ]
}
```

## 設定範例

### Random 模式，多張圖片

```json
{
  "mode": "random",
  "seed": 12345,
  "max_events": 30,
  "opacity_range": [0.15, 0.35],
  "duration_range_sec": [0.8, 2.0],
  "size_range_ratio": [0.08, 0.15],
  "position_strategy": "random",
  "margin_ratio": 0.03,
  "allow_rotation": false,
  "assets": [
    {
      "asset_id": "logo_main",
      "path": "assets/logo-main.png",
      "frequency_weight": 4,
      "opacity_range": [0.18, 0.28],
      "size_range_ratio": [0.08, 0.12]
    },
    {
      "asset_id": "logo_small",
      "path": "assets/logo-small.png",
      "frequency_weight": 1,
      "opacity": 0.42,
      "size_ratio": 0.06
    }
  ]
}
```

### Scheduled 模式，指定時間

```json
{
  "mode": "scheduled",
  "opacity_range": [0.2, 0.4],
  "duration_range_sec": [0.8, 2.0],
  "size_range_ratio": [0.08, 0.15],
  "position_strategy": "random",
  "margin_ratio": 0.03,
  "allow_rotation": false,
  "assets": [
    {
      "asset_id": "logo_main",
      "path": "assets/logo-main.png",
      "opacity": 0.3,
      "size_ratio": 0.1
    }
  ],
  "scheduled_events": [
    {
      "asset_id": "logo_main",
      "start_time_sec": 3.0,
      "duration_sec": 1.5,
      "x": 120,
      "y": 80,
      "opacity": 0.35
    }
  ]
}
```
