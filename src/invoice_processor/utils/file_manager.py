#!/usr/bin/env python3
"""File management for invoice processing - scanning and moving files."""

import os
import shutil
from typing import List
from pathlib import Path


class FileManager:
    """Manages invoice file operations."""

    def __init__(self, pending_folder: str = "invoices/pending",
                 processed_folder: str = "invoices/processed"):
        """
        Initialize file manager with folder paths.

        Args:
            pending_folder: Path to folder containing unprocessed invoices
            processed_folder: Path to folder for processed invoices
        """
        self.pending_folder = Path(pending_folder)
        self.processed_folder = Path(processed_folder)

        # Create folders if they don't exist
        self.pending_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)

        # Track files we've already seen
        self.known_files = set()

    def scan_folder(self, initial_scan: bool = False) -> List[str]:
        """
        Scan the pending folder for PDF files.

        Args:
            initial_scan: If True, return all PDFs. If False, only return new ones.

        Returns:
            List of PDF filenames (not full paths)
        """
        try:
            if not self.pending_folder.exists():
                return []

            # Get all PDF files
            all_pdfs = []
            for file in self.pending_folder.iterdir():
                if file.is_file() and file.suffix.lower() == '.pdf':
                    all_pdfs.append(file.name)

            if initial_scan:
                # First scan - return everything and mark as known
                self.known_files.update(all_pdfs)
                return sorted(all_pdfs)
            else:
                # Subsequent scan - only return new files
                new_files = [f for f in all_pdfs if f not in self.known_files]
                self.known_files.update(new_files)
                return sorted(new_files)

        except PermissionError as e:
            print(f"Permission error scanning folder: {e}")
            return []
        except Exception as e:
            print(f"Error scanning folder: {e}")
            return []

    def get_full_path(self, filename: str, folder: str = "pending") -> Path:
        """
        Get full path for a filename.

        Args:
            filename: The filename
            folder: Either 'pending' or 'processed'

        Returns:
            Full path to the file
        """
        if folder == "pending":
            return self.pending_folder / filename
        else:
            return self.processed_folder / filename

    def move_invoice(self, filename: str) -> bool:
        """
        Move an invoice from pending to processed folder.

        Args:
            filename: Name of the file to move

        Returns:
            True if successful, False otherwise
        """
        try:
            source = self.pending_folder / filename
            destination = self.processed_folder / filename

            if not source.exists():
                print(f"Source file not found: {source}")
                return False

            # Handle duplicate filenames in destination
            if destination.exists():
                # Add a number to make it unique
                base = destination.stem
                ext = destination.suffix
                counter = 1
                while destination.exists():
                    destination = self.processed_folder / f"{base}_{counter}{ext}"
                    counter += 1

            # Move the file
            shutil.move(str(source), str(destination))

            # Remove from known files since it's no longer in pending
            if filename in self.known_files:
                self.known_files.remove(filename)

            return True

        except PermissionError as e:
            print(f"Permission error moving file: {e}")
            return False
        except Exception as e:
            print(f"Error moving file {filename}: {e}")
            return False

    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in the pending folder.

        Args:
            filename: Name of the file

        Returns:
            True if file exists, False otherwise
        """
        return (self.pending_folder / filename).exists()


if __name__ == "__main__":
    # Test the file manager
    import tempfile
    import sys

    # Create temporary test directories
    with tempfile.TemporaryDirectory() as tmpdir:
        pending = os.path.join(tmpdir, "pending")
        processed = os.path.join(tmpdir, "processed")

        print("Testing FileManager...")
        print(f"Temp pending: {pending}")
        print(f"Temp processed: {processed}")

        # Initialize manager
        fm = FileManager(pending, processed)
        print("✓ FileManager initialized, folders created")

        # Create test files
        test_file1 = os.path.join(pending, "test1.pdf")
        test_file2 = os.path.join(pending, "test2.pdf")
        test_txt = os.path.join(pending, "test.txt")

        with open(test_file1, 'w') as f:
            f.write("test pdf 1")
        with open(test_file2, 'w') as f:
            f.write("test pdf 2")
        with open(test_txt, 'w') as f:
            f.write("not a pdf")

        print("✓ Created test files")

        # Test initial scan
        files = fm.scan_folder(initial_scan=True)
        assert len(files) == 2, f"Expected 2 PDFs, got {len(files)}"
        assert "test1.pdf" in files
        assert "test2.pdf" in files
        assert "test.txt" not in files
        print(f"✓ Initial scan found: {files}")

        # Test new file detection
        test_file3 = os.path.join(pending, "test3.pdf")
        with open(test_file3, 'w') as f:
            f.write("test pdf 3")

        new_files = fm.scan_folder(initial_scan=False)
        assert len(new_files) == 1, f"Expected 1 new file, got {len(new_files)}"
        assert "test3.pdf" in new_files
        print(f"✓ New file detection works: {new_files}")

        # Test file movement
        success = fm.move_invoice("test1.pdf")
        assert success, "File move failed"
        assert os.path.exists(os.path.join(processed, "test1.pdf"))
        assert not os.path.exists(test_file1)
        print("✓ File moved successfully")

        # Test file existence check
        assert fm.file_exists("test2.pdf")
        assert not fm.file_exists("test1.pdf")
        print("✓ File existence check works")

        # Test moving non-existent file
        success = fm.move_invoice("nonexistent.pdf")
        assert not success, "Should fail for non-existent file"
        print("✓ Handles non-existent file correctly")

        print("\n✓✓✓ All FileManager tests passed! ✓✓✓")
