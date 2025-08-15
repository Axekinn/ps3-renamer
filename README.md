# PS3 File Renamer

A Python tool for automatically renaming PS3 game update files (.pkg) with proper formatting using game database information.

## 🎮 Overview

This tool helps organize PS3 game update files by renaming them from cryptic package names to a clean, readable format. It uses a CSV database to match title IDs with game names and versions.

**Example transformation:**
```
EP9000-BCES00011_00-SINGSTARPS3V0600-A0600-V0100-PE.pkg
↓
SingStar [UPDATE 06.00][BCES-00011].pkg
```

## ✨ Features

- **Preview Mode**: See what will be renamed before making changes
- **Automatic Backup**: Optional safety backup of original files
- **Smart Title ID Detection**: Handles multiple PS3 package filename formats
- **Version Extraction**: Automatically detects update versions
- **Error Handling**: Comprehensive validation and logging
- **Progress Tracking**: Clear status reporting throughout the process

## 📋 Requirements

- Python 3.6+
- Standard library modules only (no external dependencies)

## 🚀 Installation

1. Clone this repository:
```bash
git clone https://github.com/Axekinn/ps3-file-renamer.git
cd ps3-file-renamer
```

2. Ensure your CSV database file is in the correct location:
```
/home/admin/Downloads/ps3-update-scraper-main/ps3_titles_updates/ps3_titles_download_links.csv (or whatever u put the folder, but change the path in the code then)
```

## 💻 Usage

1. Run the script:
```bash
python ps3-renamer.py
```

2. Enter the path to your folder containing .pkg files when prompted

3. Review the preview of what files will be renamed

4. Choose whether to create a backup (recommended)

5. Confirm the renaming operation

## 📊 CSV Database Format

The tool expects a CSV file with the following columns:
- `Title_ID`: Game title identifier (e.g., BCES-00011)
- `Title_Name`: Basic game title
- `Sony_Game_Name`: Official Sony game name (preferred)
- `Version`: Update version (e.g., 06.00)

## 🔧 Supported Filename Formats

The tool can extract title IDs from various PS3 package formats:
- `EP9000-BCES00011_00-SINGSTARPS3V0600-A0600-V0100-PE.pkg`
- `UP9000-BCUS98148_00-GAMEUPDATE-A0101-V0100.pkg`
- `BCES-00011_update.pkg`
- And more variations

## 🛡️ Safety Features

### Preview Mode
Before making any changes, the tool shows:
- ✓ Files ready to rename
- ⏭ Files that will be skipped
- ⚠ Files with warnings
- ✗ Files with errors

### Automatic Backup
Creates a `backup_before_rename` folder containing copies of all original files, allowing you to restore them if needed.

### Validation
- Checks for existing target filenames
- Validates title ID extraction
- Verifies game data availability
- Sanitizes filenames for compatibility

## 📝 Output Format

Renamed files follow this pattern:
```
[Game Name] [UPDATE [Version]][[Title ID]].pkg
```

Examples:
- `Killzone 2 [UPDATE 01.29][BCES-00081].pkg`
- `Uncharted Drake's Fortune [UPDATE 01.01][BCES-00065].pkg`
- `Fallout 3 [UPDATE 01.61][BLES-00399].pkg`

## 📋 Logging

The tool generates a detailed log file (`rename_log.txt`) containing:
- All operations performed
- Error messages and warnings
- File rename confirmations
- Timestamps for audit purposes

## 🔍 Example Session

```
PS3 File Renamer - Automatic Renaming Tool
==================================================

Enter the path to the folder containing .pkg files: /path/to/pkg/files

================================================================================
PREVIEW MODE - Analyzing files for renaming...
================================================================================

Found 3 files to analyze:

✓ READY: EP9000-BCES00011_00-SINGSTARPS3V0600-A0600-V0100-PE.pkg
    --> SingStar [UPDATE 06.00][BCES-00011].pkg

⏭ SKIP: Already Formatted Game [UPDATE 01.00][BCES-12345].pkg (SKIP - Already formatted)

✗ ERROR: UNKNOWN-GAME123_00-PATCH.pkg (ERROR - Could not extract title ID)

================================================================================
SUMMARY:
  Files ready to rename: 1
  Files to skip: 1
  Files with warnings: 0
  Files with errors: 1
================================================================================

BACKUP OPTION:
A backup creates a safety copy of all your .pkg files in a
'backup_before_rename' folder before proceeding with renaming. This allows you to
restore the original names in case of any issues.

Do you want to create a backup before renaming? (y/n): y
✓ Backup created in: /path/to/pkg/files/backup_before_rename

Do you want to proceed with renaming 1 files?
Confirm renaming? (y/n): y

Renaming in progress...

================================================================================
RESULTS:
Files successfully renamed: 1

Renamed files:
  EP9000-BCES00011_00-SINGSTARPS3V0600-A0600-V0100-PE.pkg
  --> SingStar [UPDATE 06.00][BCES-00011].pkg

================================================================================

Renaming completed successfully!
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is designed to work with legitimate PS3 game update files. Always ensure you have proper backups before running any file renaming operations.

## 🐛 Troubleshooting

### Common Issues

**"CSV file not found"**
- Ensure the CSV file exists at the specified path
- Check file permissions

**"Could not extract title ID"**
- The filename format might not be recognized
- Check if the file is actually a PS3 update package

**"No game data found"**
- The title ID might not exist in the CSV database
- Verify the CSV file contains the game information

**"Target file already exists"**
- A file with the new name already exists
- The tool will skip renaming to prevent overwrites

---

*Made with ❤️ for the PS3 homebrew community*
