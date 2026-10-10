# File Organizer

This Python project organizes files in a selected directory by moving them into folders such as Images, Documents, Videos, Audio, Archives, Code, Applications, Fonts, and Others.

## Week 1 Focus

The Week 1 report describes these goals:

- Scan a directory.
- Identify file types using file extensions.
- Create category folders when needed.
- Move files into the correct folders.
- Handle already existing folders with conditional checks.
- Use Python file handling with `os` or `shutil`.

This version implements those points and also includes a simple Tkinter interface so the user can select a directory easily.

## Files

- `main.py`: Tkinter user interface with preview, organize, undo, and preferences.
- `organizer.py`: File categorization, SHA-256 duplicate detection, and rollback/undo logic.
- `settings.py`: Saved preferences for directory, output folder, recursive mode, duplicate detection, and custom categories.
- `USER_GUIDE.md`: User-facing instructions.
- `test_organizer.py`: Unit tests for the backend organizer logic.

## How to Run

### Option 1: Standalone Windows App (.exe)
Double-click `dist/FileOrganizer.exe` (no Python needed).

### Option 2: Run via Python
```bash
python main.py
```

Choose a folder, then click **Organize Files**.

## Week 2 Updates

- Added support for more file types, including audio, archives, code files, applications, fonts, and structured document formats.
- Added an `Organized_Files` folder so category folders stay together in one clean location.
- Added a **Preview** button to scan files before moving them.
- Added status messages and clearer error handling in the GUI.
- Kept the logic modular with `main.py` for the interface and `organizer.py` for backend file handling.

## Week 3 Updates

- Improved the GUI with a clear button, progress indicator, and cleaner status updates.
- Moved scan and organize operations to background threads so the interface remains responsive with larger folders.
- Limited very large result displays while still showing the total number of files processed.
- Improved preview accuracy when duplicate destination file names already exist.
- Continued code refinement with reusable GUI helper methods.

## Safety & Collision Handling

- If a file with the same name already exists in a category folder, the program keeps both files by adding a number to the new file name.
- If identical file content is detected, it is safely isolated into the `Duplicates` category.

## Week 4 Updates

- Added custom category support so users can define their own sorting rules.
- Added saved preferences using `settings.json`.
- Added optional recursive scanning for subfolders.
- Added operation logging with timestamps in `organizer.log`.
- Added a user guide and unit tests.

## Advanced Enhancements

- **Content-Based Duplicate Detection**: Uses chunked SHA-256 hashing to find identical file contents regardless of filename, isolating duplicates into a dedicated `Duplicates` directory.
- **Date-Based Subfolder Grouping**: Hierarchically organizes files into Year/Month subfolders (e.g. `Images/2026/10/`) based on modification timestamps.
- **System & Hidden File Protection**: Automatically filters out OS files (`desktop.ini`, `Thumbs.db`, `.DS_Store`) and hidden dotfiles, preserving Windows configurations.
- **One-Click Folder Access**: Provides a dedicated **Open Folder** button to launch the organized directory directly in Windows Explorer.
- **One-Click Undo / Rollback Engine**: Maintains session history in `.organizer_history.json`. Clicking **Undo** restores files back to their exact original locations and cleans up empty category folders.
- **Audit Logging**: Logs all moves, duplicates, and rollbacks with exact timestamps.

## Testing

Run:

```bash
python -m unittest test_organizer.py
```

## Building Standalone Executable (.exe)

To bundle the application into a single standalone `.exe` with the embedded icon:

```bash
pyinstaller --noconsole --onefile --icon="app_icon.ico" --add-data="app_icon.ico;." --name="FileOrganizer" --clean main.py
```

The resulting executable will be generated inside the `dist/` directory.

