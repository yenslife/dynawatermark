# Metadata JSON 規格

## 設計原則

metadata JSON 用來記錄一次浮水印處理作業的輸入、輸出、設定、事件與完整性資訊。格式需穩定、可驗證、可重現。

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
- `integrity`：hash 與完整性資訊。

## 影片資訊

`input_video`：

- `filename`
- `sha256`
- `duration_sec`
- `width`
- `height`
- `fps`

`output_video`：

- `filename`
- `sha256`

`inspection_video`：

- `filename`
- `sha256`

`inspection_video` 是依同一批 `events` 產生的人工核對版影片。每個事件會以紅色實心區塊填滿原本浮水印的座標與尺寸，方便直接觀看影片確認浮水印出現的位置與時間。

## 浮水印素材資訊

`watermark_assets[]`：

- `asset_id`
- `filename`
- `sha256`
- `type`

MVP 的 `type` 固定為 `image/png`。

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

## Integrity

`integrity` 包含：

- `metadata_sha256`
- `config_sha256`

`config_sha256` 針對 canonical config JSON 計算。

`metadata_sha256` 針對 canonical metadata JSON 計算，但計算時 `integrity.metadata_sha256` 必須設為 `null`，避免 hash 自我遞迴。

## Canonical JSON

計算 SHA-256 時使用以下規則：

- UTF-8 編碼。
- object key 依字母排序。
- 不輸出多餘空白。
- 浮點數由資料模型先統一四捨五入到固定精度。

## 範例

```json
{
  "version": "1.0",
  "job_id": "wm_20260419_001",
  "created_at": "2026-04-19T15:30:00+08:00",
  "input_video": {
    "filename": "input.mp4",
    "sha256": "INPUT_VIDEO_HASH",
    "duration_sec": 120.53,
    "width": 1920,
    "height": 1080,
    "fps": 30.0
  },
  "output_video": {
    "filename": "output_watermarked.mp4",
    "sha256": "OUTPUT_VIDEO_HASH"
  },
  "inspection_video": {
    "filename": "inspection_red_boxes.mp4",
    "sha256": "INSPECTION_VIDEO_HASH"
  },
  "watermark_assets": [
    {
      "asset_id": "logo_01",
      "filename": "watermark.png",
      "sha256": "WATERMARK_ASSET_HASH",
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
  ],
  "integrity": {
    "config_sha256": "CONFIG_HASH",
    "metadata_sha256": "METADATA_HASH"
  }
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
