from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from organizer import (
    can_undo,
    is_system_or_hidden,
    organize_directory,
    scan_directory,
    undo_last_operation,
)


class OrganizerTests(unittest.TestCase):
    def test_organizes_known_and_unknown_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "image.jpg").write_text("image", encoding="utf-8")
            (root / "notes.unknown").write_text("other", encoding="utf-8")

            moved = organize_directory(root, enable_logging=False)
            destinations = {result.destination.relative_to(root) for result in moved}

            self.assertIn(Path("Organized_Files/Images/image.jpg"), destinations)
            self.assertIn(Path("Organized_Files/Others/notes.unknown"), destinations)

    def test_custom_category_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "mock.dat").write_text("data", encoding="utf-8")

            preview = scan_directory(root, {"Data": [".dat"]})

            self.assertEqual(preview[0].category, "Data")

    def test_duplicate_names_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / "Organized_Files" / "Documents"
            existing.mkdir(parents=True)
            (existing / "report.pdf").write_text("old", encoding="utf-8")
            (root / "report.pdf").write_text("new", encoding="utf-8")

            moved = organize_directory(root, enable_logging=False)

            self.assertEqual(moved[0].destination.name, "report_1.pdf")

    def test_detects_duplicate_files_by_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            # Create two files with different names but identical content
            (root / "doc1.txt").write_text("identical content", encoding="utf-8")
            (root / "doc2.txt").write_text("identical content", encoding="utf-8")
            (root / "doc3.txt").write_text("unique content", encoding="utf-8")

            preview = scan_directory(root, detect_duplicates=True)
            duplicates = [r for r in preview if r.is_duplicate]
            self.assertEqual(len(duplicates), 1)
            self.assertEqual(duplicates[0].category, "Duplicates")

            moved = organize_directory(root, detect_duplicates=True, enable_logging=False)
            moved_duplicates = [r for r in moved if r.is_duplicate]
            self.assertEqual(len(moved_duplicates), 1)
            self.assertTrue((root / "Organized_Files" / "Duplicates" / "doc2.txt").exists())
            self.assertTrue((root / "Organized_Files" / "Documents" / "doc1.txt").exists())
            self.assertTrue((root / "Organized_Files" / "Documents" / "doc3.txt").exists())

    def test_undo_last_operation_restores_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file1 = root / "photo.jpg"
            file2 = root / "notes.txt"
            file1.write_text("photo-data", encoding="utf-8")
            file2.write_text("notes-data", encoding="utf-8")

            self.assertFalse(can_undo(root))

            moved = organize_directory(root, enable_logging=False, enable_history=True)
            self.assertEqual(len(moved), 2)
            self.assertFalse(file1.exists())
            self.assertFalse(file2.exists())
            self.assertTrue(can_undo(root))

            # Perform undo
            restored = undo_last_operation(root, enable_logging=False)
            self.assertEqual(len(restored), 2)

            # Check that original files are restored in their original places
            self.assertTrue(file1.exists())
            self.assertTrue(file2.exists())
            self.assertEqual(file1.read_text(encoding="utf-8"), "photo-data")
            self.assertEqual(file2.read_text(encoding="utf-8"), "notes-data")

            # Check that Organized_Files category folders were cleaned up
            self.assertFalse((root / "Organized_Files" / "Images").exists())
            self.assertFalse((root / "Organized_Files" / "Documents").exists())
            self.assertFalse(can_undo(root))

    def test_undo_when_no_history_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(RuntimeError):
                undo_last_operation(root)

    def test_organize_with_date_grouping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            photo = root / "vacation.png"
            photo.write_text("photo data", encoding="utf-8")

            # Fixed mtime: 2024-05-15 12:00:00
            target_time = 1715774400.0  # May 15, 2024
            import os
            os.utime(str(photo), (target_time, target_time))

            # Preview test
            preview = scan_directory(root, group_by_date=True)
            self.assertEqual(len(preview), 1)
            expected_dest = root / "Organized_Files" / "Images" / "2024" / "05" / "vacation.png"
            self.assertEqual(preview[0].destination, expected_dest)

            # Move test
            moved = organize_directory(root, group_by_date=True, enable_logging=False, enable_history=True)
            self.assertEqual(len(moved), 1)
            self.assertTrue(expected_dest.exists())
            self.assertFalse(photo.exists())

            # Undo test
            restored = undo_last_operation(root, enable_logging=False)
            self.assertEqual(len(restored), 1)
            self.assertTrue(photo.exists())
            self.assertFalse(expected_dest.exists())
            # Date subfolders should be removed
            self.assertFalse((root / "Organized_Files" / "Images" / "2024").exists())
            self.assertFalse((root / "Organized_Files" / "Images").exists())

    def test_date_grouping_with_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file1 = root / "original.txt"
            file2 = root / "duplicate.txt"
            file1.write_text("same content", encoding="utf-8")
            file2.write_text("same content", encoding="utf-8")

            target_time = 1715774400.0  # May 15, 2024
            import os
            os.utime(str(file1), (target_time, target_time))
            os.utime(str(file2), (target_time, target_time))

            moved = organize_directory(
                root,
                detect_duplicates=True,
                group_by_date=True,
                enable_logging=False,
            )
            self.assertEqual(len(moved), 2)
            dup_results = [r for r in moved if r.is_duplicate]
            self.assertEqual(len(dup_results), 1)
            expected_dup_dir = root / "Organized_Files" / "Duplicates" / "2024" / "05"
            self.assertEqual(dup_results[0].destination.parent, expected_dup_dir)
            self.assertTrue(dup_results[0].destination.exists())

    def test_is_system_or_hidden(self) -> None:
        self.assertTrue(is_system_or_hidden(Path("desktop.ini")))
        self.assertTrue(is_system_or_hidden(Path("Thumbs.db")))
        self.assertTrue(is_system_or_hidden(Path(".DS_Store")))
        self.assertTrue(is_system_or_hidden(Path(".gitignore")))
        self.assertTrue(is_system_or_hidden(Path(".organizer_history.json")))
        self.assertTrue(is_system_or_hidden(Path("organizer.log")))
        self.assertFalse(is_system_or_hidden(Path("presentation.pptx")))
        self.assertFalse(is_system_or_hidden(Path("song.mp3")))

    def test_ignores_system_and_hidden_files_during_organize(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sys_file1 = root / "desktop.ini"
            sys_file2 = root / "thumbs.db"
            hidden_file = root / ".env"
            regular_file = root / "invoice.pdf"

            sys_file1.write_text("[.ShellClassInfo]", encoding="utf-8")
            sys_file2.write_text("cache", encoding="utf-8")
            hidden_file.write_text("SECRET=123", encoding="utf-8")
            regular_file.write_text("Invoice data", encoding="utf-8")

            # Preview ignores system and hidden files by default
            preview = scan_directory(root, ignore_hidden=True)
            self.assertEqual(len(preview), 1)
            self.assertEqual(preview[0].source.name, "invoice.pdf")

            # Organize ignores system and hidden files by default
            moved = organize_directory(root, ignore_hidden=True, enable_logging=False)
            self.assertEqual(len(moved), 1)
            self.assertEqual(moved[0].source.name, "invoice.pdf")

            # Verify system/hidden files were untouched in the root directory
            self.assertTrue(sys_file1.exists())
            self.assertTrue(sys_file2.exists())
            self.assertTrue(hidden_file.exists())
            self.assertFalse(regular_file.exists())
            self.assertTrue((root / "Organized_Files" / "Documents" / "invoice.pdf").exists())

            # Verify that if ignore_hidden=False, system/hidden files are included
            scan_all = scan_directory(root, ignore_hidden=False)
            self.assertEqual(len(scan_all), 3)


if __name__ == "__main__":
    unittest.main()
