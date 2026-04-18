# Config Reference

本文件整理 `dynawatermark render` 使用的 JSON 設定欄位。設定檔必須是合法 JSON，建議從 `examples/config.random.json`、`examples/config.advanced-random.json`、`examples/config.subtle-random.json` 或 `examples/config.scheduled.json` 複製後修改。

## CLI 與 Config 的關係

簡易模式可在 CLI 直接指定單張浮水印：

```bash
uv run dynawatermark render \
  --input input.mp4 \
  --config examples/config.random.json \
  --output-dir outputs/demo \
  --watermark watermark.png
```

進階模式請在 config 的 `assets[].path` 設定圖片路徑，並省略 `--watermark`：

```bash
uv run dynawatermark render \
  --input input.mp4 \
  --config examples/config.subtle-random.json \
  --output-dir outputs/demo
```

`assets[].path` 使用相對路徑時，會以該 config 檔所在資料夾為基準。例如 `examples/config.subtle-random.json` 裡的 `assets/subtle-main.png` 會解析成 `examples/assets/subtle-main.png`。

## 頂層欄位

| 欄位 | 型別 | 預設值 | 適用模式 | 說明 |
|---|---:|---:|---|---|
| `mode` | string | `"random"` | 全部 | 浮水印事件產生模式。支援 `"random"` 與 `"scheduled"`。 |
| `seed` | integer | `0` | random | 隨機種子。同一支影片、同一份 config、同一組圖片會產生相同事件。 |
| `max_events` | integer | `25` | random | random 模式最多產生幾個浮水印事件。允許範圍為 `1` 到 `500`。 |
| `opacity_range` | `[number, number]` | `[0.2, 0.4]` | 全部 | 全域透明度範圍。數值為 `0` 到 `1`，越大越不透明。 |
| `duration_range_sec` | `[number, number]` | `[0.8, 2.0]` | random | random 模式每次浮水印出現的持續秒數範圍。 |
| `size_range_ratio` | `[number, number]` | `[0.08, 0.15]` | 全部 | 全域尺寸範圍。代表浮水印寬度佔影片寬度的比例。 |
| `position_strategy` | string | `"random"` | random | 位置策略。MVP 目前只支援 `"random"`。 |
| `margin_ratio` | number | `0.03` | 全部 | 浮水印距離影片邊緣的保留比例。`0.03` 代表至少保留 3% 邊距。 |
| `allow_rotation` | boolean | `false` | 全部 | 保留欄位。MVP 尚未支援旋轉，必須為 `false`。 |
| `assets` | array | `[]` | 全部 | 進階圖片設定。空陣列時需用 CLI `--watermark` 指定單張圖片。 |
| `scheduled_events` | array | `[]` | scheduled | 指定時間事件。`mode` 為 `"scheduled"` 時必填且不可為空。 |

## `assets[]` 欄位

`assets` 用來設定每張浮水印圖片的路徑、透明度、尺寸與 random 模式出現權重。

| 欄位 | 型別 | 預設值 | 必填 | 說明 |
|---|---:|---:|---:|---|
| `asset_id` | string | 無 | 是 | 圖片 ID。events 會用這個 ID 記錄使用哪張圖片。 |
| `path` | string | 無 | 進階模式必填 | 圖片路徑。相對路徑會以 config 檔所在資料夾為基準。 |
| `frequency_weight` | number | `1.0` | 否 | random 模式的出現權重。權重越大，被抽到的機率越高。 |
| `opacity` | number | `null` | 否 | 這張圖片固定透明度。設定後會優先於 `opacity_range`。 |
| `opacity_range` | `[number, number]` | `null` | 否 | 這張圖片自己的透明度範圍。未設定時使用全域 `opacity_range`。 |
| `size_ratio` | number | `null` | 否 | 這張圖片固定寬度比例。設定後會優先於 `size_range_ratio`。 |
| `size_range_ratio` | `[number, number]` | `null` | 否 | 這張圖片自己的尺寸範圍。未設定時使用全域 `size_range_ratio`。 |

### 出現權重

`frequency_weight` 是加權抽選，不是精準比例。例如：

| 圖片 | `frequency_weight` | 大約出現比例 |
|---|---:|---:|
| `logo_main` | `4` | 80% |
| `logo_small` | `1` | 20% |

事件數越多，實際比例通常越接近權重比例；事件數很少時會有明顯隨機波動。

### 透明度優先順序

透明度由高到低依序採用：

1. `scheduled_events[].opacity`
2. `assets[].opacity`
3. `assets[].opacity_range`
4. 全域 `opacity_range`

`opacity: 0.12` 代表 12% 不透明，通常適合低調浮水印。`opacity: 1` 代表完全不透明。

### 尺寸優先順序

尺寸由高到低依序採用：

1. `scheduled_events[].width` 與 `scheduled_events[].height`
2. `scheduled_events[].size_ratio`
3. `assets[].size_ratio`
4. `assets[].size_range_ratio`
5. 全域 `size_range_ratio`

`size_ratio` 代表浮水印寬度相對影片寬度的比例。例如影片寬度是 `1920`，`size_ratio: 0.1` 代表浮水印寬度約 `192px`，高度會依圖片原始長寬比自動推導。

## `scheduled_events[]` 欄位

`scheduled_events` 只在 `mode: "scheduled"` 時使用，用來精準指定每個事件的時間、位置、尺寸與透明度。

| 欄位 | 型別 | 預設值 | 必填 | 說明 |
|---|---:|---:|---:|---|
| `asset_id` | string | 無 | 是 | 要使用的圖片 ID，必須存在於 `assets[].asset_id`。 |
| `start_time_sec` | number | 無 | 是 | 浮水印開始出現的秒數。 |
| `duration_sec` | number | 無 | 是 | 浮水印持續秒數。 |
| `x` | integer | `margin_ratio` 推導 | 否 | 浮水印左上角 X 座標。 |
| `y` | integer | `margin_ratio` 推導 | 否 | 浮水印左上角 Y 座標。 |
| `width` | integer | 依尺寸規則推導 | 否 | 浮水印寬度。若設定 `width`，也必須設定 `height`。 |
| `height` | integer | 依尺寸規則推導 | 否 | 浮水印高度。若設定 `height`，也必須設定 `width`。 |
| `size_ratio` | number | 依尺寸規則推導 | 否 | 該事件專用寬度比例。不可與 `width` / `height` 同時使用。 |
| `opacity` | number | 依透明度規則推導 | 否 | 該事件專用透明度。 |

若 `start_time_sec + duration_sec` 超過影片長度，實作會把 duration 截到影片結尾。若 `x + width` 或 `y + height` 超過影片邊界，實作會把位置限制在畫面內。

## 常用設定範例

### 單張圖片，隨機出現

使用 `examples/config.random.json`，圖片由 CLI `--watermark` 指定。

### 多張圖片，權重抽選

使用 `examples/config.advanced-random.json`。主 logo 權重較高，小 logo 權重較低。

### 低調浮水印

使用 `examples/config.subtle-random.json`。透明度較低、事件數較少，適合不干擾觀看的追蹤浮水印。

### 指定時間

使用 `examples/config.scheduled.json`。每個事件都由 `scheduled_events` 明確指定開始時間與持續時間。
