"""一键启动 AI 招聘评估系统"""
import uvicorn
from config import HOST, PORT

if __name__ == "__main__":
    browser_host = "127.0.0.1" if HOST in {"0.0.0.0", "::"} else HOST
    print("=" * 50)
    print("  AI 招聘评估系统")
    print("=" * 50)
    print(f"  访问地址: http://{browser_host}:{PORT}")
    if browser_host != HOST:
        print(f"  监听地址: http://{HOST}:{PORT}")
    print("=" * 50)
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
