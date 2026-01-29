"""
File Organizer - A Windows desktop application that organizes files by type and date.

Organizes files into: [Category]/[Year]/[Month]/files
"""

import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

# Directory where backup files are stored (same as script location)
BACKUP_DIR = Path(__file__).parent / "backups"

# Application info
APP_NAME = "Folder Organizer"
APP_VERSION = "1.1.0"


class SortMode(Enum):
    """File organization modes."""
    BY_TYPE = "type"           # Category only
    BY_DATE = "date"           # Year/Month only
    BY_BOTH = "both"           # Category/Year/Month


# Extension to category mapping
EXTENSION_CATEGORIES = {
    # Images
    '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
    '.bmp': 'Images', '.webp': 'Images', '.svg': 'Images', '.ico': 'Images',
    '.tiff': 'Images', '.raw': 'Images',
    # Documents
    '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
    '.txt': 'Documents', '.xlsx': 'Documents', '.pptx': 'Documents',
    '.xls': 'Documents', '.ppt': 'Documents', '.odt': 'Documents',
    '.rtf': 'Documents', '.csv': 'Documents',
    # Videos
    '.mp4': 'Videos', '.avi': 'Videos', '.mov': 'Videos',
    '.mkv': 'Videos', '.wmv': 'Videos', '.flv': 'Videos',
    '.webm': 'Videos', '.m4v': 'Videos',
    # Audio
    '.mp3': 'Audio', '.wav': 'Audio', '.flac': 'Audio', '.aac': 'Audio',
    '.wma': 'Audio', '.ogg': 'Audio', '.m4a': 'Audio',
    # Archives
    '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives',
    '.tar': 'Archives', '.gz': 'Archives', '.bz2': 'Archives',
    # Code
    '.py': 'Code', '.js': 'Code', '.html': 'Code', '.css': 'Code',
    '.java': 'Code', '.cpp': 'Code', '.c': 'Code', '.h': 'Code',
    '.json': 'Code', '.xml': 'Code', '.sql': 'Code',
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
class OrganizeResult:
    """Result of an organize operation."""
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)
    # Tracks actual moves: list of (original_path, final_destination)
    move_log: list = field(default_factory=list)


@dataclass
class BackupInfo:
    """Information about a backup file."""
    filepath: Path
    timestamp: datetime
    source_folder: str
    file_count: int


