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

# Directory where backup files are stored (same as script location)
BACKUP_DIR = Path(__file__).parent / "backups"


# Extension to category mapping
EXTENSION_CATEGORIES = {
    # Images
    '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
    '.bmp': 'Images', '.webp': 'Images', '.svg': 'Images',
    # Documents
    '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
    '.txt': 'Documents', '.xlsx': 'Documents', '.pptx': 'Documents',
    # Videos
    '.mp4': 'Videos', '.avi': 'Videos', '.mov': 'Videos',
    '.mkv': 'Videos', '.wmv': 'Videos',
    # Audio
    '.mp3': 'Audio', '.wav': 'Audio', '.flac': 'Audio', '.aac': 'Audio',
    # Archives
    '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives', '.tar': 'Archives',
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

    def __init__(self, source_folder: str):
        self.source_folder = Path(source_folder)

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
        """Calculate the destination path for a file."""
        category = self.get_category(file_path)
        file_date = self.get_file_date(file_path)
        year = str(file_date.year)
        month = MONTH_NAMES[file_date.month]

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
        relative = file_path.relative_to(self.source_folder)
        parts = relative.parts

        # Check if file is in Category/Year/Month structure
        if len(parts) >= 4:
            category = parts[0]
            year = parts[1]
            month = parts[2]

            # Verify it matches our structure
            valid_categories = set(EXTENSION_CATEGORIES.values()) | {'Other'}
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
    def save_backup(source_folder: str, move_log: list[tuple[str, str]]) -> Path:
        """Save a backup of file moves to a JSON file."""
        BACKUP_DIR.mkdir(exist_ok=True)

        timestamp = datetime.now()
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = BACKUP_DIR / filename

        backup_data = {
            "timestamp": timestamp.isoformat(),
            "source_folder": source_folder,
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


class FileOrganizerApp:
    """Main application GUI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("File Organizer")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        self.selected_folder = tk.StringVar()
        self.planned_moves: list[FileMove] = []

        self._create_widgets()

    def _create_widgets(self):
        """Create the GUI widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Folder selection
        ttk.Label(main_frame, text="Source Folder:").grid(row=0, column=0, sticky="w", pady=5)

        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=0, column=1, sticky="ew", pady=5, padx=(5, 0))
        folder_frame.columnconfigure(0, weight=1)

        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.selected_folder, state="readonly")
        self.folder_entry.grid(row=0, column=0, sticky="ew")

        self.browse_btn = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        self.browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.preview_btn = ttk.Button(btn_frame, text="Preview (Dry Run)", command=self._preview)
        self.preview_btn.pack(side="left", padx=5)

        self.organize_btn = ttk.Button(btn_frame, text="Organize Files", command=self._organize)
        self.organize_btn.pack(side="left", padx=5)

        self.restore_btn = ttk.Button(btn_frame, text="Restore...", command=self._show_restore_dialog)
        self.restore_btn.pack(side="left", padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        # Status label
        self.status_var = tk.StringVar(value="Select a folder to begin")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        # Results text area
        ttk.Label(main_frame, text="Results:").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 5))

        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)

        self.results_text = tk.Text(text_frame, height=15, width=70, state="disabled")
        self.results_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.results_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_text.configure(yscrollcommand=scrollbar.set)

        # Initial button states
        self._update_button_states()

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(title="Select Folder to Organize")
        if folder:
            self.selected_folder.set(folder)
            self.planned_moves = []
            self._clear_results()
            self._update_button_states()
            self.status_var.set("Folder selected. Click 'Preview' to see planned changes.")

    def _update_button_states(self):
        """Update button enabled/disabled states."""
        has_folder = bool(self.selected_folder.get())
        self.preview_btn.configure(state="normal" if has_folder else "disabled")
        self.organize_btn.configure(state="normal" if has_folder else "disabled")

    def _clear_results(self):
        """Clear the results text area."""
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.configure(state="disabled")

    def _append_result(self, text: str):
        """Append text to results area."""
        self.results_text.configure(state="normal")
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)
        self.results_text.configure(state="disabled")
        self.root.update_idletasks()

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

        organizer = FileOrganizer(folder)

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

        self._append_result(f"=== PREVIEW: {len(self.planned_moves)} files will be organized ===\n")

        for category, moves in sorted(categories.items()):
            self._append_result(f"\n{category} ({len(moves)} files):")
            self._append_result("-" * 40)
            for move in moves[:10]:  # Show first 10 per category
                rel_dest = move.destination.relative_to(Path(folder))
                self._append_result(f"  {move.source.name}")
                self._append_result(f"    -> {rel_dest}")
            if len(moves) > 10:
                self._append_result(f"  ... and {len(moves) - 10} more files")

        self.progress_var.set(100)
        self.status_var.set(f"Preview complete. {len(self.planned_moves)} files ready to organize.")

    def _organize(self):
        """Execute file organization."""
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        # Confirm if no preview was done
        if not self.planned_moves:
            organizer = FileOrganizer(folder)
            self.planned_moves = organizer.scan_files()

            if not self.planned_moves:
                messagebox.showinfo("Nothing to Do", "No files need to be organized.")
                return

        # Confirm action
        if not messagebox.askyesno(
            "Confirm Organization",
            f"This will move {len(self.planned_moves)} files.\n\nContinue?"
        ):
            return

        self._clear_results()
        self.progress_var.set(0)

        organizer = FileOrganizer(folder)

        def move_progress(current, total, filename):
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_var.set(f"Moving ({current}/{total}): {filename}")
            self.root.update_idletasks()

        result = organizer.execute_moves(self.planned_moves, progress_callback=move_progress)

        # Save backup if any files were moved
        backup_path = None
        if result.move_log:
            backup_path = BackupManager.save_backup(folder, result.move_log)

        # Show results
        self._append_result("=== ORGANIZATION COMPLETE ===\n")
        self._append_result(f"Files moved: {result.moved}")
        self._append_result(f"Errors: {result.errors}")

        if backup_path:
            self._append_result(f"\nBackup saved: {backup_path.name}")
            self._append_result("Use 'Restore...' to undo this operation.")

        if result.error_messages:
            self._append_result("\nErrors encountered:")
            for error in result.error_messages:
                self._append_result(f"  - {error}")

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
            messagebox.showinfo("No Backups", "No backup files found.\n\nBackups are created automatically when you organize files.")
            return

        # Create restore dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Restore from Backup")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # Main frame
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Select a backup to restore:").pack(anchor="w", pady=(0, 5))

        # Listbox with backups
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=5)

        listbox = tk.Listbox(list_frame, height=10)
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        # Populate listbox
        for backup in backups:
            display = f"{backup.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {backup.file_count} files"
            listbox.insert(tk.END, display)

        # Details label
        details_var = tk.StringVar(value="Select a backup to see details")
        details_label = ttk.Label(frame, textvariable=details_var, wraplength=450)
        details_label.pack(anchor="w", pady=5)

        def on_select(event):
            selection = listbox.curselection()
            if selection:
                backup = backups[selection[0]]
                details_var.set(f"Source folder: {backup.source_folder}\nFile: {backup.filepath.name}")

        listbox.bind('<<ListboxSelect>>', on_select)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(10, 0))

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

        ttk.Button(btn_frame, text="Restore", command=do_restore).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Backup", command=do_delete).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)

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

        self._append_result(f"=== RESTORING FROM BACKUP ===")
        self._append_result(f"Backup date: {backup_info.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self._append_result(f"Source folder: {backup_info.source_folder}")
        self._append_result(f"Files to restore: {backup_info.file_count}\n")

        def restore_progress(current, total, filename):
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_var.set(f"Restoring ({current}/{total}): {filename}")
            self.root.update_idletasks()

        result = BackupManager.execute_restore(backup_data, progress_callback=restore_progress)

        self._append_result(f"\n=== RESTORE COMPLETE ===\n")
        self._append_result(f"Files restored: {result.moved}")
        self._append_result(f"Errors: {result.errors}")

        if result.error_messages:
            self._append_result("\nErrors encountered:")
            for error in result.error_messages:
                self._append_result(f"  - {error}")

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
