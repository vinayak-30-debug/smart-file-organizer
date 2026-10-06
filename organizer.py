from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Iterable


ORGANIZED_FOLDER = "Organized_Files"
DEFAULT_CATEGORY = "Others"
DUPLICATES_CATEGORY = "Duplicates"
HISTORY_FILE = ".organizer_history.json"

FILE_CATEGORIES: dict[str, set[str]] = {
    "Images": {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".svg",
        ".ico",
        ".heic",
        ".tiff",
    },
    "Documents": {
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".rtf",
        ".odt",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".csv",
        ".json",
        ".xml",
        ".md",
    },
    "Videos": {
        ".mp4",
        ".mkv",
        ".mov",
        ".avi",
        ".wmv",
        ".flv",
        ".webm",
    },
    "Audio": {
        ".mp3",
        ".wav",
        ".aac",
        ".flac",
        ".ogg",
        ".m4a",
        ".wma",
    },
    "Archives": {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
    },
    "Code": {
        ".py",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".php",
        ".sql",
    },
    "Applications": {
        ".exe",
        ".msi",
        ".bat",
        ".cmd",
        ".apk",
    },
    "Fonts": {
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
    },
}


@dataclass(frozen=True)
class MoveResult:
    source: Path
    destination: Path
    category: str
    is_duplicate: bool = False
    file_hash: str = ""


