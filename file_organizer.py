"""
Folder Organizer - A Windows desktop application that organizes files by type and date.

Organizes files into: [Category]/[Year]/[Month]/files
"""

import os
import json
import shutil
import stat
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum
import ctypes
import threading
import queue
import time

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    try:
        from ttkbootstrap.widgets.scrolled import ScrolledFrame
    except ImportError:
        from ttkbootstrap.scrolled import ScrolledFrame
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    from tkinter import ttk
    TTKBOOTSTRAP_AVAILABLE = False

# Directory where backup files are stored (same as script location)
BACKUP_DIR = Path(__file__).parent / "backups"

# Application info
APP_NAME = "Folder Organizer"
APP_VERSION = "2.2.0"

# Windows path length limit
MAX_PATH_LENGTH = 260

# System folders to warn about
SYSTEM_FOLDERS = {
    "windows", "program files", "program files (x86)", "programdata",
    "system32", "syswow64", "$recycle.bin", "recovery", "boot"
}

# Unicode icons
ICON_FOLDER = "\U0001F4C1"
ICON_CALENDAR = "\U0001F4C5"
ICON_CHECK = "\u2713"
ICON_WARNING = "\u26A0"
ICON_ERROR = "\u2717"
ICON_ARROW = "\u2192"
ICON_FILE = "\U0001F4C4"


class SortMode(Enum):
    """File organization modes."""
    BY_TYPE = "type"
    BY_DATE = "date"
    BY_BOTH = "both"


class SkipReason(Enum):
    """Reasons for skipping a file."""
    ALREADY_ORGANIZED = "Already in organized structure"
    PERMISSION_DENIED = "Permission denied"
    FILE_IN_USE = "File is in use"
    READ_ONLY = "File is read-only"
    SYSTEM_FILE = "System file"
    HIDDEN_FILE = "Hidden file (excluded)"
    SYMLINK = "Symlink/shortcut (excluded)"
    PATH_TOO_LONG = "Destination path too long"
    INVALID_DATE = "Invalid date metadata"
    MOVE_ERROR = "Error during move"


# Extension to category mapping
EXTENSION_CATEGORIES = {
    # Images
    '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
    '.bmp': 'Images', '.webp': 'Images', '.svg': 'Images', '.ico': 'Images',
    '.tiff': 'Images', '.tif': 'Images', '.raw': 'Images', '.heic': 'Images',
    '.heif': 'Images', '.avif': 'Images',
    # Documents
    '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
    '.txt': 'Documents', '.xlsx': 'Documents', '.pptx': 'Documents',
    '.xls': 'Documents', '.ppt': 'Documents', '.odt': 'Documents',
    '.rtf': 'Documents', '.csv': 'Documents', '.md': 'Documents',
    '.epub': 'Documents', '.mobi': 'Documents',
    # Videos
    '.mp4': 'Videos', '.avi': 'Videos', '.mov': 'Videos',
    '.mkv': 'Videos', '.wmv': 'Videos', '.flv': 'Videos',
    '.webm': 'Videos', '.m4v': 'Videos', '.mpeg': 'Videos',
    '.mpg': 'Videos', '.3gp': 'Videos',
    # Audio
    '.mp3': 'Audio', '.wav': 'Audio', '.flac': 'Audio', '.aac': 'Audio',
    '.wma': 'Audio', '.ogg': 'Audio', '.m4a': 'Audio', '.opus': 'Audio',
    '.aiff': 'Audio', '.mid': 'Audio', '.midi': 'Audio',
    # Archives
    '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives',
    '.tar': 'Archives', '.gz': 'Archives', '.bz2': 'Archives',
    '.xz': 'Archives', '.iso': 'Archives', '.dmg': 'Archives',
    # Code
    '.py': 'Code', '.js': 'Code', '.html': 'Code', '.css': 'Code',
    '.java': 'Code', '.cpp': 'Code', '.c': 'Code', '.h': 'Code',
    '.json': 'Code', '.xml': 'Code', '.sql': 'Code', '.php': 'Code',
    '.rb': 'Code', '.go': 'Code', '.rs': 'Code', '.ts': 'Code',
    '.jsx': 'Code', '.tsx': 'Code', '.vue': 'Code', '.swift': 'Code',
    '.kt': 'Code', '.scala': 'Code', '.sh': 'Code', '.bat': 'Code',
    '.ps1': 'Code', '.yaml': 'Code', '.yml': 'Code', '.toml': 'Code',
    # Executables
    '.exe': 'Executables', '.msi': 'Executables', '.app': 'Executables',
    '.deb': 'Executables', '.rpm': 'Executables', '.apk': 'Executables',
    # Fonts
    '.ttf': 'Fonts', '.otf': 'Fonts', '.woff': 'Fonts', '.woff2': 'Fonts',
    '.eot': 'Fonts',
}

COMPOUND_EXTENSIONS = {
    '.tar.gz': 'Archives',
    '.tar.bz2': 'Archives',
    '.tar.xz': 'Archives',
    '.tar.zst': 'Archives',
}

MONTH_NAMES = {
    1: '01-January', 2: '02-February', 3: '03-March', 4: '04-April',
    5: '05-May', 6: '06-June', 7: '07-July', 8: '08-August',
    9: '09-September', 10: '10-October', 11: '11-November', 12: '12-December'
}


@dataclass
class FileMove:
    """Represents a planned file move operation."""
    source: Path
    destination: Path
    category: str
    year: int
    month: int


@dataclass
class SkippedFile:
    """Represents a file that was skipped during processing."""
    path: Path
    reason: SkipReason
    details: str = ""


@dataclass
class OrganizeResult:
    """Result of an organize operation."""
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)
    skipped_files: list = field(default_factory=list)
    move_log: list = field(default_factory=list)
    cancelled: bool = False


@dataclass
class BackupInfo:
    """Information about a backup file."""
    filepath: Path
    timestamp: datetime
    source_folder: str
    file_count: int


