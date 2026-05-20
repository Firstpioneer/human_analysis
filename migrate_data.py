"""数据迁移脚本 — 将 ai-interview-engine 的数据迁移到统一 data/ 目录"""
import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "ai-interview-engine", "data")
NEW_DATA_DIR = os.path.join(BASE_DIR, "data")


def ensure_dirs():
    """确保新数据目录存在"""
    dirs = [
        os.path.join(NEW_DATA_DIR, "interviews"),
        os.path.join(NEW_DATA_DIR, "interviews", "records"),
        os.path.join(NEW_DATA_DIR, "profiles"),
        os.path.join(NEW_DATA_DIR, "candidates"),
        os.path.join(NEW_DATA_DIR, "conversations"),
        os.path.join(NEW_DATA_DIR, "resumes"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def migrate_interviews():
    """迁移面试记录"""
    old_index = os.path.join(OLD_DATA_DIR, "interviews.json")
    new_index = os.path.join(NEW_DATA_DIR, "interviews", "index.json")

    # 迁移 index
    if os.path.exists(old_index):
        with open(old_index, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(new_index, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  面试索引: {len(data.get('interviews', []))} 条记录")
    else:
        print("  面试索引: 未找到，跳过")

    # 迁移 individual records
    old_records_dir = os.path.join(OLD_DATA_DIR, "records")
    new_records_dir = os.path.join(NEW_DATA_DIR, "interviews", "records")
    if os.path.exists(old_records_dir):
        count = 0
        for filename in os.listdir(old_records_dir):
            if filename.endswith(".json"):
                src = os.path.join(old_records_dir, filename)
                dst = os.path.join(new_records_dir, filename)
                shutil.copy2(src, dst)
                count += 1
        print(f"  面试记录文件: {count} 个")


def migrate_profiles():
    """迁移面试格式的画像数据"""
    old_file = os.path.join(OLD_DATA_DIR, "profiles.json")
    new_file = os.path.join(NEW_DATA_DIR, "interviews", "profiles.json")
    if os.path.exists(old_file):
        with open(old_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(new_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  面试画像: {len(data.get('items', []))} 个")
    else:
        print("  面试画像: 未找到，跳过")


def migrate_candidates():
    """迁移候选人数据"""
    old_file = os.path.join(OLD_DATA_DIR, "candidates.json")
    new_file = os.path.join(NEW_DATA_DIR, "interviews", "candidates.json")
    if os.path.exists(old_file):
        with open(old_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(new_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  候选人: {len(data.get('items', []))} 个")
    else:
        print("  候选人: 未找到，跳过")


def copy_schemas():
    """复制 JSON Schema 文件"""
    old_schemas_dir = os.path.join(OLD_DATA_DIR, "schemas")
    new_schemas_dir = os.path.join(BASE_DIR, "app", "schemas")
    os.makedirs(new_schemas_dir, exist_ok=True)

    if os.path.exists(old_schemas_dir):
        count = 0
        for filename in os.listdir(old_schemas_dir):
            if filename.endswith(".json"):
                src = os.path.join(old_schemas_dir, filename)
                dst = os.path.join(new_schemas_dir, filename)
                shutil.copy2(src, dst)
                count += 1
        print(f"  JSON Schema: {count} 个文件")
    else:
        print("  JSON Schema: 未找到，跳过")


def main():
    print("=" * 50)
    print("  AI 招聘评估系统 — 数据迁移")
    print("=" * 50)

    if not os.path.exists(OLD_DATA_DIR):
        print(f"\n错误: 未找到旧数据目录 {OLD_DATA_DIR}")
        print("请确认 ai-interview-engine/data/ 目录存在。")
        return

    print(f"\n源目录: {OLD_DATA_DIR}")
    print(f"目标目录: {NEW_DATA_DIR}\n")

    ensure_dirs()

    print("[1/4] 迁移面试记录...")
    migrate_interviews()

    print("[2/4] 迁移画像数据...")
    migrate_profiles()

    print("[3/4] 迁移候选人数据...")
    migrate_candidates()

    print("[4/4] 复制 Schema 文件...")
    copy_schemas()

    print("\n" + "=" * 50)
    print("  迁移完成！")
    print("=" * 50)
    print(f"\n启动命令: python run.py")
    print(f"访问地址: http://localhost:8000")


if __name__ == "__main__":
    main()
