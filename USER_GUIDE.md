# File Organizer User Guide

## Start the App

Run:

```bash
python main.py
```

## Organize Files

1. Click **Browse** and select a folder.
2. Click **Preview** to see where files will be moved.
3. Click **Organize Files** to move files into category folders.
4. If you ever make a mistake or want to revert, click **Undo** to restore all files back to their exact original locations.

Files are moved into the selected output folder. By default, this is `Organized_Files`.

## Preferences

- **Output folder**: Change the parent folder where organized files are stored.
- **Include subfolders**: Also scan files inside subdirectories.
- **Detect duplicates (SHA-256)**: When checked, identical files (matching content hash) are isolated into a `Duplicates` folder to keep your main categories clean.
- **Custom Category**: Add your own category name and extensions.

Example:

- Name: `Design`
- Extensions: `.psd .ai .fig`

## Undo / Rollback

- Click the **Undo** button anytime after organizing files to revert the most recent batch.
- Restores files to their original paths and cleans up empty category directories.
- Each undo operation is recorded in the session history and audit log.

## Logs

Each organize and undo operation writes details to:

```text
Organized_Files/organizer.log
```

The log includes timestamps, moved and restored file paths, categories, duplicate status, and total files processed.
