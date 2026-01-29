# Folder Organizer

A modern Windows desktop application that automatically organizes files by type and/or date into a clean folder hierarchy.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Three Organization Modes**
  - **By Type** — Sort into category folders (Images/, Documents/, Videos/...)
  - **By Date** — Sort by year and month (2024/01-January/...)
  - **By Type & Date** — Combined hierarchy (Images/2024/01-January/...)

- **Smart File Handling**
  - Automatic categorization based on file extensions
  - Uses file creation date (falls back to modified date)
  - Duplicate filename protection with auto-numbering
  - Skips files already in the correct location

- **Safety First**
  - Preview mode to see changes before applying
  - Automatic backup before every organization
  - One-click restore to undo changes

- **Modern UI**
  - Clean, dark-themed interface
  - Real-time progress tracking
  - Detailed operation results

## Screenshot

```
┌─────────────────────────────────────────────────────────┐
│  Folder Organizer                                         │
│  Automatically organize your files by type and date     │
│                                                         │
│  Select Folder                                          │
│  ┌─────────────────────────────────┐ ┌─────────┐       │
│  │ C:/Users/Documents/Downloads    │ │ Browse..│       │
│  └─────────────────────────────────┘ └─────────┘       │
│                                                         │
│  Organization Mode                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ○ By Type      Images/, Documents/, Videos/...  │   │
│  │ ○ By Date      2024/01-January/...              │   │
│  │ ● By Type & Date  Images/2024/01-January/...    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Preview Changes]  [Organize Files]      [Restore...] │
│                                                         │
│  ████████████████████████░░░░░░░░░░░░░░░░  65%         │
│  Moving (13/20): photo.jpg                              │
│                                                         │
│  Results                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ PREVIEW: 20 files will be organized             │   │
│  │ Images (12 files)                               │   │
│  │   photo.jpg → Images/2024/03-March/photo.jpg   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Installation

No installation required. Just run with Python:

```bash
python file_organizer.py
```

**Requirements:**
- Python 3.10 or higher
- Windows (uses native file creation dates)
- No external dependencies (uses only standard library)

## Usage

1. **Select a folder** — Click "Browse..." to choose the folder to organize
2. **Choose organization mode** — Select how you want files sorted
3. **Preview changes** — Click "Preview Changes" to see what will happen
4. **Organize** — Click "Organize Files" to execute (backup is automatic)
5. **Restore if needed** — Click "Restore..." to undo any organization

## Supported File Types

| Category   | Extensions                                    |
|------------|-----------------------------------------------|
| Images     | jpg, jpeg, png, gif, bmp, webp, svg, ico, tiff, raw |
| Documents  | pdf, doc, docx, txt, xlsx, pptx, xls, ppt, odt, rtf, csv |
| Videos     | mp4, avi, mov, mkv, wmv, flv, webm, m4v       |
| Audio      | mp3, wav, flac, aac, wma, ogg, m4a            |
| Archives   | zip, rar, 7z, tar, gz, bz2                    |
| Code       | py, js, html, css, java, cpp, c, h, json, xml, sql |
| Other      | Everything else                               |

## Folder Structure Examples

**By Type:**
```
Downloads/
├── Images/
│   └── photo.jpg
├── Documents/
│   └── report.pdf
└── Videos/
    └── clip.mp4
```

**By Date:**
```
Downloads/
├── 2024/
│   ├── 01-January/
│   │   └── photo.jpg
│   └── 03-March/
│       └── report.pdf
└── 2023/
    └── 12-December/
        └── clip.mp4
```

**By Type & Date (Recommended):**
```
Downloads/
├── Images/
│   └── 2024/
│       └── 01-January/
│           └── photo.jpg
├── Documents/
│   └── 2024/
│       └── 03-March/
│           └── report.pdf
└── Videos/
    └── 2023/
        └── 12-December/
            └── clip.mp4
```

## Backup & Restore

- **Automatic backups** are saved to the `backups/` folder next to the application
- Each backup records the original and new location of every moved file
- **Restore** moves files back to their exact original locations
- Backups can be deleted after successful restore

## License

MIT