class FileOrganizer:
    """Handles the file organization logic."""

    def __init__(self, source_folder: str, sort_mode: SortMode = SortMode.BY_BOTH):
        self.source_folder = Path(source_folder)
        self.sort_mode = sort_mode

    def get_category(self, file_path: Path) -> str:
        """Get the category for a file based on its extension."""
        ext = file_path.suffix.lower()
        return EXTENSION_CATEGORIES.get(ext, 'Other')

    def get_file_date(self, file_path: Path) -> datetime:
        """Get file creation date, falling back to modified date."""
        try:
            # On Windows, st_ctime is creation time
            stat = file_path.stat()
            timestamp = stat.st_ctime
            # Use modified time if it's older (more reliable in some cases)
            if stat.st_mtime < timestamp:
                timestamp = stat.st_mtime
            return datetime.fromtimestamp(timestamp)
        except OSError:
            return datetime.now()

    def get_destination_path(self, file_path: Path) -> Path:
        """Calculate the destination path for a file based on sort mode."""
        category = self.get_category(file_path)
        file_date = self.get_file_date(file_path)
        year = str(file_date.year)
        month = MONTH_NAMES[file_date.month]

        if self.sort_mode == SortMode.BY_TYPE:
            return self.source_folder / category / file_path.name
        elif self.sort_mode == SortMode.BY_DATE:
            return self.source_folder / year / month / file_path.name
        else:  # BY_BOTH
            return self.source_folder / category / year / month / file_path.name

    def get_unique_destination(self, dest_path: Path) -> Path:
        """Get a unique destination path by appending a number if needed."""
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

    def is_in_correct_location(self, file_path: Path, dest_path: Path) -> bool:
        """Check if a file is already in its correct location."""
        try:
            return file_path.resolve() == dest_path.resolve()
        except OSError:
            return False

    def is_in_organized_structure(self, file_path: Path) -> bool:
        """Check if a file is already within an organized folder structure."""
        try:
            relative = file_path.relative_to(self.source_folder)
        except ValueError:
            return False
        parts = relative.parts
        valid_categories = set(EXTENSION_CATEGORIES.values()) | {'Other'}

        if self.sort_mode == SortMode.BY_TYPE:
            # Check if in Category/file structure
            if len(parts) >= 2:
                return parts[0] in valid_categories
        elif self.sort_mode == SortMode.BY_DATE:
            # Check if in Year/Month/file structure
            if len(parts) >= 3:
                year = parts[0]
                month = parts[1]
                if year.isdigit() and len(year) == 4:
                    if month in MONTH_NAMES.values():
                        return True
        else:  # BY_BOTH
            # Check if in Category/Year/Month structure
            if len(parts) >= 4:
                category = parts[0]
                year = parts[1]
                month = parts[2]
                if category in valid_categories:
                    if year.isdigit() and len(year) == 4:
                        if month in MONTH_NAMES.values():
                            return True
        return False

    def scan_files(self, progress_callback: Callable[[str], None] = None) -> list[FileMove]:
        """Scan the source folder and plan file moves."""
        planned_moves = []

        for file_path in self.source_folder.rglob('*'):
            if not file_path.is_file():
                continue

            # Skip files already in organized structure
            if self.is_in_organized_structure(file_path):
                continue

            if progress_callback:
                progress_callback(f"Scanning: {file_path.name}")

            dest_path = self.get_destination_path(file_path)

            # Skip if already in correct location
            if self.is_in_correct_location(file_path, dest_path):
                continue

            file_date = self.get_file_date(file_path)
            planned_moves.append(FileMove(
                source=file_path,
                destination=dest_path,
                category=self.get_category(file_path),
                year=file_date.year,
                month=file_date.month
            ))

        return planned_moves

    def execute_moves(
        self,
        planned_moves: list[FileMove],
        progress_callback: Callable[[int, int, str], None] = None
    ) -> OrganizeResult:
        """Execute the planned file moves."""
        result = OrganizeResult()
        total = len(planned_moves)

        for i, move in enumerate(planned_moves):
            if progress_callback:
                progress_callback(i + 1, total, move.source.name)

            try:
                # Create destination directory
                move.destination.parent.mkdir(parents=True, exist_ok=True)

                # Get unique destination if file exists
                final_dest = self.get_unique_destination(move.destination)

                # Record the move before executing
                original_path = str(move.source.resolve())

                # Move the file
                shutil.move(str(move.source), str(final_dest))
                result.moved += 1

                # Log the successful move
                result.move_log.append((original_path, str(final_dest.resolve())))

            except Exception as e:
                result.errors += 1
                result.error_messages.append(f"{move.source.name}: {str(e)}")

        return result


