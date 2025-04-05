"""Tests for the FileSurfer plugin."""

import os
from datetime import datetime, timezone
from pathlib import Path
import pytest
from unittest.mock import patch

from agentic_kernel.plugins.file_surfer import FileSurferPlugin, FileInfo

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with some test files."""
    # Create test files
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Create a binary file
    binary_file = tmp_path / "test.bin"
    binary_file.write_bytes(b'\x00\x01\x02\x03')
    
    # Create subdirectory with files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    subdir_file = subdir / "subfile.txt"
    subdir_file.write_text("Subdir test content")
    
    # Create a file with search content
    search_file = tmp_path / "search.txt"
    search_file.write_text("This file contains searchable content")
    
    return tmp_path

@pytest.fixture
def file_surfer(temp_dir):
    """Create a FileSurfer plugin instance for testing."""
    return FileSurferPlugin(base_path=temp_dir)

def test_list_files_basic(file_surfer, temp_dir):
    """Test basic file listing functionality."""
    files = file_surfer.list_files()
    assert isinstance(files, list)
    assert len(files) == 3  # test.txt, test.bin, search.txt
    
    # Check first file details
    file = next(f for f in files if f.name == "test.txt")
    assert isinstance(file, FileInfo)
    assert file.name == "test.txt"
    assert isinstance(file.path, Path)
    assert file.size > 0
    assert "text/plain" in file.content_type.lower()
    # Check last_modified is a valid ISO format date
    datetime.fromisoformat(file.last_modified)

def test_list_files_pattern(file_surfer):
    """Test file listing with pattern matching."""
    files = file_surfer.list_files(pattern="*.txt")
    assert len(files) == 2  # test.txt and search.txt
    assert all(f.name.endswith(".txt") for f in files)

def test_list_files_recursive(file_surfer):
    """Test recursive file listing."""
    files = file_surfer.list_files(recursive=True)
    assert len(files) == 4  # All files including subdir
    subdir_files = [f for f in files if "subdir" in str(f.path)]
    assert len(subdir_files) == 1
    assert subdir_files[0].name == "subfile.txt"

def test_read_file(file_surfer, temp_dir):
    """Test file reading functionality."""
    content = file_surfer.read_file("test.txt")
    assert content == "Test content"

def test_read_file_subdir(file_surfer):
    """Test reading file from subdirectory."""
    content = file_surfer.read_file("subdir/subfile.txt")
    assert content == "Subdir test content"

def test_read_file_outside_base(file_surfer, tmp_path):
    """Test attempting to read file outside base directory."""
    outside_file = tmp_path.parent / "outside.txt"
    result = file_surfer.read_file(str(outside_file))
    assert "Error" in result
    assert "outside base directory" in result

def test_read_file_nonexistent(file_surfer):
    """Test reading nonexistent file."""
    result = file_surfer.read_file("nonexistent.txt")
    assert "Error" in result

def test_search_files(file_surfer):
    """Test file content searching."""
    files = file_surfer.search_files("searchable")
    assert len(files) == 1
    assert files[0].name == "search.txt"

def test_search_files_case_insensitive(file_surfer):
    """Test case-insensitive file content searching."""
    files = file_surfer.search_files("SEARCHABLE")
    assert len(files) == 1
    assert files[0].name == "search.txt"

def test_search_files_pattern(file_surfer):
    """Test file searching with pattern."""
    files = file_surfer.search_files("test", file_pattern="*.txt")
    assert len(files) == 2  # test.txt and subfile.txt
    assert all(f.name.endswith(".txt") for f in files)

def test_search_files_binary(file_surfer):
    """Test searching binary files is handled gracefully."""
    # Search should skip binary files without error
    files = file_surfer.search_files("test")
    assert all(f.name != "test.bin" for f in files)

def test_file_surfer_default_path():
    """Test FileSurfer initialization with default path."""
    with patch('pathlib.Path.cwd') as mock_cwd:
        mock_cwd.return_value = Path("/test/path")
        plugin = FileSurferPlugin()
        assert plugin.base_path == Path("/test/path")

def test_file_surfer_custom_path(temp_dir):
    """Test FileSurfer initialization with custom path."""
    plugin = FileSurferPlugin(base_path=temp_dir)
    assert plugin.base_path == temp_dir 