def compute_file_hash(file_path: Path, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file efficiently using chunks."""
    hasher = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return ""


def index_existing_organized_hashes(organized_root: Path) -> dict[str, Path]:
    """Index SHA-256 hashes of all existing files already inside organized_root."""
    hashes: dict[str, Path] = {}
    if not organized_root.exists() or not organized_root.is_dir():
        return hashes

    for item in organized_root.rglob("*"):
        if not item.is_file():
            continue
        # Skip system, log, and history files
        if item.name in ("organizer.log", HISTORY_FILE):
            continue
        h = compute_file_hash(item)
        if h:
            hashes[h] = item
    return hashes


def normalize_extensions(extensions: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for extension in extensions:
        clean_extension = extension.strip().lower()
        if not clean_extension:
            continue
        if not clean_extension.startswith("."):
            clean_extension = f".{clean_extension}"
        normalized.add(clean_extension)
    return normalized


def sanitize_category_name(category: str) -> str:
    safe_name = "".join(
        character if character.isalnum() or character in (" ", "-", "_") else "_"
        for character in category.strip()
    )
    return safe_name or DEFAULT_CATEGORY


def normalize_custom_categories(
    custom_categories: dict[str, Iterable[str]] | None,
) -> dict[str, set[str]]:
    if not custom_categories:
        return {}

    normalized: dict[str, set[str]] = {}
    used_extensions: set[str] = set()

    for category, extensions in custom_categories.items():
        safe_category = sanitize_category_name(category)
        clean_extensions = normalize_extensions(extensions)
        clean_extensions -= used_extensions
        if not clean_extensions:
            continue

        normalized[safe_category] = clean_extensions
        used_extensions.update(clean_extensions)

    return normalized


def get_category(
    file_path: Path,
    custom_categories: dict[str, Iterable[str]] | None = None,
) -> str:
    """Return the folder category for a file based on its extension."""
    extension = file_path.suffix.lower()

    for category, extensions in normalize_custom_categories(custom_categories).items():
        if extension in extensions:
            return category

    for category, extensions in FILE_CATEGORIES.items():
        if extension in extensions:
            return category

    return DEFAULT_CATEGORY


def unique_destination(destination: Path) -> Path:
    """Avoid overwriting files by adding a number to duplicate names."""
    if not destination.exists():
        return destination

    parent = destination.parent
    stem = destination.stem
    suffix = destination.suffix
    counter = 1

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def validate_directory(directory: str | Path) -> Path:
    target_dir = Path(directory).expanduser().resolve()

    if not target_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {target_dir}")
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {target_dir}")

    return target_dir


def iter_organizable_files(
    target_dir: Path,
    organized_root: Path,
    recursive: bool = False,
) -> Iterable[Path]:
    candidates = target_dir.rglob("*") if recursive else target_dir.iterdir()

    for item in candidates:
        if not item.is_file():
            continue
        if item.is_relative_to(organized_root):
            continue
        yield item


def scan_directory(
    directory: str | Path,
    custom_categories: dict[str, Iterable[str]] | None = None,
    output_folder: str = ORGANIZED_FOLDER,
    recursive: bool = False,
    detect_duplicates: bool = True,
) -> list[MoveResult]:
    """Return the files that can be organized without moving them."""
    target_dir = validate_directory(directory)
    organized_root = target_dir / sanitize_category_name(output_folder)
    planned_files: list[MoveResult] = []

    seen_hashes: dict[str, Path] = {}
    if detect_duplicates:
        seen_hashes.update(index_existing_organized_hashes(organized_root))

    for item in iter_organizable_files(target_dir, organized_root, recursive):
        file_hash = compute_file_hash(item) if detect_duplicates else ""
        is_duplicate = False

        if detect_duplicates and file_hash:
            if file_hash in seen_hashes:
                is_duplicate = True
            else:
                seen_hashes[file_hash] = item

        if is_duplicate:
            category = DUPLICATES_CATEGORY
        else:
            category = get_category(item, custom_categories)

        destination = unique_destination(organized_root / category / item.name)
        planned_files.append(
            MoveResult(
                source=item,
                destination=destination,
                category=category,
                is_duplicate=is_duplicate,
                file_hash=file_hash,
            )
        )

    return planned_files


def organize_directory(
    directory: str | Path,
    custom_categories: dict[str, Iterable[str]] | None = None,
    output_folder: str = ORGANIZED_FOLDER,
    recursive: bool = False,
    detect_duplicates: bool = True,
    enable_logging: bool = True,
    enable_history: bool = True,
) -> list[MoveResult]:
    """Organize files into an Organized_Files folder with category subfolders."""
    target_dir = validate_directory(directory)
    organized_root = target_dir / sanitize_category_name(output_folder)
    moved_files: list[MoveResult] = []

    seen_hashes: dict[str, Path] = {}
    if detect_duplicates:
        seen_hashes.update(index_existing_organized_hashes(organized_root))

    for item in iter_organizable_files(target_dir, organized_root, recursive):
        file_hash = compute_file_hash(item) if detect_duplicates else ""
        is_duplicate = False

        if detect_duplicates and file_hash:
            if file_hash in seen_hashes:
                is_duplicate = True
            else:
                seen_hashes[file_hash] = item

        if is_duplicate:
            category = DUPLICATES_CATEGORY
        else:
            category = get_category(item, custom_categories)

        category_folder = organized_root / category
        category_folder.mkdir(parents=True, exist_ok=True)

        destination = unique_destination(category_folder / item.name)
        shutil.move(str(item), str(destination))
        moved_files.append(
            MoveResult(
                source=item,
                destination=destination,
                category=category,
                is_duplicate=is_duplicate,
                file_hash=file_hash,
            )
        )

    if enable_history and moved_files:
        record_history_session(organized_root, moved_files)

    if enable_logging:
        write_operation_log(organized_root, moved_files)

    return moved_files


def _get_history_file(organized_root: Path) -> Path:
    return organized_root / HISTORY_FILE


def load_history(organized_root: Path) -> list[dict[str, Any]]:
    history_file = _get_history_file(organized_root)
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def save_history(organized_root: Path, history: list[dict[str, Any]]) -> None:
    organized_root.mkdir(parents=True, exist_ok=True)
    history_file = _get_history_file(organized_root)
    if not history:
        if history_file.exists():
            try:
                history_file.unlink()
            except OSError:
                pass
        return
    history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")


def record_history_session(
    organized_root: Path,
    moved_files: list[MoveResult],
) -> str:
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    session_data = {
        "session_id": session_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "moves": [
            {
                "source": str(result.source),
                "destination": str(result.destination),
                "category": result.category,
                "is_duplicate": result.is_duplicate,
                "file_hash": result.file_hash,
            }
            for result in moved_files
        ],
    }
    history = load_history(organized_root)
    history.append(session_data)
    save_history(organized_root, history)
    return session_id


def can_undo(
    directory: str | Path,
    output_folder: str = ORGANIZED_FOLDER,
) -> bool:
    """Return True if an undoable operation exists for the given directory."""
    try:
        target_dir = validate_directory(directory)
        organized_root = target_dir / sanitize_category_name(output_folder)
        return len(load_history(organized_root)) > 0
    except (FileNotFoundError, NotADirectoryError):
        return False


def cleanup_empty_folders(root: Path) -> None:
    """Remove empty subdirectories within root, preserving root itself if not empty."""
    if not root.exists() or not root.is_dir():
        return

    for dirpath, dirnames, filenames in list(os.walk(root, topdown=False)):
        current_dir = Path(dirpath)
        if current_dir == root:
            continue
        try:
            if not any(current_dir.iterdir()):
                current_dir.rmdir()
        except OSError:
            pass


def undo_last_operation(
    directory: str | Path,
    output_folder: str = ORGANIZED_FOLDER,
    enable_logging: bool = True,
) -> list[MoveResult]:
    """Undo the most recent organize operation by moving files back to their original locations."""
    target_dir = validate_directory(directory)
    organized_root = target_dir / sanitize_category_name(output_folder)

    history = load_history(organized_root)
    if not history:
        raise RuntimeError("No previous operations found to undo.")

    latest_session = history.pop()
    moves = latest_session.get("moves", [])
    restored_files: list[MoveResult] = []

    # Process in reverse order of moves
    for item in reversed(moves):
        dest_path = Path(item["destination"])
        src_path = Path(item["source"])

        if not dest_path.exists():
            continue

        src_path.parent.mkdir(parents=True, exist_ok=True)
        restore_target = unique_destination(src_path)
        shutil.move(str(dest_path), str(restore_target))

        restored_files.append(
            MoveResult(
                source=dest_path,
                destination=restore_target,
                category=item.get("category", DEFAULT_CATEGORY),
                is_duplicate=item.get("is_duplicate", False),
                file_hash=item.get("file_hash", ""),
            )
        )

    save_history(organized_root, history)
    cleanup_empty_folders(organized_root)

    if enable_logging:
        write_undo_log(organized_root, latest_session.get("session_id", "unknown"), restored_files)

    return restored_files


def write_operation_log(organized_root: Path, moved_files: list[MoveResult]) -> None:
    organized_root.mkdir(parents=True, exist_ok=True)
    log_file = organized_root / "organizer.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] Operation started\n")
        if not moved_files:
            file.write("No files moved.\n")
        for result in moved_files:
            dup_tag = " [DUPLICATE]" if result.is_duplicate else ""
            file.write(
                f"{result.source} -> {result.destination} ({result.category}){dup_tag}\n"
            )
        file.write(f"Total files moved: {len(moved_files)}\n\n")


def write_undo_log(
    organized_root: Path,
    session_id: str,
    restored_files: list[MoveResult],
) -> None:
    organized_root.mkdir(parents=True, exist_ok=True)
    log_file = organized_root / "organizer.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] UNDO session {session_id}\n")
        if not restored_files:
            file.write("No files restored.\n")
        for result in restored_files:
            file.write(
                f"RESTORED: {result.source} -> {result.destination}\n"
            )
        file.write(f"Total files restored: {len(restored_files)}\n\n")
