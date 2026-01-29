# File Organizer

A Windows desktop application that automatically organizes files by type and date into a clean folder hierarchy.

## Features

- **Automatic categorization** - Files sorted into Images, Documents, Videos, Audio, Archives, or Other
- **Date-based organization** - Subfolders by year and month based on file creation/modified date
- **Preview mode** - See exactly what will happen before committing changes
- **Backup & Restore** - Automatically saves snapshots; undo organization with one click
- **Duplicate handling** - Safely renames files when conflicts occur
- **No dependencies** - Pure Python with tkinter (included with Python on Windows)

## Folder Structure

```
Your Folder/
├── Images/
│   └── 2024/
│       └── 03-March/
│           └── photo.jpg
├── Documents/
│   └── 2023/
│       └── 11-November/
│           └── report.pdf
└── Videos/
    └── 2024/
        └── 01-January/
            └── clip.mp4
```

## Usage

```bash
python file_organizer.py
```

1. Click **Browse...** to select a folder
2. Click **Preview (Dry Run)** to see planned changes
3. Click **Organize Files** to execute (creates automatic backup)
4. Click **Restore...** to undo if needed

## Supported File Types

| Category  | Extensions                          |
|-----------|-------------------------------------|
| Images    | jpg, jpeg, png, gif, bmp, webp, svg |
| Documents | pdf, doc, docx, txt, xlsx, pptx     |
| Videos    | mp4, avi, mov, mkv, wmv             |
| Audio     | mp3, wav, flac, aac                 |
| Archives  | zip, rar, 7z, tar                   |
| Other     | Everything else                     |

## Requirements

- Python 3.10+
- Windows (uses native file creation dates)

## License

MIT
