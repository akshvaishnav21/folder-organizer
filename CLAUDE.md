# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

File Organizer is a Windows desktop application (Python/tkinter) that organizes files by type and date into a hierarchical folder structure: `[Category]/[Year]/[Month]/files`.

## Running the Application

```bash
python file_organizer.py
```

No external dependencies required—uses only Python standard library (tkinter, pathlib, shutil, dataclasses).

## Architecture

Single-file application with clear separation of concerns:

- **`EXTENSION_CATEGORIES`** / **`MONTH_NAMES`** - Configuration constants for file categorization
- **`FileMove`** / **`OrganizeResult`** - Dataclasses for operation data
- **`FileOrganizer`** - Core logic class handling file scanning, categorization, date extraction, and move execution
- **`FileOrganizerApp`** - tkinter GUI class

### Key Logic Flow

1. `scan_files()` builds a list of `FileMove` objects (preview/dry-run)
2. `execute_moves()` performs the actual file operations with progress callbacks
3. Files already in the organized structure (`Category/Year/Month`) are automatically skipped
4. Duplicate filenames handled by appending `_1`, `_2`, etc.

### Backup/Restore System

- **`BackupManager`** - Handles saving/loading/restoring backup snapshots
- Backups stored as JSON in `backups/` folder (next to script)
- Each backup records original path → destination path for every moved file
- Restore recreates original directory structure and moves files back

### File Categories

Images, Documents, Videos, Audio, Archives, Other (fallback). Extend `EXTENSION_CATEGORIES` dict to add new mappings.
