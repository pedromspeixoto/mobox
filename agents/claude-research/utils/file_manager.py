"""Manage research artifacts and file operations."""

from pathlib import Path
from typing import Optional

# Directory structure for research artifacts
DIRS = {
    "research_notes": "files/research_notes",
    "data": "files/data",
    "charts": "files/charts",
    "reports": "files/reports",
}

OUTPUT_FORMAT_FILE = "files/output_format.txt"


def ensure_directories(workspace: str) -> None:
    """Create all required directories for research artifacts.

    Args:
        workspace: Base workspace directory
    """
    workspace_path = Path(workspace)

    # Create files directory
    files_dir = workspace_path / "files"
    files_dir.mkdir(exist_ok=True)

    # Create subdirectories
    for _, dir_path in DIRS.items():
        full_path = workspace_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)


def save_output_format(workspace: str, format_type: str) -> None:
    """Save the selected output format to a file.

    Args:
        workspace: Base workspace directory
        format_type: Output format ("none", "pdf", or "pptx")
    """
    workspace_path = Path(workspace)
    format_file = workspace_path / OUTPUT_FORMAT_FILE
    format_file.parent.mkdir(parents=True, exist_ok=True)
    format_file.write_text(format_type.lower().strip())


def get_output_format(workspace: str) -> Optional[str]:
    """Read the output format from file.

    Args:
        workspace: Base workspace directory

    Returns:
        The output format string, or None if not set
    """
    workspace_path = Path(workspace)
    format_file = workspace_path / OUTPUT_FORMAT_FILE

    if format_file.exists():
        content = format_file.read_text().strip()
        if content:
            return content
    return None


def has_research_notes(workspace: str) -> bool:
    """Check if research notes exist from a previous run.

    Args:
        workspace: Base workspace directory

    Returns:
        True if research notes exist
    """
    workspace_path = Path(workspace)
    notes_dir = workspace_path / DIRS["research_notes"]

    if not notes_dir.exists():
        return False

    # Check for any .md files
    return any(notes_dir.glob("*.md"))


def list_research_notes(workspace: str) -> list[str]:
    """List all research note files.

    Args:
        workspace: Base workspace directory

    Returns:
        List of absolute paths to research note files
    """
    workspace_path = Path(workspace)
    notes_dir = workspace_path / DIRS["research_notes"]

    if not notes_dir.exists():
        return []

    return sorted([str(f) for f in notes_dir.glob("*.md")])


def list_charts(workspace: str) -> list[str]:
    """List all chart files.

    Args:
        workspace: Base workspace directory

    Returns:
        List of absolute paths to chart files (PNG)
    """
    workspace_path = Path(workspace)
    charts_dir = workspace_path / DIRS["charts"]

    if not charts_dir.exists():
        return []

    return sorted([str(f) for f in charts_dir.glob("*.png")])


def save_research_note(workspace: str, filename: str, content: str) -> str:
    """Save a research note to the research_notes directory.

    Args:
        workspace: Base workspace directory
        filename: Name of the file (without path)
        content: Content to write

    Returns:
        Absolute path to the saved file
    """
    workspace_path = Path(workspace)
    notes_dir = workspace_path / DIRS["research_notes"]
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Ensure .md extension
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    file_path = notes_dir / filename
    file_path.write_text(content)
    return str(file_path)


def get_research_notes_content(workspace: str) -> dict[str, str]:
    """Read all research notes and return as a dictionary.

    Args:
        workspace: Base workspace directory

    Returns:
        Dictionary mapping filename to content
    """
    notes = {}
    for note_path in list_research_notes(workspace):
        path = Path(note_path)
        notes[path.name] = path.read_text()
    return notes


def get_data_summary(workspace: str) -> Optional[str]:
    """Read the data summary file if it exists.

    Args:
        workspace: Base workspace directory

    Returns:
        Content of data_summary.md or None
    """
    workspace_path = Path(workspace)
    summary_file = workspace_path / DIRS["data"] / "data_summary.md"

    if summary_file.exists():
        return summary_file.read_text()
    return None


def save_chart(workspace: str, filename: str, data: bytes) -> str:
    """Save a chart image to the charts directory.

    Args:
        workspace: Base workspace directory
        filename: Name of the file (without path)
        data: Binary image data

    Returns:
        Absolute path to the saved file
    """
    workspace_path = Path(workspace)
    charts_dir = workspace_path / DIRS["charts"]
    charts_dir.mkdir(parents=True, exist_ok=True)

    # Ensure .png extension
    if not filename.endswith(".png"):
        filename = f"{filename}.png"

    file_path = charts_dir / filename
    file_path.write_bytes(data)
    return str(file_path)


def save_report(workspace: str, filename: str, data: bytes | str) -> str:
    """Save a report to the reports directory.

    Args:
        workspace: Base workspace directory
        filename: Name of the file (without path)
        data: Report data (bytes for binary, str for text)

    Returns:
        Absolute path to the saved file
    """
    workspace_path = Path(workspace)
    reports_dir = workspace_path / DIRS["reports"]
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_path = reports_dir / filename

    if isinstance(data, bytes):
        file_path.write_bytes(data)
    else:
        file_path.write_text(data)

    return str(file_path)


def get_reports_dir(workspace: str) -> str:
    """Get the absolute path to the reports directory.

    Args:
        workspace: Base workspace directory

    Returns:
        Absolute path to reports directory
    """
    workspace_path = Path(workspace)
    return str(workspace_path / DIRS["reports"])


def get_charts_dir(workspace: str) -> str:
    """Get the absolute path to the charts directory.

    Args:
        workspace: Base workspace directory

    Returns:
        Absolute path to charts directory
    """
    workspace_path = Path(workspace)
    return str(workspace_path / DIRS["charts"])
