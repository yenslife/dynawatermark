"""Entry point for web GUI."""
from __future__ import annotations

import sys

import uvicorn


def main() -> None:
    """啟動 DynaWatermark Web GUI。"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DynaWatermark Web GUI")
    parser.add_argument("--host", default="127.0.0.1", help="監聽位址 (預設: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="監聽埠號 (預設: 8080)")
    parser.add_argument("--reload", action="store_true", help="開發模式：檔案變更自動重載")
    
    args = parser.parse_args()
    
    print(f"🚀 啟動 DynaWatermark Web GUI")
    print(f"📍 網址: http://{args.host}:{args.port}")
    print(f"⚙️  按 Ctrl+C 停止伺服器")
    
    uvicorn.run(
        "dynawatermark.web.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
