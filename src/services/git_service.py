"""Git service for managing workflow and app code."""

import subprocess
from pathlib import Path
from typing import Optional


class GitService:
    """Service for writing code to disk and committing to Git."""

    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def get_workspace_path(self, workspace_id: int) -> Path:
        """Get the workspace directory for a given workspace ID."""
        workspace_path = self.workspace_root / f"workspace_{workspace_id}"
        workspace_path.mkdir(parents=True, exist_ok=True)
        return workspace_path

    def write_workflow_code(self, workspace_id: int, workflow_slug: str, code: str) -> str:
        """Write workflow code to disk and return the module path."""
        workspace_path = self.get_workspace_path(workspace_id)
        workflows_dir = workspace_path / "workflows"
        workflows_dir.mkdir(exist_ok=True)

        # Create __init__.py if it doesn't exist
        init_file = workflows_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")

        # Write workflow module
        workflow_file = workflows_dir / f"{workflow_slug}.py"
        workflow_file.write_text(code)

        # Return relative module path
        return f"workspace.workspace_{workspace_id}.workflows.{workflow_slug}"

    def write_app_code(self, workspace_id: int, app_slug: str, code: str) -> str:
        """Write app code to disk and return the module path."""
        workspace_path = self.get_workspace_path(workspace_id)
        apps_dir = workspace_path / "apps"
        apps_dir.mkdir(exist_ok=True)

        # Create __init__.py if it doesn't exist
        init_file = apps_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")

        # Write app module
        app_file = apps_dir / f"{app_slug}.py"
        app_file.write_text(code)

        # Return relative module path
        return f"workspace.workspace_{workspace_id}.apps.{app_slug}"

    def commit_changes(self, workspace_id: int, message: str, author: Optional[str] = None) -> bool:
        """Commit changes to git (if initialized)."""
        workspace_path = self.get_workspace_path(workspace_id)

        # Check if git repo exists
        git_dir = workspace_path / ".git"
        if not git_dir.exists():
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=workspace_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "user.name", author or "Tapcraft Agent"],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "agent@tapcraft.local"],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )

        # Add all changes
        subprocess.run(["git", "add", "."], cwd=workspace_path, capture_output=True, check=True)

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=workspace_path,
            capture_output=True,
        )

        return result.returncode == 0

    def read_workflow_code(self, workspace_id: int, workflow_slug: str) -> Optional[str]:
        """Read workflow code from disk."""
        workspace_path = self.get_workspace_path(workspace_id)
        workflow_file = workspace_path / "workflows" / f"{workflow_slug}.py"

        if not workflow_file.exists():
            return None

        return workflow_file.read_text()

    def read_app_code(self, workspace_id: int, app_slug: str) -> Optional[str]:
        """Read app code from disk."""
        workspace_path = self.get_workspace_path(workspace_id)
        app_file = workspace_path / "apps" / f"{app_slug}.py"

        if not app_file.exists():
            return None

        return app_file.read_text()
