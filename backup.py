import hashlib
import json
import shutil
import tarfile
import time
from datetime import datetime
from pathlib import Path
 
SOURCE = Path("company_data")      
BACKUP_DIR = Path("backups")       
KEEP_LAST = 8                     
 
 
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
 
 
def make_manifest(folder):
    """Контрольная сумма каждого файла: {относительный_путь: sha256}."""
    return {str(p.relative_to(folder)): sha256(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}
 
 
def create_backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = BACKUP_DIR / f"backup_{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(SOURCE, arcname=SOURCE.name)
    manifest = {"created": stamp, "archive_sha256": sha256(archive),
                "files": make_manifest(SOURCE)}
    archive.with_suffix("").with_suffix(".json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Создан {archive.name}, файлов: {len(manifest['files'])}, "
          f"размер: {archive.stat().st_size / 1024:.1f} КБ")
    return archive
 
 
def rotate():
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))
    for old in archives[:-KEEP_LAST]:
        old.unlink()
        old.with_suffix("").with_suffix(".json").unlink(missing_ok=True)
        print(f"[ROTATE] Удалена старая копия {old.name}")
 
 
def verify_restore(archive):
    """Проверяет архив и выводит различия между файлами."""
    manifest_path = archive.with_suffix("").with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if sha256(archive) != manifest["archive_sha256"]:
        print("[FAIL] Архив повреждён: контрольная сумма не совпадает")
        return False

    tmp = Path("restore_test")
    shutil.rmtree(tmp, ignore_errors=True)

    try:
        with tarfile.open(archive) as tar:
            tar.extractall(tmp, filter="data")

        restored = make_manifest(tmp / SOURCE.name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    expected = manifest["files"]

    missing = sorted(set(expected) - set(restored))
    extra = sorted(set(restored) - set(expected))
    changed = sorted(
        name
        for name in set(expected) & set(restored)
        if expected[name] != restored[name]
    )

    if not missing and not extra and not changed:
        print(
            f"[OK] Восстановление проверено: "
            f"{len(restored)} файлов совпадают"
        )
        return True

    print("[FAIL] Восстановленные данные не совпадают с манифестом")

    for name in missing:
        print(f"[ОТСУТСТВУЕТ] {name}")

    for name in extra:
        print(f"[ЛИШНИЙ] {name}")

    for name in changed:
        print(f"[ИЗМЕНЁН] {name}")

    print(
        f"Итого: отсутствует — {len(missing)}, "
        f"лишних — {len(extra)}, "
        f"изменено — {len(changed)}"
    )

    return False
 
def restore(archive):
    if not verify_restore(archive):
        print("[FAIL] Восстановление отменено: копия не прошла проверку")
        return False

    start = time.perf_counter()

    if SOURCE.exists():
        shutil.rmtree(SOURCE)

    with tarfile.open(archive) as tar:
        tar.extractall(Path("."), filter="data")

    elapsed = time.perf_counter() - start

    manifest_path = archive.with_suffix("").with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if make_manifest(SOURCE) != manifest["files"]:
        print("[FAIL] После восстановления файлы не совпадают")
        return False

    print(f"[OK] Данные восстановлены из {archive.name}")
    print(f"[OK] Восстановлено файлов: {len(manifest['files'])}")
    print(f"Время восстановления: {elapsed:.3f} с")
    return True
    
if __name__ == "__main__":
    archive = create_backup()
    rotate()
    verify_restore(archive)