@dataclass
class ScanOptions:
    """Options for file scanning."""
    include_hidden: bool = False
    include_symlinks: bool = False
    delete_empty_folders: bool = False


def is_hidden_file(file_path: Path) -> bool:
    """Check if a file is hidden."""
    try:
        if file_path.name.startswith('.'):
            return True
        if os.name == 'nt':
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            if attrs != -1:
                return bool(attrs & 0x2)
    except Exception:
        pass
    return False


def is_system_file(file_path: Path) -> bool:
    """Check if a file is a system file."""
    try:
        if os.name == 'nt':
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            if attrs != -1:
                return bool(attrs & 0x4)
    except Exception:
        pass
    return False


def is_file_locked(file_path: Path) -> bool:
    """Check if a file is locked/in use."""
    try:
        with open(file_path, 'r+b'):
            pass
        return False
    except (IOError, PermissionError):
        return True
    except Exception:
        return False


def is_symlink_or_shortcut(file_path: Path) -> bool:
    """Check if a file is a symlink or Windows shortcut."""
    return file_path.is_symlink() or file_path.suffix.lower() == '.lnk'


def is_system_folder(folder_path: Path) -> bool:
    """Check if a folder is a system folder."""
    path_lower = str(folder_path).lower()
    if len(str(folder_path)) <= 3:
        return True
    for sys_folder in SYSTEM_FOLDERS:
        if sys_folder in path_lower:
            return True
    if os.name == 'nt':
        try:
            windows_dir = os.environ.get('WINDIR', 'C:\\Windows').lower()
            if path_lower.startswith(windows_dir):
                return True
        except Exception:
            pass
    return False


def get_compound_extension(file_path: Path) -> Optional[str]:
    """Get compound extension like .tar.gz if applicable."""
    name_lower = file_path.name.lower()
    for compound_ext in COMPOUND_EXTENSIONS:
        if name_lower.endswith(compound_ext):
            return compound_ext
    return None


def count_files_in_folder(folder_path: Path) -> int:
    """Count files in a folder (non-recursive, quick count)."""
    try:
        return sum(1 for f in folder_path.iterdir() if f.is_file())
    except Exception:
        return 0


def delete_empty_folders(folder_path: Path, progress_callback: Callable[[str], None] = None) -> int:
    """Delete empty folders recursively."""
    deleted = 0
    for dirpath, dirnames, filenames in os.walk(str(folder_path), topdown=False):
        dir_path = Path(dirpath)
        if dir_path == folder_path:
            continue
        try:
            if not any(dir_path.iterdir()):
                if progress_callback:
                    progress_callback(f"Deleting empty folder: {dir_path.name}")
                dir_path.rmdir()
                deleted += 1
        except (PermissionError, OSError):
            pass
    return deleted


