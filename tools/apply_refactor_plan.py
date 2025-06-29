import os
import json
import shutil

ROOT_DIR = "/noctria_kingdom"
PLAN_PATH = os.path.join(ROOT_DIR, "logs", "refactor_plan.json")

def load_plan(path):
    with open(path, "r") as f:
        return json.load(f)

def apply_refactor_step(src_path, dst_path):
    abs_src = os.path.join(ROOT_DIR, src_path)
    abs_dst = os.path.join(ROOT_DIR, dst_path)

    if not os.path.exists(abs_src):
        print(f"⚠️ Not found: {src_path}")
        return

    os.makedirs(os.path.dirname(abs_dst), exist_ok=True)
    shutil.move(abs_src, abs_dst)
    print(f"📁 Moved: {src_path} → {dst_path}")

    # パスの参照も書き換え（importやopen等）
    update_references(src_path, dst_path)

def update_references(old_path, new_path):
    all_py_files = []

    for dirpath, _, filenames in os.walk(ROOT_DIR):
        for filename in filenames:
            if filename.endswith(".py"):
                all_py_files.append(os.path.join(dirpath, filename))

    old_import = path_to_import(old_path)
    new_import = path_to_import(new_path)

    for file_path in all_py_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_import in content or old_path in content:
            content = content.replace(old_import, new_import)
            content = content.replace(old_path, new_path)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✏️ Updated import in: {os.path.relpath(file_path, ROOT_DIR)}")

def path_to_import(path):
    return path.replace("/", ".").replace(".py", "")

def main():
    if not os.path.exists(PLAN_PATH):
        print(f"❌ No refactor plan found at {PLAN_PATH}")
        return

    plan = load_plan(PLAN_PATH)
    print(f"🧠 Applying {len(plan)} refactor steps...")

    for step in plan:
        apply_refactor_step(step["src"], step["dst"])

    print("✅ Refactoring complete!")

if __name__ == "__main__":
    main()
