# Claude Project Guide

## Project Overview

**Folder Organizer** is a Windows desktop application built with Python and tkinter/ttkbootstrap that automatically organizes files by type and/or date into a clean folder hierarchy.

## Tech Stack

- **Language:** Python 3.10+
- **GUI Framework:** tkinter with optional ttkbootstrap for modern styling
- **Platform:** Windows (uses Windows-specific APIs for file attributes)
- **Dependencies:**
  - Standard library only (required)
  - ttkbootstrap (optional, for dark theme UI)

## Project Structure

```
folder-organizer/
├── file_organizer.py    # Main application (single-file architecture)
├── README.md            # User documentation
├── CLAUDE.md            # This file - AI assistant guide
├── .gitignore           # Git ignore rules
└── backups/             # Auto-generated backup folder (gitignored)
```

## Architecture

The application follows a single-file architecture with clear class separation:

### Core Classes

1. **FileOrganizer** - Handles file organization logic
   - File scanning with `os.scandir` for performance
   - Category detection based on file extensions
   - Date extraction from file metadata
   - Path validation and duplicate handling

2. **BackupManager** - Manages backup/restore operations
   - JSON-based backup files
   - Restore functionality with conflict handling

3. **FileOrganizerApp** - Main GUI application
   - ttkbootstrap/tkinter UI with conditional styling
   - Threading for non-blocking operations
   - Queue-based UI updates from background threads

### Key Design Patterns

- **Dataclasses** for structured data (FileMove, FolderMove, SkippedFile, etc.)
- **Enums** for type safety (SortMode, SkipReason)
- **Threading + Queue** for responsive UI during long operations
- **Graceful degradation** when ttkbootstrap is unavailable

## Key Features

1. **Organization Modes:** By Type, By Date, By Type & Date
2. **Folder Handling:** Preserve folders, Flatten all files
3. **Pie Chart:** Visual file extension analysis
4. **Safety:** Preview mode, automatic backups, one-click restore
5. **Error Handling:** Skips locked/system files gracefully

## Code Conventions

- Use `_bootstyle()` helper for conditional ttkbootstrap styling
- Background operations use `_run_in_thread()` with `_task_queue` for UI updates
- Progress callbacks use batched updates (50-100ms intervals) for performance
- Path operations use `pathlib.Path` throughout

## Common Tasks

### Adding a New File Category
1. Add extensions to `EXTENSION_CATEGORIES` dict
2. Category name becomes the folder name

### Adding a New Option
1. Add `tk.BooleanVar` in `__init__`
2. Add checkbox in `_create_options_section`
3. Update `ScanOptions` dataclass
4. Update `_get_scan_options` method
5. Handle in `scan_files` method

### Adding UI Sections
1. Create `_create_*_section` method
2. Call it in `_create_widgets` in desired order
3. Use `_bootstyle()` for conditional theming

## Testing Locally

```bash
# Run with ttkbootstrap (modern UI)
pip install ttkbootstrap
python file_organizer.py

# Run without ttkbootstrap (basic UI)
python file_organizer.py
```

## Version History

- **2.4.0** - Added pie chart for file extension analysis
- **2.3.0** - Added folder preservation and flatten options
- **2.2.0** - Performance optimizations (threading, batched updates)
- **2.1.0** - Added ttkbootstrap support with superhero theme
- **2.0.0** - Initial release with backup/restore functionality
