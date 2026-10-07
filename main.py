from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from organizer import (
    MoveResult,
    can_undo,
    organize_directory,
    scan_directory,
    undo_last_operation,
)
from settings import load_settings, normalize_custom_categories, save_settings


DISPLAY_LIMIT = 300


class FileOrganizerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("File Organizer")
        self.geometry("900x640")
        self.minsize(780, 520)

        icon_path = (
            Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
            / "app_icon.ico"
        )
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.settings = load_settings()
        self.directory_var = tk.StringVar()
        self.output_folder_var = tk.StringVar(value=self.settings["output_folder"])
        self.recursive_var = tk.BooleanVar(value=self.settings["recursive"])
        self.detect_duplicates_var = tk.BooleanVar(
            value=self.settings.get("detect_duplicates", True)
        )
        self.category_var = tk.StringVar()
        self.extensions_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Choose a directory to organize.")
        self.action_buttons: list[ttk.Button] = []
        self.custom_categories = normalize_custom_categories(
            self.settings["custom_categories"]
        )

        if self.settings["last_directory"]:
            self.directory_var.set(self.settings["last_directory"])
            self.status_var.set("Loaded saved directory preference.")

        self._build_ui()
        self.refresh_undo_button_state()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        header = ttk.Label(
            self,
            text="File Organizer",
            font=("Segoe UI", 18, "bold"),
        )
        header.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        input_frame = ttk.Frame(self)
        input_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=8)
        input_frame.columnconfigure(0, weight=1)

        directory_entry = ttk.Entry(input_frame, textvariable=self.directory_var)
        directory_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        browse_button = ttk.Button(
            input_frame,
            text="Browse",
            command=self.choose_directory,
        )
        browse_button.grid(row=0, column=1, padx=(0, 8))
        self.action_buttons.append(browse_button)

        preview_button = ttk.Button(
            input_frame,
            text="Preview",
            command=self.preview_files,
        )
        preview_button.grid(row=0, column=2, padx=(0, 8))
        self.action_buttons.append(preview_button)

        organize_button = ttk.Button(
            input_frame,
            text="Organize Files",
            command=self.organize_files,
        )
        organize_button.grid(row=0, column=3, padx=(0, 8))
        self.action_buttons.append(organize_button)

        self.undo_button = ttk.Button(
            input_frame,
            text="Undo",
            command=self.undo_files,
            state=tk.DISABLED,
        )
        self.undo_button.grid(row=0, column=4, padx=(0, 8))
        self.action_buttons.append(self.undo_button)

        clear_button = ttk.Button(
            input_frame,
            text="Clear",
            command=self.clear_selection,
        )
        clear_button.grid(row=0, column=5)
        self.action_buttons.append(clear_button)

        options_frame = ttk.LabelFrame(self, text="Preferences")
        options_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=8)
        options_frame.columnconfigure(1, weight=1)

        ttk.Label(options_frame, text="Output folder").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(10, 8),
            pady=8,
        )
        ttk.Entry(options_frame, textvariable=self.output_folder_var).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8,
        )
        ttk.Checkbutton(
            options_frame,
            text="Include subfolders",
            variable=self.recursive_var,
            command=self.save_current_settings,
        ).grid(row=0, column=2, padx=12, pady=8)

        ttk.Checkbutton(
            options_frame,
            text="Detect duplicates (SHA-256)",
            variable=self.detect_duplicates_var,
            command=self.save_current_settings,
        ).grid(row=0, column=3, padx=12, pady=8)

        custom_frame = ttk.LabelFrame(self, text="Custom Category")
        custom_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=8)
        custom_frame.columnconfigure(1, weight=1)
        custom_frame.columnconfigure(3, weight=1)

        ttk.Label(custom_frame, text="Name").grid(row=0, column=0, padx=(10, 8), pady=8)
        ttk.Entry(custom_frame, textvariable=self.category_var).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8,
        )
        ttk.Label(custom_frame, text="Extensions").grid(row=0, column=2, padx=8, pady=8)
        ttk.Entry(custom_frame, textvariable=self.extensions_var).grid(
            row=0,
            column=3,
            sticky="ew",
            pady=8,
        )
        add_button = ttk.Button(custom_frame, text="Add Rule", command=self.add_custom_rule)
        add_button.grid(row=0, column=4, padx=(8, 10), pady=8)
        self.action_buttons.append(add_button)

        self.custom_rules_label = ttk.Label(custom_frame, text="")
        self.custom_rules_label.grid(
            row=1,
            column=0,
            columnspan=5,
            sticky="w",
            padx=10,
            pady=(0, 8),
        )
        self.refresh_custom_rules_label()

        result_frame = ttk.Frame(self)
        result_frame.grid(row=4, column=0, sticky="nsew", padx=18, pady=8)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_box = tk.Text(result_frame, wrap="word", height=12)
        self.result_box.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=self.result_box.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.result_box.configure(yscrollcommand=scrollbar.set)

        self.progress = ttk.Progressbar(self, mode="indeterminate")

        status = ttk.Label(self, textvariable=self.status_var)
        status.grid(row=6, column=0, sticky="w", padx=18, pady=(6, 14))

    def choose_directory(self) -> None:
        selected_directory = filedialog.askdirectory(title="Select Directory")
        if selected_directory:
            self.directory_var.set(selected_directory)
            self.save_current_settings()
            self.status_var.set("Directory selected. Ready to organize.")
            self.refresh_undo_button_state()

    def clear_selection(self) -> None:
        self.directory_var.set("")
        self.result_box.delete("1.0", tk.END)
        self.save_current_settings()
        self.status_var.set("Selection cleared. Choose a directory to organize.")
        self.refresh_undo_button_state()

    def refresh_undo_button_state(self) -> None:
        directory = self.directory_var.get().strip()
        output_folder = self.output_folder_var.get().strip() or "Organized_Files"
        if directory and can_undo(directory, output_folder):
            self.undo_button.configure(state=tk.NORMAL)
        else:
            self.undo_button.configure(state=tk.DISABLED)

    def add_custom_rule(self) -> None:
        category = self.category_var.get().strip()
        extensions_text = self.extensions_var.get().strip()
        if not category or not extensions_text:
            messagebox.showwarning(
                "Custom Rule Required",
                "Please enter both a category name and one or more extensions.",
            )
            return

        extensions = extensions_text.replace(",", " ").split()
        custom_categories = dict(self.custom_categories)
        existing_extensions = custom_categories.get(category, [])
        custom_categories[category] = list(existing_extensions) + extensions
        self.custom_categories = normalize_custom_categories(custom_categories)

        self.category_var.set("")
        self.extensions_var.set("")
        self.refresh_custom_rules_label()
        self.save_current_settings()
        self.status_var.set(f"Saved custom category: {category}.")

    def refresh_custom_rules_label(self) -> None:
        if not self.custom_categories:
            self.custom_rules_label.configure(text="No custom rules added.")
            return

        rules = []
        for category, extensions in sorted(self.custom_categories.items()):
            rules.append(f"{category}: {', '.join(extensions)}")
        self.custom_rules_label.configure(text=" | ".join(rules))

    def preview_files(self) -> None:
        directory = self.directory_var.get().strip()
        if not directory:
            messagebox.showwarning("Directory Required", "Please choose a directory first.")
            return

        self.result_box.delete("1.0", tk.END)
        self.save_current_settings()
        self.run_background_task(
            lambda: scan_directory(
                directory,
                self.custom_categories,
                self.output_folder_var.get().strip(),
                self.recursive_var.get(),
                detect_duplicates=self.detect_duplicates_var.get(),
            ),
            self.show_preview_results,
            "Scanning directory...",
            "Could not scan the selected directory.",
        )

    def show_preview_results(self, planned_files: list[MoveResult]) -> None:
        if not planned_files:
            self.result_box.insert(tk.END, "No files found to organize.\n")
            self.status_var.set("No files found.")
            return

        self.write_results("Preview summary", planned_files)
        dup_count = sum(1 for r in planned_files if r.is_duplicate)
        dup_text = f" ({dup_count} duplicate(s) flagged)" if dup_count > 0 else ""
        self.status_var.set(f"Found {len(planned_files)} file(s) ready to organize{dup_text}.")

    def organize_files(self) -> None:
        directory = self.directory_var.get().strip()
        if not directory:
            messagebox.showwarning("Directory Required", "Please choose a directory first.")
            return

        self.result_box.delete("1.0", tk.END)
        self.save_current_settings()
        self.run_background_task(
            lambda: organize_directory(
                directory,
                self.custom_categories,
                self.output_folder_var.get().strip(),
                self.recursive_var.get(),
                detect_duplicates=self.detect_duplicates_var.get(),
            ),
            self.show_organize_results,
            "Organizing files...",
            "Could not organize the selected directory.",
        )

    def show_organize_results(self, moved_files: list[MoveResult]) -> None:
        self.refresh_undo_button_state()
        if not moved_files:
            self.result_box.insert(tk.END, "No files found to organize.\n")
            self.status_var.set("No files were moved.")
            return

        self.write_results("Organized files", moved_files)
        dup_count = sum(1 for r in moved_files if r.is_duplicate)
        dup_text = f" (including {dup_count} duplicate(s) isolated)" if dup_count > 0 else ""
        self.status_var.set(f"Organized {len(moved_files)} file(s) successfully{dup_text}.")
        messagebox.showinfo("Done", f"Organized {len(moved_files)} file(s){dup_text}.\nYou can click Undo to revert anytime.")

    def undo_files(self) -> None:
        directory = self.directory_var.get().strip()
        if not directory:
            messagebox.showwarning("Directory Required", "Please choose a directory first.")
            return

        output_folder = self.output_folder_var.get().strip() or "Organized_Files"
        if not can_undo(directory, output_folder):
            messagebox.showinfo("Undo", "No previous organization operations found to undo.")
            return

        confirmed = messagebox.askyesno(
            "Confirm Undo",
            "Are you sure you want to restore the last batch of organized files back to their original locations?",
        )
        if not confirmed:
            return

        self.result_box.delete("1.0", tk.END)
        self.run_background_task(
            lambda: undo_last_operation(
                directory,
                output_folder,
            ),
            self.show_undo_results,
            "Undoing last operation...",
            "Could not undo the last operation.",
        )

    def show_undo_results(self, restored_files: list[MoveResult]) -> None:
        self.refresh_undo_button_state()
        if not restored_files:
            self.result_box.insert(tk.END, "No files needed to be restored.\n")
            self.status_var.set("No files restored.")
            return

        self.result_box.insert(
            tk.END,
            f"Undo complete! Restored {len(restored_files)} file(s) back to original locations:\n\n",
        )
        for result in restored_files[:DISPLAY_LIMIT]:
            self.result_box.insert(
                tk.END,
                f"Restored: {result.source.name} -> {result.destination}\n",
            )

        hidden_count = len(restored_files) - DISPLAY_LIMIT
        if hidden_count > 0:
            self.result_box.insert(
                tk.END,
                f"\nShowing first {DISPLAY_LIMIT} file(s). {hidden_count} more file(s) restored.\n",
            )

        self.status_var.set(f"Successfully restored {len(restored_files)} file(s).")
        messagebox.showinfo("Undo Complete", f"Restored {len(restored_files)} file(s) successfully.")

    def write_results(self, title: str, results: list[MoveResult]) -> None:
        category_counts = Counter(result.category for result in results)
        self.result_box.insert(tk.END, f"{title}:\n")

        for category, count in sorted(category_counts.items()):
            self.result_box.insert(tk.END, f"- {category}: {count} file(s)\n")

        duplicates = [r for r in results if r.is_duplicate]
        if duplicates:
            self.result_box.insert(
                tk.END,
                f"\nDuplicate files detected: {len(duplicates)} file(s) (routed to 'Duplicates')\n",
            )

        self.result_box.insert(tk.END, "\nFiles:\n")
        for result in results[:DISPLAY_LIMIT]:
            dup_tag = " [DUPLICATE]" if result.is_duplicate else ""
            self.result_box.insert(
                tk.END,
                f"{result.source.name} -> {self.format_destination(result)}{dup_tag}\n",
            )

        hidden_count = len(results) - DISPLAY_LIMIT
        if hidden_count > 0:
            self.result_box.insert(
                tk.END,
                f"\nShowing first {DISPLAY_LIMIT} file(s). {hidden_count} more file(s) processed.\n",
            )

    def run_background_task(
        self,
        task: Callable[[], list[MoveResult]],
        on_success: Callable[[list[MoveResult]], None],
        running_message: str,
        failure_message: str,
    ) -> None:
        self.set_busy(True, running_message)

        def worker() -> None:
            try:
                results = task()
            except Exception as error:
                self.after(0, lambda caught_error=error: self.finish_with_error(caught_error, failure_message))
            else:
                self.after(0, lambda: self.finish_successfully(results, on_success))

        threading.Thread(target=worker, daemon=True).start()

    def finish_successfully(
        self,
        results: list[MoveResult],
        on_success: Callable[[list[MoveResult]], None],
    ) -> None:
        self.set_busy(False)
        on_success(results)

    def finish_with_error(self, error: Exception, status_message: str) -> None:
        self.set_busy(False)
        messagebox.showerror("File Organizer", str(error))
        self.status_var.set(status_message)

    def set_busy(self, is_busy: bool, message: str | None = None) -> None:
        state = tk.DISABLED if is_busy else tk.NORMAL
        for button in self.action_buttons:
            button.configure(state=state)

        # Ensure Undo button respects can_undo state when returning to unbusy
        if not is_busy:
            self.refresh_undo_button_state()

        if is_busy:
            self.progress.grid(row=5, column=0, sticky="ew", padx=18, pady=(4, 0))
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.grid_remove()

        if message:
            self.status_var.set(message)

    def format_destination(self, result: MoveResult) -> str:
        parts = result.destination.parts
        if len(parts) >= 3:
            return "/".join(parts[-3:])
        return result.destination.name

    def save_current_settings(self) -> None:
        save_settings(
            {
                "last_directory": self.directory_var.get().strip(),
                "output_folder": self.output_folder_var.get().strip() or "Organized_Files",
                "recursive": self.recursive_var.get(),
                "detect_duplicates": self.detect_duplicates_var.get(),
                "custom_categories": self.custom_categories,
            }
        )


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()