class FileOrganizer:
    """Handles the file organization logic."""

    def __init__(self, source_folder: str, sort_mode: SortMode = SortMode.BY_BOTH,
                 options: ScanOptions = None):
        self.source_folder = Path(source_folder)
        self.sort_mode = sort_mode
        self.options = options or ScanOptions()
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def reset_cancel(self):
        self._cancel_requested = False

    def get_category(self, file_path: Path) -> str:
        compound_ext = get_compound_extension(file_path)
        if compound_ext:
            return COMPOUND_EXTENSIONS[compound_ext]
        ext = file_path.suffix.lower()
        if not ext:
            return 'No Extension'
        return EXTENSION_CATEGORIES.get(ext, 'Other')

    def get_file_date(self, file_path: Path) -> tuple[datetime, bool]:
        try:
            stat_info = file_path.stat()
            ctime = stat_info.st_ctime
            mtime = stat_info.st_mtime
            timestamp = min(ctime, mtime)
            dt = datetime.fromtimestamp(timestamp)
            if dt.year < 1980 or dt.year > datetime.now().year + 1:
                dt = datetime.fromtimestamp(mtime)
                if dt.year < 1980 or dt.year > datetime.now().year + 1:
                    return (None, False)
            return (dt, True)
        except (OSError, ValueError, OverflowError):
            return (None, False)

    def get_destination_path(self, file_path: Path, file_date: Optional[datetime] = None) -> Path:
        category = self.get_category(file_path)
        if file_date:
            year = str(file_date.year)
            month = MONTH_NAMES[file_date.month]
        else:
            year = "Unknown"
            month = "Unknown"

        if self.sort_mode == SortMode.BY_TYPE:
            return self.source_folder / category / file_path.name
        elif self.sort_mode == SortMode.BY_DATE:
            return self.source_folder / year / month / file_path.name
        else:
            return self.source_folder / category / year / month / file_path.name

    def check_path_length(self, dest_path: Path) -> bool:
        return len(str(dest_path)) <= MAX_PATH_LENGTH

    def get_unique_destination(self, dest_path: Path) -> Path:
        if not dest_path.exists():
            return dest_path
        stem = dest_path.stem
        suffix = dest_path.suffix
        parent = dest_path.parent
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
            if counter > 10000:
                raise RuntimeError("Too many duplicate files")

    def is_in_correct_location(self, file_path: Path, dest_path: Path) -> bool:
        try:
            return file_path.resolve() == dest_path.resolve()
        except OSError:
            return False

    def is_in_organized_structure(self, file_path: Path) -> bool:
        try:
            relative = file_path.relative_to(self.source_folder)
        except ValueError:
            return False
        parts = relative.parts
        valid_categories = set(EXTENSION_CATEGORIES.values()) | {'Other', 'No Extension'}

        if self.sort_mode == SortMode.BY_TYPE:
            if len(parts) >= 2:
                return parts[0] in valid_categories
        elif self.sort_mode == SortMode.BY_DATE:
            if len(parts) >= 3:
                year, month = parts[0], parts[1]
                if (year.isdigit() and len(year) == 4) or year == "Unknown":
                    if month in MONTH_NAMES.values() or month == "Unknown":
                        return True
        else:
            if len(parts) >= 4:
                category, year, month = parts[0], parts[1], parts[2]
                if category in valid_categories:
                    if (year.isdigit() and len(year) == 4) or year == "Unknown":
                        if month in MONTH_NAMES.values() or month == "Unknown":
                            return True
        return False

    def check_file_accessibility(self, file_path: Path, check_lock: bool = True) -> Optional[SkipReason]:
        """Check if file can be accessed. Set check_lock=False for faster scanning."""
        try:
            if not self.options.include_symlinks and is_symlink_or_shortcut(file_path):
                return SkipReason.SYMLINK
            if not self.options.include_hidden and is_hidden_file(file_path):
                return SkipReason.HIDDEN_FILE
            if is_system_file(file_path):
                return SkipReason.SYSTEM_FILE
            # Only check lock when actually moving (expensive operation)
            if check_lock and is_file_locked(file_path):
                return SkipReason.FILE_IN_USE
        except PermissionError:
            return SkipReason.PERMISSION_DENIED
        except Exception:
            return SkipReason.PERMISSION_DENIED
        return None

    def _scan_directory_fast(self, directory: Path):
        """Fast recursive directory scan using os.scandir."""
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if self._cancel_requested:
                        return
                    try:
                        if entry.is_file(follow_symlinks=False):
                            yield Path(entry.path)
                        elif entry.is_dir(follow_symlinks=False):
                            yield from self._scan_directory_fast(Path(entry.path))
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass

    def scan_files(self, progress_callback: Callable[[str, int], None] = None) -> tuple[list[FileMove], list[SkippedFile]]:
        """Scan files with optimized performance. Callback receives (status_msg, file_count)."""
        planned_moves = []
        skipped_files = []
        self.reset_cancel()

        file_count = 0
        last_update = time.time()
        update_interval = 0.1  # Update UI every 100ms max

        for file_path in self._scan_directory_fast(self.source_folder):
            if self._cancel_requested:
                break

            file_count += 1

            # Batch UI updates for performance
            now = time.time()
            if progress_callback and (now - last_update) >= update_interval:
                progress_callback(f"Scanning: {file_count} files found...", file_count)
                last_update = now

            if self.is_in_organized_structure(file_path):
                continue

            # Skip lock check during scan for speed - will check before move
            skip_reason = self.check_file_accessibility(file_path, check_lock=False)
            if skip_reason:
                skipped_files.append(SkippedFile(file_path, skip_reason))
                continue

            file_date, date_valid = self.get_file_date(file_path)
            dest_path = self.get_destination_path(file_path, file_date)

            if not self.check_path_length(dest_path):
                skipped_files.append(SkippedFile(
                    file_path, SkipReason.PATH_TOO_LONG,
                    f"Path would be {len(str(dest_path))} chars"
                ))
                continue

            if self.is_in_correct_location(file_path, dest_path):
                continue

            planned_moves.append(FileMove(
                source=file_path,
                destination=dest_path,
                category=self.get_category(file_path),
                year=file_date.year if file_date else 0,
                month=file_date.month if file_date else 0
            ))

        # Final update
        if progress_callback:
            progress_callback(f"Scan complete: {file_count} files processed", file_count)

        return planned_moves, skipped_files

    def execute_moves(self, planned_moves: list[FileMove],
                      progress_callback: Callable[[int, int, str], None] = None) -> OrganizeResult:
        """Execute file moves with batched progress updates."""
        result = OrganizeResult()
        total = len(planned_moves)
        self.reset_cancel()

        last_update = time.time()
        update_interval = 0.05  # Update UI every 50ms max for moves

        for i, move in enumerate(planned_moves):
            if self._cancel_requested:
                result.cancelled = True
                break

            # Batch UI updates
            now = time.time()
            if progress_callback and (now - last_update) >= update_interval:
                progress_callback(i + 1, total, move.source.name)
                last_update = now

            try:
                # Full accessibility check including lock check before move
                skip_reason = self.check_file_accessibility(move.source, check_lock=True)
                if skip_reason:
                    result.skipped += 1
                    result.skipped_files.append(SkippedFile(move.source, skip_reason))
                    continue

                move.destination.parent.mkdir(parents=True, exist_ok=True)
                final_dest = self.get_unique_destination(move.destination)

                if not self.check_path_length(final_dest):
                    result.skipped += 1
                    result.skipped_files.append(SkippedFile(move.source, SkipReason.PATH_TOO_LONG))
                    continue

                original_path = str(move.source.resolve())
                shutil.move(str(move.source), str(final_dest))
                result.moved += 1
                result.move_log.append((original_path, str(final_dest.resolve())))

            except PermissionError as e:
                result.skipped += 1
                result.skipped_files.append(SkippedFile(move.source, SkipReason.PERMISSION_DENIED, str(e)))
            except OSError as e:
                if "being used" in str(e).lower() or "in use" in str(e).lower():
                    result.skipped += 1
                    result.skipped_files.append(SkippedFile(move.source, SkipReason.FILE_IN_USE, str(e)))
                else:
                    result.errors += 1
                    result.error_messages.append(f"{move.source.name}: {str(e)}")
            except Exception as e:
                result.errors += 1
                result.error_messages.append(f"{move.source.name}: {str(e)}")

        # Final progress update
        if progress_callback:
            progress_callback(total, total, "Complete")

        return result


