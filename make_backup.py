import os
import sys
import shutil
import zipfile
from datetime import datetime

# Set output encoding to UTF-8 for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def backup_project():
    source_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(source_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Target folder & zip names
    folder_backup_name = "ระบบกิจกรรม - สำเนา"
    folder_backup_path = os.path.join(parent_dir, folder_backup_name)
    zip_backup_name = f"ระบบกิจกรรม_backup_{timestamp}.zip"
    zip_backup_path = os.path.join(parent_dir, zip_backup_name)
    latest_zip_path = os.path.join(parent_dir, "ระบบกิจกรรม_สำเนา.zip")
    local_zip_path = os.path.join(source_dir, "ระบบกิจกรรม_สำเนา.zip")

    # Exclude directories and files that are build artifacts or redundant
    exclude_dirs = {'.venv', '.git', '__pycache__', '.pytest_cache', '.idea', '.vscode'}
    exclude_files = {'ระบบกิจกรรม.zip', 'ระบบกิจกรรม_สำเนา.zip'}

    print("==================================================")
    print("   กำลังเริ่มต้นทำสำเนาโปรเจกต์ (Backup)...")
    print("==================================================")

    print(f"ต้นทาง: {source_dir}")

    # 1. ทำสำเนาเป็นโฟลเดอร์ (Directory Copy)
    if os.path.exists(folder_backup_path):
        try:
            shutil.rmtree(folder_backup_path)
        except Exception as e:
            print(f"Warning: Could not clear existing backup folder completely: {e}")

    def copy_ignore(path, names):
        ignored = set()
        for name in names:
            if name in exclude_dirs or name in exclude_files or name.endswith('.pyc'):
                ignored.add(name)
        return ignored

    print(f"\n[1/2] กำลังสร้างโฟลเดอร์สำเนา: {folder_backup_path}")
    shutil.copytree(source_dir, folder_backup_path, ignore=copy_ignore, dirs_exist_ok=True)
    print(" -> สำเนาโฟลเดอร์เรียบร้อยแล้ว!")

    # 2. ทำสำเนาเป็นไฟล์ Zip
    print(f"\n[2/2] กำลังสร้างไฟล์ ZIP สำเนา: {zip_backup_path}")
    file_count = 0
    with zipfile.ZipFile(zip_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude ignored directories in-place
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file in exclude_files or file.endswith('.zip'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                file_count += 1

    # Copy to latest zip paths for convenience
    shutil.copy2(zip_backup_path, latest_zip_path)
    shutil.copy2(zip_backup_path, local_zip_path)

    zip_size_mb = os.path.getsize(zip_backup_path) / (1024 * 1024)

    print("\n==================================================")
    print("   [SUCCESS] ทำสำเนาโปรเจกต์สำเร็จเรียบร้อย!")
    print("==================================================")
    print(f" - โฟลเดอร์สำเนา   : {folder_backup_path}")
    print(f" - ไฟล์ ZIP สำเนา : {zip_backup_path} ({zip_size_mb:.2f} MB)")
    print(f" - ไฟล์ ZIP ล่าสุด : {latest_zip_path}")
    print(f" - จำนวนไฟล์ทั้งหมด : {file_count} ไฟล์")
    print("==================================================")

if __name__ == "__main__":
    backup_project()
