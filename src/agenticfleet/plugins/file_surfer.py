"""FileSurfer plugin for file system operations."""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import magic
except ImportError:
    import mimetypes as magic

    def from_file(path, mime=True):
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    magic.from_file = from_file

from pydantic import BaseModel
from semantic_kernel.functions import kernel_function


class FileInfo(BaseModel):
    """Model for file information."""

    name: str
    path: Path
    size: int
    content_type: str
    last_modified: str


class FileSurferPlugin:
    """Plugin for file system operations."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialize the FileSurfer plugin.

        Args:
            base_path: Optional base path to restrict file operations
        """
        self.base_path = base_path or Path.cwd()
        # Initialize mimetypes database
        mimetypes.init()

    def _get_file_info(self, file_path: Path) -> FileInfo:
        """Get information about a file.

        Args:
            file_path: Path to the file

        Returns:
            FileInfo object with file details
        """
        # Get basic file information
        stat = file_path.stat()

        # Detect content type using python-magic
        try:
            content_type = magic.from_file(str(file_path), mime=True)
        except (ImportError, IOError, OSError):
            # Fallback to mimetypes if magic fails
            content_type = (
                mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            )

        # Format last modified time
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

        return FileInfo(
            name=file_path.name,
            path=file_path,
            size=stat.st_size,
            content_type=content_type,
            last_modified=last_modified,
        )

    @kernel_function(
        name="list_files", description="Lists files in a directory matching a pattern"
    )
    def list_files(self, pattern: str = "*", recursive: bool = False) -> List[FileInfo]:
        """List files in the base directory matching the pattern.

        Args:
            pattern: Glob pattern to match files (default: "*")
            recursive: Whether to search recursively (default: False)

        Returns:
            List of FileInfo objects
        """
        try:
            # Use rglob for recursive search, glob for non-recursive
            glob_func = self.base_path.rglob if recursive else self.base_path.glob

            # Get all files matching the pattern
            files = [self._get_file_info(f) for f in glob_func(pattern) if f.is_file()]

            return sorted(files, key=lambda x: x.name)

        except (OSError, IOError) as e:
            print(f"Error listing files: {e}")
            return []

    @kernel_function(
        name="read_file", description="Reads and returns the content of a file"
    )
    def read_file(self, file_path: str) -> str:
        """Read the content of a file.

        Args:
            file_path: Path to the file to read

        Returns:
            Content of the file as a string
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.base_path / path

            # Verify the file is within base_path
            if not str(path.resolve()).startswith(str(self.base_path.resolve())):
                raise ValueError("Access denied: File is outside base directory")

            # Read and return file content with explicit encoding
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        except (OSError, IOError, ValueError) as e:
            return f"Error reading file: {e}"

    @kernel_function(
        name="search_files", description="Searches for files containing specific text"
    )
    def search_files(self, text: str, file_pattern: str = "*") -> List[FileInfo]:
        """Search for files containing specific text.

        Args:
            text: Text to search for
            file_pattern: Glob pattern to match files (default: "*")

        Returns:
            List of FileInfo objects for files containing the text
        """
        try:
            matching_files = []

            # Get all files matching the pattern
            for file_path in self.base_path.rglob(file_pattern):
                if not file_path.is_file():
                    continue

                try:
                    # Try to read the file as text with explicit encoding
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if text.lower() in content.lower():
                        matching_files.append(self._get_file_info(file_path))
                except (OSError, IOError, UnicodeDecodeError):
                    # Skip files that can't be read as text
                    continue

            return sorted(matching_files, key=lambda x: x.name)

        except (OSError, IOError) as e:
            print(f"Error searching files: {e}")
            return []