class BackupManager:
    """Manages backup and restore operations."""

    @staticmethod
    def save_backup(source_folder: str, move_log: list[tuple[str, str]],
                    sort_mode: str, skipped_files: list[SkippedFile] = None) -> Path:
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now()
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = BACKUP_DIR / filename

        backup_data = {
            "timestamp": timestamp.isoformat(),
            "source_folder": source_folder,
            "sort_mode": sort_mode,
            "file_count": len(move_log),
            "moves": [{"original": orig, "destination": dest} for orig, dest in move_log],
            "skipped": [
                {"path": str(sf.path), "reason": sf.reason.value, "details": sf.details}
                for sf in (skipped_files or [])
            ]
        }

        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        return backup_path

    @staticmethod
    def list_backups() -> list[BackupInfo]:
        if not BACKUP_DIR.exists():
            return []
        backups = []
        for filepath in BACKUP_DIR.glob("backup_*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                backups.append(BackupInfo(
                    filepath=filepath,
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    source_folder=data["source_folder"],
                    file_count=data["file_count"]
                ))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups

    @staticmethod
    def load_backup(filepath: Path) -> dict:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def execute_restore(backup_data: dict,
                        progress_callback: Callable[[int, int, str], None] = None,
                        cancel_check: Callable[[], bool] = None) -> OrganizeResult:
        result = OrganizeResult()
        moves = backup_data["moves"]
        total = len(moves)

        for i, move in enumerate(moves):
            if cancel_check and cancel_check():
                result.cancelled = True
                break

            original = Path(move["original"])
            destination = Path(move["destination"])

            if progress_callback:
                progress_callback(i + 1, total, destination.name)

            try:
                if not destination.exists():
                    result.skipped += 1
                    result.skipped_files.append(SkippedFile(
                        destination, SkipReason.MOVE_ERROR, "File not found"
                    ))
                    continue

                original.parent.mkdir(parents=True, exist_ok=True)
                final_original = original
                if original.exists():
                    stem, suffix = original.stem, original.suffix
                    counter = 1
                    while final_original.exists():
                        final_original = original.parent / f"{stem}_restored_{counter}{suffix}"
                        counter += 1

                shutil.move(str(destination), str(final_original))
                result.moved += 1
                result.move_log.append((str(destination), str(final_original)))

            except PermissionError as e:
                result.skipped += 1
                result.skipped_files.append(SkippedFile(destination, SkipReason.PERMISSION_DENIED, str(e)))
            except Exception as e:
                result.errors += 1
                result.error_messages.append(f"{destination.name}: {str(e)}")

        return result

    @staticmethod
    def delete_backup(filepath: Path) -> bool:
        try:
            filepath.unlink()
            return True
        except OSError:
            return False


