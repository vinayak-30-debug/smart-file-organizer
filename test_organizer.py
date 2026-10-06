from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from organizer import (
    can_undo,
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


if __name__ == "__main__":
    unittest.main()
