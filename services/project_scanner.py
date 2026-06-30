"""Project scanner for extracting project metadata."""

from pathlib import Path
from typing import Any


def scan_project(path: str) -> dict[str, Any]:
    """
    Recursively inspect a project folder and return structured metadata.
    
    Args:
        path: Path to the project directory
        
    Returns:
        Dictionary containing project metadata with keys:
        - project_name: Name of the project folder
        - language: Detected programming language
        - package_manager: Detected package manager
        - framework: Detected framework
        - entry_points: List of found entry point files
        - important_files: List of found important files
        - top_level_dirs: List of top-level directories
    """
    project_path = Path(path).resolve()
   
    if not project_path.exists() or not project_path.is_dir():
        return {
            "success": False,
            "error": f"Path does not exist or is not a directory: {path}",
            "project_name": None,
            "language": "Unknown",
            "package_manager": "Unknown",
            "framework": "Unknown",
            "entry_points": [],
            "important_files": [],
            "top_level_dirs": [],
        }
    
    return {
        "success": True,
        "project_name": project_path.name,
        "language": _detect_language(project_path),
        "package_manager": _detect_package_manager(project_path),
        "framework": _detect_framework(project_path),
        "entry_points": _find_entry_points(project_path),
        "important_files": _find_important_files(project_path),
         "top_level_dirs": _get_top_level_dirs(project_path),
    }


def _detect_language(project_path: Path) -> str:
    """Detect the primary programming language of the project."""
    extensions = {
        ".py": "Python",
        ".js": "JavaScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
    }
    
    counts = {ext: len(list(project_path.rglob(f"*{ext}"))) for ext in extensions}
    max_ext = max(counts, key=counts.get)
    
    return extensions[max_ext] if counts[max_ext] > 0 else "Unknown"


def _detect_package_manager(project_path: Path) -> str:
    """Detect the package manager used by the project."""
    indicators = {
        "pip": ["requirements.txt", "pyproject.toml", "setup.py"],
        "npm": ["package.json", "package-lock.json"],
        "yarn": ["yarn.lock"],
        "cargo": ["Cargo.toml"],
        "go": ["go.mod"],
        "maven": ["pom.xml"],
    }
    
    for manager, files in indicators.items():
        if any((project_path / f).exists() for f in files):
            return manager
    
    return "Unknown"


def _detect_framework(project_path: Path) -> str:
    """Detect the framework used by the project (best effort)."""
    indicators = {
        "PySide6": ["pyside6"],
        "Django": ["django"],
        "Flask": ["flask"],
        "FastAPI": ["fastapi"],
        "React": ["react"],
        "Vue": ["vue"],
        "Angular": ["angular"],
        "Express": ["express"],
        "Spring": ["spring"],
    }
    
    for config_file in ["requirements.txt", "package.json", "pom.xml"]:
        config_path = project_path / config_file
        if config_path.exists():
            try:
                content = config_path.read_text(errors="ignore")
                for framework, keywords in indicators.items():
                    if any(kw in content.lower() for kw in keywords):
                        return framework
            except Exception:
                pass
    
    return "Unknown"


def _find_entry_points(project_path: Path) -> list[str]:
    """Find common entry point files."""
    entry_point_names = ["app.py", "main.py", "server.py", "run.py"]
    return [name for name in entry_point_names if (project_path / name).exists()]


def _find_important_files(project_path: Path) -> list[str]:
    """Find important project files."""
    important_names = [
        "README.md",
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "Dockerfile",
        ".env",
        "setup.py",
    ]
    return [name for name in important_names if (project_path / name).exists()]


def _get_top_level_dirs(project_path: Path) -> list[str]:
    """Get top-level directories, excluding common non-essential ones."""
    exclude = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache", "dist", "build"}
    
    dirs = [
        item.name
        for item in project_path.iterdir()
        if item.is_dir() and item.name not in exclude and not item.name.startswith(".")
    ]
    
    return sorted(dirs)

def format_project_metadata(metadata: dict) -> str:
    """Format project metadata into a readable text block for the AI."""

    lines = [
        f"Project Name: {metadata.get('project_name', 'Unknown')}",
        f"Language: {metadata.get('language', 'Unknown')}",
        f"Framework: {metadata.get('framework', 'Unknown')}",
        f"Package Manager: {metadata.get('package_manager', 'Unknown')}",
        "",
        "Entry Points:",
    ]

    for item in metadata.get("entry_points", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Important Files:")

    for item in metadata.get("important_files", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Top Level Directories:")

    for item in metadata.get("top_level_dirs", []):
        lines.append(f"- {item}")

    return "\n".join(lines)


def get_project_context(path: str) -> dict[str, Any]:
    """
    Get comprehensive project context including metadata and key files.
    
    Args:
        path: Path to the project directory
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if operation succeeded
        - metadata: Project metadata from scan_project()
        - readme: Contents of README.md if it exists, empty string otherwise
        - requirements: Contents of requirements.txt if it exists, empty string otherwise
        - error: Error message if success is False (empty string otherwise)
    """
    metadata = scan_project(path)
    
    if not metadata.get("success", False):
        return {
            "success": False,
            "error": metadata.get("error", "Failed to scan project"),
            "metadata": {},
            "readme": "",
            "requirements": "",
        }
    
    project_path = Path(path).resolve()
    
    readme_content = _read_file_safe(project_path / "README.md")
    requirements_content = _read_file_safe(project_path / "requirements.txt")
    
    return {
        "success": True,
        "error": "",
        "metadata": metadata,
        "readme": readme_content,
        "requirements": requirements_content,
    }


def _read_file_safe(file_path: Path) -> str:
    """
    Read file content safely.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File contents as string, empty string if file doesn't exist or read fails
    """
    if not file_path.exists():
        return ""
    
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return ""