class FileOrganizerApp:
    """Main application GUI using ttkbootstrap."""

    def __init__(self):
        # Create window with ttkbootstrap theme
        if TTKBOOTSTRAP_AVAILABLE:
            self.root = ttk.Window(themename="superhero")
        else:
            self.root = tk.Tk()

        self.root.title(APP_NAME)
        self.root.geometry("850x900")
        self.root.minsize(750, 800)

        # Variables
        self.selected_folder = tk.StringVar()
        self.sort_mode = tk.StringVar(value=SortMode.BY_BOTH.value)
        self.include_hidden = tk.BooleanVar(value=False)
        self.include_symlinks = tk.BooleanVar(value=False)
        self.delete_empty = tk.BooleanVar(value=False)

        self.planned_moves: list[FileMove] = []
        self.skipped_files: list[SkippedFile] = []
        self.organizer: Optional[FileOrganizer] = None
        self.is_processing = False
        self.file_count = 0

        # Threading support
        self._task_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None

        self._create_widgets()
        self._center_window()

        # Start polling for task results
        self._poll_task_queue()

    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _poll_task_queue(self):
        """Poll the task queue for updates from worker thread."""
        try:
            while True:
                task = self._task_queue.get_nowait()
                task_type = task.get("type")

                if task_type == "status":
                    self.status_var.set(task["message"])
                elif task_type == "progress":
                    self._set_progress(task["percent"])
                    if "message" in task:
                        self.status_var.set(task["message"])
                elif task_type == "scan_complete":
                    self._on_scan_complete(task["moves"], task["skipped"], task["cancelled"])
                elif task_type == "organize_complete":
                    self._on_organize_complete(task["result"], task["all_skipped"], task["backup_path"])
        except queue.Empty:
            pass

        # Continue polling
        self.root.after(50, self._poll_task_queue)

    def _run_in_thread(self, target, *args):
        """Run a function in a background thread."""
        self._worker_thread = threading.Thread(target=target, args=args, daemon=True)
        self._worker_thread.start()

    def _create_widgets(self):
        # Main container with padding
        self.main_frame = ttk.Frame(self.root, padding=30)
        self.main_frame.pack(fill="both", expand=True)

        self._create_header()
        self._create_folder_section()
        self._create_mode_section()
        self._create_options_section()
        self._create_action_buttons()
        self._create_progress_section()
        self._create_results_section()
        self._create_footer()

    def _bootstyle(self, style: str) -> dict:
        """Return bootstyle kwarg only if ttkbootstrap is available."""
        if TTKBOOTSTRAP_AVAILABLE:
            return {"bootstyle": style}
        return {}

    def _create_header(self):
        header = ttk.Frame(self.main_frame)
        header.pack(fill="x", pady=(0, 20))

        title = ttk.Label(header, text=APP_NAME, font=("Segoe UI", 28, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(header, text="Automatically organize your files by type and date",
                            font=("Segoe UI", 11), **self._bootstyle("secondary"))
        subtitle.pack(anchor="w", pady=(4, 0))

    def _create_folder_section(self):
        card = ttk.Labelframe(self.main_frame, text=f"  {ICON_FOLDER}  Select Folder  ", padding=20)
        card.pack(fill="x", pady=(0, 15))

        # Folder info label (shows after selection)
        self.folder_info = ttk.Label(card, text="No folder selected", **self._bootstyle("secondary"))
        self.folder_info.pack(anchor="w", pady=(0, 10))

        # Input row
        input_row = ttk.Frame(card)
        input_row.pack(fill="x")

        self.folder_entry = ttk.Entry(input_row, textvariable=self.selected_folder,
                                     font=("Segoe UI", 10), state="readonly")
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_btn = ttk.Button(input_row, text="Browse...", command=self._browse_folder,
                                     **self._bootstyle("secondary"))
        self.browse_btn.pack(side="right")

    def _create_mode_section(self):
        card = ttk.Labelframe(self.main_frame, text="  Organization Mode  ", padding=20)
        card.pack(fill="x", pady=(0, 15))

        modes = [
            (SortMode.BY_TYPE.value, f"{ICON_FOLDER}  By Type",
             "Organize into category folders: Images/, Documents/, Videos/..."),
            (SortMode.BY_DATE.value, f"{ICON_CALENDAR}  By Date",
             "Organize by year and month: 2024/01-January/..."),
            (SortMode.BY_BOTH.value, f"{ICON_FOLDER} {ICON_CALENDAR}  By Type & Date  (Recommended)",
             "Combined: Images/2024/01-January/..."),
        ]

        for value, label, desc in modes:
            frame = ttk.Frame(card)
            frame.pack(fill="x", pady=4)

            rb = ttk.Radiobutton(frame, text=label, variable=self.sort_mode, value=value,
                                **self._bootstyle("primary-toolbutton"))
            rb.pack(anchor="w")

            desc_label = ttk.Label(frame, text=desc, font=("Segoe UI", 9), **self._bootstyle("secondary"))
            desc_label.pack(anchor="w", padx=(28, 0))

    def _create_options_section(self):
        card = ttk.Labelframe(self.main_frame, text="  Options  ", padding=20)
        card.pack(fill="x", pady=(0, 15))

        options_frame = ttk.Frame(card)
        options_frame.pack(fill="x")

        # Row 1
        row1 = ttk.Frame(options_frame)
        row1.pack(fill="x", pady=4)

        cb_hidden = ttk.Checkbutton(row1, text="Include hidden files", variable=self.include_hidden,
                                    **self._bootstyle("round-toggle"))
        cb_hidden.pack(side="left", padx=(0, 40))

        cb_symlinks = ttk.Checkbutton(row1, text="Include shortcuts & symlinks",
                                     variable=self.include_symlinks,
                                     **self._bootstyle("round-toggle"))
        cb_symlinks.pack(side="left")

        # Row 2
        row2 = ttk.Frame(options_frame)
        row2.pack(fill="x", pady=4)

        cb_empty = ttk.Checkbutton(row2, text="Delete empty folders after organizing",
                                  variable=self.delete_empty,
                                  **self._bootstyle("round-toggle"))
        cb_empty.pack(side="left")

    def _create_action_buttons(self):
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(0, 20))

        # Left side buttons
        left_btns = ttk.Frame(btn_frame)
        left_btns.pack(side="left")

        self.preview_btn = ttk.Button(left_btns, text="Preview Changes", command=self._preview,
                                      **self._bootstyle("info-outline"))
        self.preview_btn.pack(side="left", padx=(0, 10))

        self.organize_btn = ttk.Button(left_btns, text="Organize Files", command=self._organize,
                                       **self._bootstyle("success"))
        self.organize_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ttk.Button(left_btns, text="Cancel", command=self._cancel_operation,
                                     **self._bootstyle("danger"))
        # Hidden initially

        # Right side
        self.restore_btn = ttk.Button(btn_frame, text="Restore...", command=self._show_restore_dialog,
                                      **self._bootstyle("secondary-link"))
        self.restore_btn.pack(side="right")

        self._update_button_states()

    def _create_progress_section(self):
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_frame.pack(fill="x", pady=(0, 15))

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate",
                                            **self._bootstyle("success-striped"))
        self.progress_bar.pack(fill="x")

        # Status row
        status_row = ttk.Frame(self.progress_frame)
        status_row.pack(fill="x", pady=(8, 0))

        self.status_var = tk.StringVar(value="Select a folder to get started")
        self.status_label = ttk.Label(status_row, textvariable=self.status_var,
                                     font=("Segoe UI", 10), **self._bootstyle("secondary"))
        self.status_label.pack(side="left")

        self.progress_pct = ttk.Label(status_row, text="", font=("Segoe UI", 10, "bold"),
                                     **self._bootstyle("success"))
        self.progress_pct.pack(side="right")

    def _create_results_section(self):
        card = ttk.Labelframe(self.main_frame, text="  Results  ", padding=15)
        card.pack(fill="both", expand=True, pady=(0, 15))

        # Header with summary
        header_row = ttk.Frame(card)
        header_row.pack(fill="x", pady=(0, 10))

        self.results_summary = ttk.Label(header_row, text="", **self._bootstyle("secondary"))
        self.results_summary.pack(side="right")

        # Status indicator frame (shown after operations)
        self.status_indicator = ttk.Frame(card)

        # Results container with scrollbar
        if TTKBOOTSTRAP_AVAILABLE:
            self.results_scroll = ScrolledFrame(card, autohide=True)
            self.results_scroll.pack(fill="both", expand=True)
            self.results_inner = self.results_scroll
        else:
            results_container = ttk.Frame(card)
            results_container.pack(fill="both", expand=True)

            canvas = tk.Canvas(results_container, highlightthickness=0)
            scrollbar = ttk.Scrollbar(results_container, orient="vertical", command=canvas.yview)

            self.results_inner = ttk.Frame(canvas)
            self.results_inner.bind("<Configure>",
                                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

            canvas.create_window((0, 0), window=self.results_inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            canvas.bind_all("<MouseWheel>",
                           lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _create_footer(self):
        footer = ttk.Frame(self.main_frame)
        footer.pack(fill="x")

        version = ttk.Label(footer, text=f"v{APP_VERSION}", font=("Segoe UI", 9),
                           **self._bootstyle("secondary"))
        version.pack(side="right")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Organize")
        if folder:
            folder_path = Path(folder)

            if is_system_folder(folder_path):
                if not messagebox.askyesno(
                    "Warning",
                    f"{ICON_WARNING} This appears to be a system folder.\n\n"
                    "Organizing files here could cause problems.\n\n"
                    "Are you sure you want to continue?",
                    icon="warning"
                ):
                    return

            self.selected_folder.set(folder)
            self.planned_moves = []
            self.skipped_files = []
            self._clear_results()
            self._update_button_states()

            # Count files and update info
            self.file_count = count_files_in_folder(folder_path)
            folder_name = folder_path.name
            self.folder_info.configure(text=f"{ICON_FOLDER}  {folder_name}  -  {self.file_count} files")

            self.status_var.set("Folder selected. Click 'Preview Changes' to see what will happen.")
            self._set_progress(0)

    def _update_button_states(self):
        has_folder = bool(self.selected_folder.get())
        enabled = has_folder and not self.is_processing

        state = "normal" if enabled else "disabled"
        self.preview_btn.configure(state=state)
        self.organize_btn.configure(state=state)
        self.browse_btn.configure(state="normal" if not self.is_processing else "disabled")
        self.restore_btn.configure(state="normal" if not self.is_processing else "disabled")

    def _show_cancel_button(self, show: bool):
        if show:
            self.cancel_btn.pack(side="left", padx=(0, 10))
        else:
            self.cancel_btn.pack_forget()

    def _cancel_operation(self):
        if self.organizer:
            self.organizer.request_cancel()
            self.status_var.set("Cancelling...")

    def _clear_results(self):
        for widget in self.results_inner.winfo_children():
            widget.destroy()
        self.results_summary.configure(text="")
        self.status_indicator.pack_forget()

    def _set_progress(self, percent: float):
        self.progress_bar["value"] = percent
        if percent > 0:
            self.progress_pct.configure(text=f"{int(percent)}%")
        else:
            self.progress_pct.configure(text="")

    def _add_result_header(self, text: str, icon: str = "", style: str = ""):
        frame = ttk.Frame(self.results_inner)
        frame.pack(fill="x", pady=(12, 6))

        full_text = f"{icon}  {text}" if icon else text
        label = ttk.Label(frame, text=full_text, font=("Segoe UI", 11, "bold"),
                         **self._bootstyle(style) if style else {})
        label.pack(side="left")

    def _add_result_item(self, icon: str, text: str, style: str = "", indent: int = 0):
        frame = ttk.Frame(self.results_inner, padding=(indent * 20, 2, 0, 2))
        frame.pack(fill="x")

        full_text = f"{icon}  {text}" if icon else text
        label = ttk.Label(frame, text=full_text, font=("Segoe UI", 10),
                         **self._bootstyle(style) if style else {})
        label.pack(side="left")

    def _add_tree_item(self, text: str, level: int = 0):
        frame = ttk.Frame(self.results_inner)
        frame.pack(fill="x", pady=1)

        indent = "    " * level
        prefix = "--- " if level > 0 else ""

        label = ttk.Label(frame, text=f"{indent}{prefix}{text}",
                         font=("Consolas", 10), **self._bootstyle("secondary"))
        label.pack(side="left")

    def _show_success_state(self, moved: int, skipped: int, errors: int):
        self.status_indicator.pack(fill="x", pady=(0, 12))
        for widget in self.status_indicator.winfo_children():
            widget.destroy()

        if errors == 0 and skipped == 0:
            style = "success"
            indicator_text = f"{ICON_CHECK}  Successfully organized {moved} files"
        elif errors > 0:
            style = "danger"
            indicator_text = f"{ICON_ERROR}  Completed with {errors} errors"
        else:
            style = "warning"
            indicator_text = f"{ICON_WARNING}  Completed with {skipped} files skipped"

        indicator = ttk.Label(self.status_indicator, text=indicator_text,
                             font=("Segoe UI", 12, "bold"),
                             **self._bootstyle(f"inverse-{style}"))
        indicator.pack(fill="x", pady=12)

    def _get_sort_mode(self) -> SortMode:
        value = self.sort_mode.get()
        for mode in SortMode:
            if mode.value == value:
                return mode
        return SortMode.BY_BOTH

    def _get_scan_options(self) -> ScanOptions:
        return ScanOptions(
            include_hidden=self.include_hidden.get(),
            include_symlinks=self.include_symlinks.get(),
            delete_empty_folders=self.delete_empty.get()
        )

    def _preview(self):
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        self._clear_results()
        self._set_progress(0)
        self.status_var.set("Scanning files...")
        self.is_processing = True
        self._update_button_states()
        self._show_cancel_button(True)

        sort_mode = self._get_sort_mode()
        options = self._get_scan_options()
        self.organizer = FileOrganizer(folder, sort_mode, options)

        # Run scan in background thread
        self._run_in_thread(self._scan_worker, folder, sort_mode, options)

    def _scan_worker(self, folder: str, sort_mode: SortMode, options: ScanOptions):
        """Background worker for scanning files."""
        def progress_callback(msg: str, count: int):
            self._task_queue.put({"type": "status", "message": msg})

        moves, skipped = self.organizer.scan_files(progress_callback=progress_callback)
        cancelled = self.organizer._cancel_requested

        self._task_queue.put({
            "type": "scan_complete",
            "moves": moves,
            "skipped": skipped,
            "cancelled": cancelled
        })

    def _on_scan_complete(self, moves: list, skipped: list, cancelled: bool):
        """Called on main thread when scan completes."""
        self.planned_moves = moves
        self.skipped_files = skipped
        self.is_processing = False
        self._update_button_states()
        self._show_cancel_button(False)

        if cancelled:
            self.status_var.set("Preview cancelled.")
            self._add_result_header("Preview was cancelled", ICON_WARNING, "warning")
            return

        # Show dry run notice
        dry_run_frame = ttk.Frame(self.results_inner)
        dry_run_frame.pack(fill="x", pady=(0, 12))

        dry_run_label = ttk.Label(dry_run_frame,
                                 text=f"{ICON_FILE}  DRY RUN - No files have been moved yet",
                                 font=("Segoe UI", 10, "bold"),
                                 **self._bootstyle("info"))
        dry_run_label.pack(pady=8)

        if not self.planned_moves and not self.skipped_files:
            self.status_var.set("No files need to be organized.")
            self._add_result_header("No files to organize", ICON_CHECK, "success")
            self._add_result_item("", "All files are already in the correct location", "secondary", 1)
            return

        # Summary
        self.results_summary.configure(
            text=f"{len(self.planned_moves)} to move, {len(self.skipped_files)} skipped"
        )

        sort_mode = self._get_sort_mode()
        folder = self.selected_folder.get()

        # Show folder structure preview
        if self.planned_moves:
            self._add_result_header(f"Folder Structure Preview ({len(self.planned_moves)} files)")

            # Build tree structure
            categories = {}
            for move in self.planned_moves:
                if move.category not in categories:
                    categories[move.category] = {"years": {}, "count": 0}
                categories[move.category]["count"] += 1

                if sort_mode != SortMode.BY_TYPE:
                    year = str(move.year) if move.year else "Unknown"
                    if year not in categories[move.category]["years"]:
                        categories[move.category]["years"][year] = {"months": set(), "count": 0}
                    categories[move.category]["years"][year]["count"] += 1
                    month = MONTH_NAMES.get(move.month, "Unknown") if move.month else "Unknown"
                    categories[move.category]["years"][year]["months"].add(month)

            # Display tree
            folder_name = Path(folder).name
            self._add_tree_item(f"{ICON_FOLDER} {folder_name}/", 0)

            for cat, cat_data in sorted(categories.items()):
                if sort_mode == SortMode.BY_TYPE:
                    self._add_tree_item(f"{ICON_FOLDER} {cat}/  ({cat_data['count']} files)", 1)
                elif sort_mode == SortMode.BY_DATE:
                    for year, year_data in sorted(cat_data["years"].items()):
                        self._add_tree_item(f"{ICON_FOLDER} {year}/", 1)
                        for month in sorted(year_data["months"]):
                            self._add_tree_item(f"{ICON_FOLDER} {month}/", 2)
                else:
                    self._add_tree_item(f"{ICON_FOLDER} {cat}/", 1)
                    for year, year_data in sorted(cat_data["years"].items()):
                        self._add_tree_item(f"{ICON_FOLDER} {year}/", 2)
                        for month in sorted(year_data["months"]):
                            self._add_tree_item(f"{ICON_FOLDER} {month}/", 3)

        # Show skipped files
        if self.skipped_files:
            self._add_result_header(f"Skipped Files ({len(self.skipped_files)})", ICON_WARNING, "warning")

            by_reason = {}
            for sf in self.skipped_files:
                if sf.reason not in by_reason:
                    by_reason[sf.reason] = []
                by_reason[sf.reason].append(sf)

            for reason, files in by_reason.items():
                self._add_result_item(ICON_WARNING, f"{reason.value}: {len(files)} files",
                                      "warning", 1)

        self._set_progress(100)
        self.status_var.set(f"Preview complete. {len(self.planned_moves)} files ready to organize.")

    def _organize(self):
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        sort_mode = self._get_sort_mode()
        options = self._get_scan_options()

        if not self.planned_moves:
            # Quick synchronous scan if no preview was done
            self.organizer = FileOrganizer(folder, sort_mode, options)
            self.planned_moves, self.skipped_files = self.organizer.scan_files()

            if not self.planned_moves:
                messagebox.showinfo("Nothing to Do", "No files need to be organized.")
                return

        # Confirmation dialog
        msg = f"This will organize {len(self.planned_moves)} files."
        if self.skipped_files:
            msg += f"\n{len(self.skipped_files)} files will be skipped."
        if options.delete_empty_folders:
            msg += "\n\nEmpty folders will be deleted."
        msg += "\n\nA backup will be created automatically."

        if not messagebox.askyesno("Confirm Organization", msg):
            return

        self._clear_results()
        self._set_progress(0)
        self.is_processing = True
        self._update_button_states()
        self._show_cancel_button(True)

        self.organizer = FileOrganizer(folder, sort_mode, options)

        # Run organize in background thread
        self._run_in_thread(self._organize_worker, folder, sort_mode, options)

    def _organize_worker(self, folder: str, sort_mode: SortMode, options: ScanOptions):
        """Background worker for organizing files."""
        def move_progress(current, total, filename):
            percent = (current / total) * 100
            self._task_queue.put({
                "type": "progress",
                "percent": percent,
                "message": f"Moving file {current} of {total}: {filename}"
            })

        result = self.organizer.execute_moves(self.planned_moves, progress_callback=move_progress)
        all_skipped = self.skipped_files + result.skipped_files

        # Save backup
        backup_path = None
        if result.move_log:
            backup_path = BackupManager.save_backup(folder, result.move_log, sort_mode.value, all_skipped)

        # Delete empty folders
        if options.delete_empty_folders and result.moved > 0:
            self._task_queue.put({"type": "status", "message": "Cleaning up empty folders..."})
            delete_empty_folders(Path(folder))

        self._task_queue.put({
            "type": "organize_complete",
            "result": result,
            "all_skipped": all_skipped,
            "backup_path": backup_path
        })

    def _on_organize_complete(self, result: OrganizeResult, all_skipped: list, backup_path: Optional[Path]):
        """Called on main thread when organize completes."""
        self.is_processing = False
        self._update_button_states()
        self._show_cancel_button(False)

        # Show success/error state
        self._show_success_state(result.moved, len(all_skipped), result.errors)

        # Update summary
        self.results_summary.configure(
            text=f"{result.moved} moved, {len(all_skipped)} skipped, {result.errors} errors"
        )

        # Results details
        if result.cancelled:
            self._add_result_header("Operation Cancelled", ICON_WARNING, "warning")

        self._add_result_header(f"Moved ({result.moved} files)", ICON_CHECK, "success")
        if result.move_log:
            for orig, dest in result.move_log[:5]:
                dest_name = Path(dest).name
                self._add_result_item(ICON_CHECK, dest_name, "success", 1)
            if len(result.move_log) > 5:
                self._add_result_item("", f"... and {len(result.move_log) - 5} more files",
                                      "secondary", 1)

        if all_skipped:
            self._add_result_header(f"Skipped ({len(all_skipped)} files)", ICON_WARNING, "warning")
            by_reason = {}
            for sf in all_skipped:
                if sf.reason not in by_reason:
                    by_reason[sf.reason] = 0
                by_reason[sf.reason] += 1
            for reason, count in by_reason.items():
                self._add_result_item(ICON_WARNING, f"{reason.value}: {count}", "warning", 1)

        if result.errors > 0:
            self._add_result_header(f"Errors ({result.errors})", ICON_ERROR, "danger")
            for err in result.error_messages[:5]:
                self._add_result_item(ICON_ERROR, err, "danger", 1)

        if backup_path:
            self._add_result_header("Backup Created")
            self._add_result_item(ICON_FILE, backup_path.name, "secondary", 1)

        self._set_progress(100)
        self.status_var.set(f"Complete! Moved {result.moved} files.")
        self.planned_moves = []
        self.skipped_files = []

    def _show_restore_dialog(self):
        backups = BackupManager.list_backups()

        if not backups:
            messagebox.showinfo("No Backups", "No backup files found.\n\nBackups are created when you organize files.")
            return

        if TTKBOOTSTRAP_AVAILABLE:
            dialog = ttk.Toplevel(self.root)
        else:
            dialog = tk.Toplevel(self.root)
        dialog.title("Restore from Backup")
        dialog.geometry("550x500")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        frame = ttk.Frame(dialog, padding=24)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Restore from Backup",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")

        ttk.Label(frame, text="Select a backup to restore files to their original locations",
                 font=("Segoe UI", 10), **self._bootstyle("secondary")).pack(anchor="w", pady=(4, 20))

        # Listbox with treeview for better appearance
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 16))

        columns = ("date", "files", "folder")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        tree.heading("date", text="Date")
        tree.heading("files", text="Files")
        tree.heading("folder", text="Source Folder")
        tree.column("date", width=150)
        tree.column("files", width=60)
        tree.column("folder", width=300)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for backup in backups:
            tree.insert("", "end", values=(
                backup.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                backup.file_count,
                backup.source_folder
            ))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")

        def do_restore():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No Selection", "Please select a backup.", parent=dialog)
                return
            idx = tree.index(sel[0])
            backup = backups[idx]
            if messagebox.askyesno("Confirm", f"Restore {backup.file_count} files?", parent=dialog):
                dialog.destroy()
                self._execute_restore(backup)

        def do_delete():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No Selection", "Please select a backup.", parent=dialog)
                return
            idx = tree.index(sel[0])
            backup = backups[idx]
            if messagebox.askyesno("Confirm Delete", "Delete this backup?", parent=dialog):
                BackupManager.delete_backup(backup.filepath)
                tree.delete(sel[0])
                backups.pop(idx)
                if not backups:
                    dialog.destroy()

        ttk.Button(btn_frame, text="Restore", command=do_restore,
                  **self._bootstyle("success")).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Delete", command=do_delete,
                  **self._bootstyle("danger-outline")).pack(side="left")
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                  **self._bootstyle("secondary-link")).pack(side="right")

    def _execute_restore(self, backup_info: BackupInfo):
        self._clear_results()
        self._set_progress(0)
        self.status_var.set("Loading backup...")
        self.is_processing = True
        self._update_button_states()
        self._show_cancel_button(True)
        self.root.update_idletasks()

        try:
            backup_data = BackupManager.load_backup(backup_info.filepath)
        except Exception as e:
            self.is_processing = False
            self._update_button_states()
            self._show_cancel_button(False)
            messagebox.showerror("Error", f"Failed to load backup: {e}")
            return

        self._add_result_header("Restoring from Backup")
        self._add_result_item(ICON_CALENDAR, backup_info.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "secondary", 1)
        self._add_result_item(ICON_FILE, f"{backup_info.file_count} files to restore", "secondary", 1)

        cancel_flag = [False]

        def check_cancel():
            return cancel_flag[0]

        def restore_progress(current, total, filename):
            percent = (current / total) * 100
            self._set_progress(percent)
            self.status_var.set(f"Restoring file {current} of {total}: {filename}")
            self.root.update_idletasks()

        original_cancel = self._cancel_operation

        def cancel_restore():
            cancel_flag[0] = True
            self.status_var.set("Cancelling...")

        self._cancel_operation = cancel_restore

        result = BackupManager.execute_restore(backup_data, restore_progress, check_cancel)

        self._cancel_operation = original_cancel
        self.is_processing = False
        self._update_button_states()
        self._show_cancel_button(False)

        self._show_success_state(result.moved, result.skipped, result.errors)

        self._add_result_header(f"Restored ({result.moved} files)", ICON_CHECK, "success")

        if result.skipped > 0:
            self._add_result_header(f"Skipped ({result.skipped})", ICON_WARNING, "warning")

        if result.errors > 0:
            self._add_result_header(f"Errors ({result.errors})", ICON_ERROR, "danger")

        self._set_progress(100)
        self.status_var.set(f"Restore complete! {result.moved} files restored.")

        if result.moved > 0 and result.errors == 0 and not result.cancelled:
            if messagebox.askyesno("Success", f"Restored {result.moved} files.\n\nDelete backup?"):
                BackupManager.delete_backup(backup_info.filepath)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.run()
