# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

File Organizer is a Windows desktop application (Python/tkinter) that organizes files into a hierarchical folder structure based on type and/or date.

## Running the Application

```bash
python file_organizer.py
```

No external dependencies—uses only Python standard library (tkinter, pathlib, shutil, dataclasses, enum).

## Architecture

Single-file application (`file_organizer.py`) with clear separation:

### Core Classes

- **`SortMode`** (Enum) - Organization modes: BY_TYPE, BY_DATE, BY_BOTH
- **`FileOrganizer`** - Core logic: scanning, categorization, date extraction, move execution
- **`BackupManager`** - Backup/restore operations with JSON storage
- **`ModernStyle`** - UI theming and styling configuration
- **`FileOrganizerApp`** - tkinter GUI

### Data Classes

- **`FileMove`** - Planned move operation (source, destination, category, year, month)
- **`OrganizeResult`** - Operation result with move log for backup
- **`BackupInfo`** - Backup metadata (filepath, timestamp, source_folder, file_count)

### Configuration

- **`EXTENSION_CATEGORIES`** - Maps file extensions to category names
- **`MONTH_NAMES`** - Month number to folder name mapping

### Key Logic Flow

1. User selects folder and organization mode
2. `scan_files()` builds list of `FileMove` objects (preview)
3. `execute_moves()` performs moves and logs them for backup
4. `BackupManager.save_backup()` stores move log as JSON
5. Restore reads backup and reverses moves

### Extending Categories

Add new extensions to `EXTENSION_CATEGORIES` dict:
```python
'.ext': 'CategoryName'
```
