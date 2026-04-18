# 動態影片浮水印需求規格

## 產品目標

本專案提供一套可追蹤的影片動態浮水印流程，能在影片時間軸上以固定或隨機方式加入半透明浮水印圖塊，並在輸出後產生結構化 JSON 紀錄檔。紀錄檔保存每次浮水印出現的時間、位置、大小、透明度與素材識別資訊，作為後續版權追蹤、來源鑑識與內容歸屬證明的輔助資料。

## MVP 範圍

第一版先做本機 CLI 工具，聚焦在可驗證的影片處理核心。

- 輸入一支影片。
- 輸入一張透明 PNG 浮水印素材。
- 依 JSON 設定產生隨機或指定時間的浮水印事件。
- 使用 FFmpeg 輸出加上浮水印的新影片。
- 輸出 metadata JSON。
- 計算輸入影片、輸出影片、浮水印素材、設定與 metadata 的 SHA-256，寫入 metadata。

## 暫不納入 MVP

- Web UI。
- 文字浮水印。
- SVG 浮水印。
- 人臉、字幕或敏感區域避讓。
- 私鑰簽章。
- RFC 3161 timestamp。
- 獨立 verify 指令。
- 依使用者自動產生不同 fingerprint 的分發流程。

## 輸入

### 影片

MVP 以 MP4 為主要支援格式。FFmpeg 可讀取的 MOV 或 MKV 不特別禁止，但不保證所有 codec 組合都能成功處理。

### 浮水印素材

MVP 支援一張或多張 PNG，建議使用透明背景。

### 設定

設定檔使用 JSON，至少包含：

- `mode`：支援 `random` 與 `scheduled`。
- `seed`：隨機種子，用於重現 random 模式的事件。
- `max_events`：random 模式最多產生事件數。
- `opacity_range`：全域透明度範圍。
- `duration_range_sec`：random 模式每次出現持續時間範圍。
- `size_range_ratio`：全域尺寸比例範圍，代表浮水印寬度相對影片寬度的比例。
- `position_strategy`：目前支援 `random`。
- `margin_ratio`：距離影片邊界的最小比例。
- `allow_rotation`：MVP 先接受欄位，但預設不旋轉。
- `assets`：進階圖片設定，可指定每張圖的 path、透明度、尺寸與出現權重。
- `scheduled_events`：scheduled 模式使用，指定每個事件的出現時間、位置、尺寸與透明度。

## 透明度設定

透明度可分三層設定，優先順序由高到低：

1. `scheduled_events[].opacity`：單一指定事件的透明度。
2. `assets[].opacity` 或 `assets[].opacity_range`：單一圖片的固定透明度或透明度範圍。
3. `opacity_range`：全域預設透明度範圍。

例如 `opacity: 0.3` 代表該圖片或事件固定使用 30% 不透明度；`opacity_range: [0.2, 0.5]` 代表每次事件從 20% 到 50% 之間隨機挑選。

## 多圖片與出現頻率

`assets` 可設定多張 PNG。random 模式會依 `frequency_weight` 做加權抽選。

例如：

- `logo_main.frequency_weight = 4`
- `logo_small.frequency_weight = 1`

代表 `logo_main` 大約會佔 80% 事件，`logo_small` 大約會佔 20% 事件。這不是保證精準比例，而是隨機抽選的權重。

每張圖片也可以設定自己的：

- `opacity`
- `opacity_range`
- `size_ratio`
- `size_range_ratio`

## 指定時間模式

`mode: "scheduled"` 會停用 random 事件產生，改用 `scheduled_events` 裡列出的事件。

每個指定事件至少要有：

- `asset_id`
- `start_time_sec`
- `duration_sec`

可選設定：

- `x`
- `y`
- `width`
- `height`
- `size_ratio`
- `opacity`

若沒有指定 `x`、`y`，會使用靠近左上方且保留 `margin_ratio` 的預設位置。若沒有指定尺寸，會依事件、圖片或全域尺寸設定推導。

## 處理流程

1. 使用 ffprobe 讀取影片資訊。
2. 計算輸入影片與浮水印素材 SHA-256。
3. 載入並驗證設定。
4. 根據影片資訊與設定產生 watermark events；random 模式自動產生，scheduled 模式使用指定事件。
5. 為每個 event 產生暫存 PNG，套用尺寸與透明度。
6. 使用 FFmpeg filter graph 將暫存 PNG 疊加到影片。
7. 輸出影片。
8. 計算輸出影片 SHA-256。
9. 產生 metadata JSON 與 metadata SHA-256。

## 證明力限制

MVP 的 JSON 與 SHA-256 可以保留檔案摘要與處理紀錄，但目前不提供獨立 verify 指令，也不能單獨證明 metadata 一定由特定系統或特定人產生。若需要更強證明力，後續版本應加入私鑰簽章、可信時間戳記與分發對象識別碼。
