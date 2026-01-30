# Folder Organizer

A modern Windows desktop application that automatically organizes files by type and/or date into a clean folder hierarchy.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

### Organization Modes
- **By Type** — Sort into category folders (Images/, Documents/, Videos/...)
- **By Date** — Sort by year and month (2024/01-January/...)
- **By Type & Date** — Combined hierarchy (Images/2024/01-January/...)

### Smart File Handling
- Automatic categorization based on file extensions
- Compound extensions support (.tar.gz, .tar.bz2, etc.)
- Files with no extension → "No Extension" category
- Uses file creation date (falls back to modified date)
- Invalid dates → "Unknown" folder
- Duplicate filename protection with auto-numbering

### Robust Error Handling
- **Permission errors** — Skips locked, in-use, or inaccessible files
- **System files** — Automatically skipped
- **Path length** — Warns if destination exceeds 260 chars
- **System folders** — Warning when selecting Windows/Program Files
- **Graceful cancellation** — Cancel button to stop mid-operation

### Options
- Include/exclude hidden files
- Include/exclude shortcuts and symlinks
- **Preserve folders** — Move entire folders as units (By Date mode only)
- **Flatten all files** — Ignore folder structure and sort all files individually
- Delete empty folders after organizing

### File Analysis
- **Pie chart visualization** — See file extension distribution before organizing
- Color-coded chart with legend showing counts and percentages
- Top 8 extensions displayed, smaller groups combined as "Other"

### Safety Features
- **Preview mode** — See all changes before applying
- **Automatic backup** — JSON log of all moves saved before organizing
- **One-click restore** — Undo any organization operation
- **Detailed logging** — Summary of files moved, skipped (with reasons), and errors

## Screenshot

```
┌────────────────────────────────────────────────────────────┐
│  Folder Organizer                                          │
│  Automatically organize your files by type and date        │
│                                                            │
│  Select Folder                                             │
│  ┌──────────────────────────────────┐ ┌──────────┐        │
│  │ C:/Users/Documents/Downloads     │ │ Browse.. │        │
│  └──────────────────────────────────┘ └──────────┘        │
│                                                            │
│  Organization Mode                                         │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ○ By Type        Images/, Documents/, Videos/...   │   │
│  │ ○ By Date        2024/01-January/...               │   │
│  │ ● By Type & Date Images/2024/01-January/...        │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  Options                                                   │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ☐ Include hidden files    ☐ Include shortcuts      │   │
│  │ ☐ Preserve folders        ☐ Flatten all files      │   │
│  │ ☐ Delete empty folders after organizing            │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  [Preview] [Organize Files] [Cancel]          [Restore...] │
│                                                            │
│  File Extension Analysis                                   │
│  ┌────────────────────────────────────────────────────┐   │
│  │  [PIE]    .jpg: 45 (28.8%)  .pdf: 32 (20.5%)      │   │
│  │  [CHART]  .png: 28 (17.9%)  .docx: 18 (11.5%)     │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

## Installation

1. Install the optional dependency for modern UI styling:

```bash
pip install ttkbootstrap
```

2. Run the application:

```bash
python file_organizer.py
```

**Requirements:**
- Python 3.10 or higher
- Windows (uses native file creation dates and Windows API)
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) (optional, for modern dark theme UI)

> **Note:** The app works without ttkbootstrap but will use the default tkinter appearance.

## Usage

1. **Select a folder** — Click "Browse..." to choose the folder to organize
2. **Choose organization mode** — Select how you want files sorted
3. **Configure options** — Include hidden files, symlinks, folder handling, or enable empty folder cleanup
4. **Preview changes** — Click "Preview Changes" to see what will happen
5. **Organize** — Click "Organize Files" to execute (backup is automatic)
6. **Restore if needed** — Click "Restore..." to undo any organization

## Supported File Types

| Category     | Extensions                                              |
|--------------|---------------------------------------------------------|
| Images       | jpg, jpeg, png, gif, bmp, webp, svg, ico, tiff, raw, heic, avif |
| Documents    | pdf, doc, docx, txt, xlsx, pptx, xls, ppt, odt, rtf, csv, md, epub |
| Videos       | mp4, avi, mov, mkv, wmv, flv, webm, m4v, mpeg, 3gp     |
| Audio        | mp3, wav, flac, aac, wma, ogg, m4a, opus, aiff, midi   |
| Archives     | zip, rar, 7z, tar, tar.gz, tar.bz2, gz, bz2, xz, iso   |
| Code         | py, js, ts, html, css, java, cpp, c, h, json, xml, sql, php, go, rs |
| Executables  | exe, msi, app, deb, rpm, apk                           |
| Fonts        | ttf, otf, woff, woff2, eot                             |
| No Extension | Files without any extension                             |
| Other        | Everything else                                         |

## Folder Handling

When your source folder contains subfolders, you have three options:

| Option | Behavior |
|--------|----------|
| **Default** | Only root-level files are sorted; subfolders are left untouched |
| **Preserve folders** | Move entire folders as units into date-based hierarchy (By Date mode only) |
| **Flatten all files** | Ignore folder structure and sort all files from all subfolders |

**Examples:**

With **Preserve folders** enabled (By Date mode):
```
Downloads/
  ProjectA/          →    2024/01-January/ProjectA/
    file1.txt
    file2.doc
```

With **Flatten all files** enabled:
```
Downloads/
  ProjectA/
    photo.jpg        →    Images/2024/01-January/photo.jpg
    report.pdf       →    Documents/2024/02-February/report.pdf
```

> **Note:** Preserve folders only works with "By Date" mode since folders cannot be categorized by file type.

## Skip Reasons

Files may be skipped for the following reasons:
- **Already organized** — File is already in the correct structure
- **Permission denied** — No access to the file
- **File in use** — File is locked by another process
- **System file** — Windows system file attribute
- **Hidden file** — Hidden files (when option is disabled)
- **Symlink/shortcut** — Symbolic links or .lnk files (when option is disabled)
- **Path too long** — Destination path exceeds 260 characters

## Backup & Restore

- **Automatic backups** are saved to the `backups/` folder next to the application
- Each backup is a JSON file containing:
  - Timestamp and source folder
  - List of all file moves (original → destination)
  - List of skipped files with reasons
- **Restore** moves files back to their exact original locations
- Backups can be deleted after successful restore

## License

MIT
