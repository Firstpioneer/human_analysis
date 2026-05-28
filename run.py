"""一键启动 AI 招聘评估系统"""
import uvicorn
from config import HOST, PORT

if __name__ == "__main__":
    print("=" * 50)
    print("  AI 招聘评估系统")
    print("=" * 50)
    print(f"  访问地址: http://{HOST}:{PORT}")
    print("=" * 50)
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