class BackupManager:
    """Manages backup and restore operations."""

    @staticmethod
    def save_backup(source_folder: str, move_log: list[tuple[str, str]], sort_mode: str) -> Path:
        """Save a backup of file moves to a JSON file."""
        BACKUP_DIR.mkdir(exist_ok=True)

        timestamp = datetime.now()
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = BACKUP_DIR / filename

        backup_data = {
            "timestamp": timestamp.isoformat(),
            "source_folder": source_folder,
            "sort_mode": sort_mode,
            "file_count": len(move_log),
            "moves": [
                {"original": orig, "destination": dest}
                for orig, dest in move_log
            ]
        }

        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        return backup_path

    @staticmethod
    def list_backups() -> list[BackupInfo]:
        """List all available backup files."""
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

        # Sort by timestamp, newest first
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups

    @staticmethod
    def load_backup(filepath: Path) -> dict:
        """Load a backup file and return its data."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def execute_restore(
        backup_data: dict,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> OrganizeResult:
        """Restore files to their original locations."""
        result = OrganizeResult()
        moves = backup_data["moves"]
        total = len(moves)

        for i, move in enumerate(moves):
            original = Path(move["original"])
            destination = Path(move["destination"])

            if progress_callback:
                progress_callback(i + 1, total, destination.name)

            try:
                # Check if the file exists at the destination
                if not destination.exists():
                    result.errors += 1
                    result.error_messages.append(
                        f"{destination.name}: File not found at organized location"
                    )
                    continue

                # Create original directory if needed
                original.parent.mkdir(parents=True, exist_ok=True)

                # Handle if a file already exists at original location
                final_original = original
                if original.exists():
                    stem = original.stem
                    suffix = original.suffix
                    counter = 1
                    while final_original.exists():
                        final_original = original.parent / f"{stem}_restored_{counter}{suffix}"
                        counter += 1

                # Move the file back
                shutil.move(str(destination), str(final_original))
                result.moved += 1
                result.move_log.append((str(destination), str(final_original)))

            except Exception as e:
                result.errors += 1
                result.error_messages.append(f"{destination.name}: {str(e)}")

        return result

    @staticmethod
    def delete_backup(filepath: Path) -> bool:
        """Delete a backup file."""
        try:
            filepath.unlink()
            return True
        except OSError:
            return False


class ModernStyle:
    """Modern styling configuration for the application."""

    # Colors
    PRIMARY = "#2563eb"       # Blue
    PRIMARY_HOVER = "#1d4ed8"
    SUCCESS = "#16a34a"       # Green
    WARNING = "#ea580c"       # Orange
    DANGER = "#dc2626"        # Red

    BG_DARK = "#1e293b"       # Dark slate
    BG_MEDIUM = "#334155"     # Medium slate
    BG_LIGHT = "#475569"      # Light slate

    TEXT_PRIMARY = "#f8fafc"  # Almost white
    TEXT_SECONDARY = "#cbd5e1" # Light gray (more readable)
    TEXT_MUTED = "#94a3b8"    # Muted gray (lighter than before)

    CARD_BG = "#1e293b"
    BORDER = "#475569"

    @classmethod
    def apply(cls, root: tk.Tk):
        """Apply modern styling to the application."""
        style = ttk.Style()

        # Try to use a modern theme as base
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')

        # Configure colors
        root.configure(bg=cls.BG_DARK)

        # Frame styles
        style.configure("TFrame", background=cls.BG_DARK)
        style.configure("Card.TFrame", background=cls.BG_MEDIUM, relief="flat")

        # Label styles
        style.configure("TLabel",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10))

        style.configure("Header.TLabel",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 24, "bold"))

        style.configure("Subheader.TLabel",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_SECONDARY,
                       font=("Segoe UI", 11))

        style.configure("Section.TLabel",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 11, "bold"))

        style.configure("Card.TLabel",
                       background=cls.BG_MEDIUM,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10))

        style.configure("Status.TLabel",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 9))

        # Button styles
        style.configure("TButton",
                       background=cls.PRIMARY,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10),
                       padding=(16, 8),
                       borderwidth=0)

        style.map("TButton",
                 background=[("active", cls.PRIMARY_HOVER), ("disabled", cls.BG_LIGHT)],
                 foreground=[("disabled", cls.TEXT_MUTED)])

        style.configure("Accent.TButton",
                       background=cls.SUCCESS,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10, "bold"),
                       padding=(20, 10))

        style.map("Accent.TButton",
                 background=[("active", "#15803d"), ("disabled", cls.BG_LIGHT)])

        style.configure("Secondary.TButton",
                       background=cls.BG_MEDIUM,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10),
                       padding=(16, 8))

        style.map("Secondary.TButton",
                 background=[("active", cls.BG_LIGHT), ("disabled", cls.BG_LIGHT)])

        # Entry styles
        style.configure("TEntry",
                       fieldbackground=cls.BG_MEDIUM,
                       foreground=cls.TEXT_PRIMARY,
                       insertcolor=cls.TEXT_PRIMARY,
                       padding=8)

        # Radiobutton styles
        style.configure("TRadiobutton",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10),
                       padding=4)

        style.configure("Card.TRadiobutton",
                       background=cls.BG_MEDIUM,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10),
                       padding=4)

        # Progressbar styles
        style.configure("TProgressbar",
                       background=cls.PRIMARY,
                       troughcolor=cls.BG_MEDIUM,
                       borderwidth=0,
                       thickness=8)

        # LabelFrame styles
        style.configure("TLabelframe",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY)

        style.configure("TLabelframe.Label",
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       font=("Segoe UI", 10, "bold"))


class FileOrganizerApp:
    """Main application GUI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}")
        self.root.geometry("700x650")
        self.root.minsize(600, 550)
        self.root.resizable(True, True)

        # Apply modern styling
        ModernStyle.apply(self.root)

        # Variables
        self.selected_folder = tk.StringVar()
        self.sort_mode = tk.StringVar(value=SortMode.BY_BOTH.value)
        self.planned_moves: list[FileMove] = []

        self._create_widgets()
        self._center_window()

    def _center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self):
        """Create the GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Header section
        self._create_header(main_frame)

        # Folder selection section
        self._create_folder_section(main_frame)

        # Sort options section
        self._create_sort_options(main_frame)

        # Action buttons section
        self._create_action_buttons(main_frame)

        # Progress section
        self._create_progress_section(main_frame)

        # Results section
        self._create_results_section(main_frame)

        # Footer
        self._create_footer(main_frame)

    def _create_header(self, parent):
        """Create the header section."""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(
            header_frame,
            text=APP_NAME,
            style="Header.TLabel"
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            header_frame,
            text="Automatically organize your files by type and date",
            style="Subheader.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _create_folder_section(self, parent):
        """Create the folder selection section."""
        section_frame = ttk.Frame(parent)
        section_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        section_frame.columnconfigure(1, weight=1)

        ttk.Label(
            section_frame,
            text="Select Folder",
            style="Section.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Folder entry with custom styling
        self.folder_entry = tk.Entry(
            section_frame,
            textvariable=self.selected_folder,
            state="readonly",
            font=("Segoe UI", 10),
            bg=ModernStyle.BG_MEDIUM,
            fg=ModernStyle.TEXT_PRIMARY,
            insertbackground=ModernStyle.TEXT_PRIMARY,
            relief="flat",
            readonlybackground=ModernStyle.BG_MEDIUM
        )
        self.folder_entry.grid(row=1, column=0, sticky="ew", ipady=8, padx=(0, 8))
        section_frame.columnconfigure(0, weight=1)

        self.browse_btn = ttk.Button(
            section_frame,
            text="Browse...",
            command=self._browse_folder,
            style="Secondary.TButton"
        )
        self.browse_btn.grid(row=1, column=1, sticky="e")

    def _create_sort_options(self, parent):
        """Create the sorting options section."""
        section_frame = ttk.Frame(parent)
        section_frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        ttk.Label(
            section_frame,
            text="Organization Mode",
            style="Section.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Options card
        options_card = tk.Frame(
            section_frame,
            bg=ModernStyle.BG_MEDIUM,
            padx=16,
            pady=12
        )
        options_card.grid(row=1, column=0, sticky="ew")
        section_frame.columnconfigure(0, weight=1)

        options = [
            (SortMode.BY_TYPE.value, "By Type", "Images/, Documents/, Videos/..."),
            (SortMode.BY_DATE.value, "By Date", "2024/01-January/, 2024/02-February/..."),
            (SortMode.BY_BOTH.value, "By Type & Date", "Images/2024/01-January/... (Recommended)"),
        ]

        for i, (value, label, desc) in enumerate(options):
            opt_frame = tk.Frame(options_card, bg=ModernStyle.BG_MEDIUM)
            opt_frame.grid(row=i, column=0, sticky="w", pady=4)

            rb = tk.Radiobutton(
                opt_frame,
                text=label,
                variable=self.sort_mode,
                value=value,
                font=("Segoe UI", 10),
                bg=ModernStyle.BG_MEDIUM,
                fg=ModernStyle.TEXT_PRIMARY,
                selectcolor=ModernStyle.BG_DARK,
                activebackground=ModernStyle.BG_MEDIUM,
                activeforeground=ModernStyle.TEXT_PRIMARY,
                highlightthickness=0
            )
            rb.grid(row=0, column=0, sticky="w")

            desc_label = tk.Label(
                opt_frame,
                text=f"  {desc}",
                font=("Segoe UI", 9),
                bg=ModernStyle.BG_MEDIUM,
                fg=ModernStyle.TEXT_SECONDARY
            )
            desc_label.grid(row=0, column=1, sticky="w")

    def _create_action_buttons(self, parent):
        """Create the action buttons section."""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(0, 16))

        # Left buttons
        left_frame = ttk.Frame(btn_frame)
        left_frame.pack(side="left")

        self.preview_btn = ttk.Button(
            left_frame,
            text="Preview Changes",
            command=self._preview,
            style="Secondary.TButton"
        )
        self.preview_btn.pack(side="left", padx=(0, 8))

        self.organize_btn = ttk.Button(
            left_frame,
            text="Organize Files",
            command=self._organize,
            style="Accent.TButton"
        )
        self.organize_btn.pack(side="left", padx=(0, 8))

        # Right button
        self.restore_btn = ttk.Button(
            btn_frame,
            text="Restore...",
            command=self._show_restore_dialog,
            style="Secondary.TButton"
        )
        self.restore_btn.pack(side="right")

        # Initial button states
        self._update_button_states()

    def _create_progress_section(self, parent):
        """Create the progress section."""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            style="TProgressbar"
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.status_var = tk.StringVar(value="Select a folder to get started")
        self.status_label = ttk.Label(
            progress_frame,
            textvariable=self.status_var,
            style="Status.TLabel"
        )
        self.status_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _create_results_section(self, parent):
        """Create the results section."""
        results_frame = ttk.Frame(parent)
        results_frame.grid(row=5, column=0, sticky="nsew", pady=(8, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        parent.rowconfigure(5, weight=1)

        ttk.Label(
            results_frame,
            text="Results",
            style="Section.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Text widget with custom styling
        text_container = tk.Frame(
            results_frame,
            bg=ModernStyle.BG_MEDIUM,
            padx=2,
            pady=2
        )
        text_container.grid(row=1, column=0, sticky="nsew")
        text_container.columnconfigure(0, weight=1)
        text_container.rowconfigure(0, weight=1)

        self.results_text = tk.Text(
            text_container,
            height=12,
            font=("Consolas", 9),
            bg=ModernStyle.BG_DARK,
            fg=ModernStyle.TEXT_PRIMARY,
            insertbackground=ModernStyle.TEXT_PRIMARY,
            relief="flat",
            padx=12,
            pady=12,
            state="disabled",
            wrap="word"
        )
        self.results_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            text_container,
            orient="vertical",
            command=self.results_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_text.configure(yscrollcommand=scrollbar.set)

    def _create_footer(self, parent):
        """Create the footer section."""
        footer_frame = ttk.Frame(parent)
        footer_frame.grid(row=6, column=0, sticky="ew", pady=(12, 0))

        ttk.Label(
            footer_frame,
            text=f"v{APP_VERSION}",
            style="Status.TLabel"
        ).pack(side="right")

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(title="Select Folder to Organize")
        if folder:
            self.selected_folder.set(folder)
            self.planned_moves = []
            self._clear_results()
            self._update_button_states()
            self.status_var.set("Folder selected. Click 'Preview Changes' to see what will happen.")
            self.progress_var.set(0)

    def _update_button_states(self):
        """Update button enabled/disabled states."""
        has_folder = bool(self.selected_folder.get())
        state = "normal" if has_folder else "disabled"
        self.preview_btn.configure(state=state)
        self.organize_btn.configure(state=state)

    def _clear_results(self):
        """Clear the results text area."""
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.configure(state="disabled")

    def _append_result(self, text: str, tag: str = None):
        """Append text to results area."""
        self.results_text.configure(state="normal")
        self.results_text.insert(tk.END, text + "\n", tag)
        self.results_text.see(tk.END)
        self.results_text.configure(state="disabled")
        self.root.update_idletasks()

    def _get_sort_mode(self) -> SortMode:
        """Get the current sort mode."""
        value = self.sort_mode.get()
        for mode in SortMode:
            if mode.value == value:
                return mode
        return SortMode.BY_BOTH

    def _preview(self):
        """Run preview/dry-run mode."""
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        self._clear_results()
        self.progress_var.set(0)
        self.status_var.set("Scanning files...")
        self.root.update_idletasks()

        sort_mode = self._get_sort_mode()
        organizer = FileOrganizer(folder, sort_mode)

        def scan_progress(msg):
            self.status_var.set(msg)
            self.root.update_idletasks()

        self.planned_moves = organizer.scan_files(progress_callback=scan_progress)

        if not self.planned_moves:
            self.status_var.set("No files need to be organized.")
            self._append_result("No files found that need organizing.")
            self._append_result("Files may already be in the correct location.")
            return

        # Group by category for summary
        categories = {}
        for move in self.planned_moves:
            if move.category not in categories:
                categories[move.category] = []
            categories[move.category].append(move)

        mode_desc = {
            SortMode.BY_TYPE: "by type only",
            SortMode.BY_DATE: "by date only",
            SortMode.BY_BOTH: "by type and date"
        }

        self._append_result(f"PREVIEW: {len(self.planned_moves)} files will be organized {mode_desc[sort_mode]}")
        self._append_result("=" * 50)

        for category, moves in sorted(categories.items()):
            self._append_result(f"\n{category} ({len(moves)} files)")
            self._append_result("-" * 40)
            for move in moves[:5]:  # Show first 5 per category
                rel_dest = move.destination.relative_to(Path(folder))
                self._append_result(f"  {move.source.name}")
                self._append_result(f"    → {rel_dest}")
            if len(moves) > 5:
                self._append_result(f"  ... and {len(moves) - 5} more files")

        self.progress_var.set(100)
        self.status_var.set(f"Preview complete. {len(self.planned_moves)} files ready to organize.")

    def _organize(self):
        """Execute file organization."""
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        sort_mode = self._get_sort_mode()

        # Confirm if no preview was done
        if not self.planned_moves:
            organizer = FileOrganizer(folder, sort_mode)
            self.planned_moves = organizer.scan_files()

            if not self.planned_moves:
                messagebox.showinfo("Nothing to Do", "No files need to be organized.")
                return

        # Confirm action
        if not messagebox.askyesno(
            "Confirm Organization",
            f"This will move {len(self.planned_moves)} files.\n\n"
            f"A backup will be created automatically.\n\nContinue?"
        ):
            return

        self._clear_results()
        self.progress_var.set(0)

        organizer = FileOrganizer(folder, sort_mode)

        def move_progress(current, total, filename):
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_var.set(f"Moving ({current}/{total}): {filename}")
            self.root.update_idletasks()

        result = organizer.execute_moves(self.planned_moves, progress_callback=move_progress)

        # Save backup if any files were moved
        backup_path = None
        if result.move_log:
            backup_path = BackupManager.save_backup(folder, result.move_log, sort_mode.value)

        # Show results
        self._append_result("ORGANIZATION COMPLETE")
        self._append_result("=" * 50)
        self._append_result(f"\nFiles moved: {result.moved}")
        self._append_result(f"Errors: {result.errors}")

        if backup_path:
            self._append_result(f"\nBackup saved: {backup_path.name}")
            self._append_result("Use 'Restore...' to undo this operation.")

        if result.error_messages:
            self._append_result("\nErrors encountered:")
            for error in result.error_messages:
                self._append_result(f"  • {error}")

        self.progress_var.set(100)
        self.status_var.set(f"Complete! Moved {result.moved} files.")
        self.planned_moves = []

        messagebox.showinfo(
            "Organization Complete",
            f"Successfully moved {result.moved} files.\nErrors: {result.errors}"
        )

    def _show_restore_dialog(self):
        """Show dialog to select and restore from a backup."""
        backups = BackupManager.list_backups()

        if not backups:
            messagebox.showinfo(
                "No Backups",
                "No backup files found.\n\nBackups are created automatically when you organize files."
            )
            return

        # Create restore dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Restore from Backup")
        dialog.geometry("550x450")
        dialog.configure(bg=ModernStyle.BG_DARK)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # Main frame
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Restore from Backup",
            style="Header.TLabel"
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            frame,
            text="Select a backup to restore files to their original locations",
            style="Subheader.TLabel"
        ).pack(anchor="w", pady=(0, 16))

        # Listbox with backups
        list_frame = tk.Frame(frame, bg=ModernStyle.BG_MEDIUM, padx=2, pady=2)
        list_frame.pack(fill="both", expand=True, pady=(0, 12))

        listbox = tk.Listbox(
            list_frame,
            height=8,
            font=("Segoe UI", 10),
            bg=ModernStyle.BG_DARK,
            fg=ModernStyle.TEXT_PRIMARY,
            selectbackground=ModernStyle.PRIMARY,
            selectforeground=ModernStyle.TEXT_PRIMARY,
            relief="flat",
            highlightthickness=0
        )
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        # Populate listbox
        for backup in backups:
            display = f"  {backup.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  •  {backup.file_count} files"
            listbox.insert(tk.END, display)

        # Details label
        details_var = tk.StringVar(value="Select a backup to see details")
        details_label = ttk.Label(frame, textvariable=details_var, style="Status.TLabel", wraplength=500)
        details_label.pack(anchor="w", pady=(0, 16))

        def on_select(event):
            selection = listbox.curselection()
            if selection:
                backup = backups[selection[0]]
                details_var.set(f"Source: {backup.source_folder}")

        listbox.bind('<<ListboxSelect>>', on_select)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")

        def do_restore():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup to restore.", parent=dialog)
                return

            backup = backups[selection[0]]

            if not messagebox.askyesno(
                "Confirm Restore",
                f"This will restore {backup.file_count} files to their original locations.\n\nContinue?",
                parent=dialog
            ):
                return

            dialog.destroy()
            self._execute_restore(backup)

        def do_delete():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup to delete.", parent=dialog)
                return

            backup = backups[selection[0]]

            if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete backup from {backup.timestamp.strftime('%Y-%m-%d %H:%M:%S')}?\n\nThis cannot be undone.",
                parent=dialog
            ):
                return

            if BackupManager.delete_backup(backup.filepath):
                listbox.delete(selection[0])
                backups.pop(selection[0])
                details_var.set("Backup deleted")
                if not backups:
                    dialog.destroy()
                    messagebox.showinfo("No Backups", "All backups have been deleted.")

        ttk.Button(btn_frame, text="Restore Selected", command=do_restore, style="Accent.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Delete", command=do_delete, style="Secondary.TButton").pack(side="left")
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, style="Secondary.TButton").pack(side="right")

    def _execute_restore(self, backup_info: BackupInfo):
        """Execute a restore operation."""
        self._clear_results()
        self.progress_var.set(0)
        self.status_var.set("Loading backup...")
        self.root.update_idletasks()

        try:
            backup_data = BackupManager.load_backup(backup_info.filepath)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load backup: {e}")
            return

        self._append_result("RESTORING FROM BACKUP")
        self._append_result("=" * 50)
        self._append_result(f"\nBackup date: {backup_info.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self._append_result(f"Source folder: {backup_info.source_folder}")
        self._append_result(f"Files to restore: {backup_info.file_count}\n")

        def restore_progress(current, total, filename):
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_var.set(f"Restoring ({current}/{total}): {filename}")
            self.root.update_idletasks()

        result = BackupManager.execute_restore(backup_data, progress_callback=restore_progress)

        self._append_result("\nRESTORE COMPLETE")
        self._append_result("=" * 50)
        self._append_result(f"\nFiles restored: {result.moved}")
        self._append_result(f"Errors: {result.errors}")

        if result.error_messages:
            self._append_result("\nErrors encountered:")
            for error in result.error_messages:
                self._append_result(f"  • {error}")

        self.progress_var.set(100)
        self.status_var.set(f"Restore complete! {result.moved} files restored.")

        # Ask if user wants to delete the backup
        if result.moved > 0 and result.errors == 0:
            if messagebox.askyesno(
                "Restore Complete",
                f"Successfully restored {result.moved} files.\n\nDelete this backup file?"
            ):
                BackupManager.delete_backup(backup_info.filepath)
                self._append_result("\nBackup file deleted.")
        else:
            messagebox.showinfo(
                "Restore Complete",
                f"Restored {result.moved} files.\nErrors: {result.errors}"
            )

    def run(self):
        """Start the application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.run()
