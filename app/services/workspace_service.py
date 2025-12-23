from typing import List, Optional
from pathlib import Path
from datetime import datetime
import os

from app.config import settings
from app.models.schemas import WorkspaceFile


class WorkspaceService:
    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = Path(workspace_path or settings.workspace_path).resolve()
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, path: str) -> Path:
        resolved = (self.workspace_path / path).resolve()
        if not str(resolved).startswith(str(self.workspace_path)):
            raise ValueError(f"Path '{path}' is outside workspace")
        return resolved
    
    def _path_to_file(self, path: Path, include_children: bool = False) -> WorkspaceFile:
        stat = path.stat()
        
        file = WorkspaceFile(
            path=str(path.relative_to(self.workspace_path)),
            name=path.name,
            is_directory=path.is_dir(),
            size=stat.st_size if path.is_file() else None,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )
        
        if include_children and path.is_dir():
            file.children = [
                self._path_to_file(child, include_children=False)
                for child in sorted(path.iterdir())
                if not child.name.startswith(".")
            ]
        
        return file
    
    def get_file_tree(
        self, 
        path: str = ".",
        max_depth: int = 3,
        include_hidden: bool = False,
    ) -> WorkspaceFile:
        root_path = self._resolve_path(path)
        
        if not root_path.exists():
            raise ValueError(f"Path not found: {path}")
        
        return self._build_tree(root_path, max_depth, include_hidden, current_depth=0)
    
    def _build_tree(
        self, 
        path: Path, 
        max_depth: int,
        include_hidden: bool,
        current_depth: int,
    ) -> WorkspaceFile:
        stat = path.stat()
        
        file = WorkspaceFile(
            path=str(path.relative_to(self.workspace_path)) if path != self.workspace_path else ".",
            name=path.name or "workspace",
            is_directory=path.is_dir(),
            size=stat.st_size if path.is_file() else None,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )
        
        if path.is_dir() and current_depth < max_depth:
            children = []
            try:
                for child in sorted(path.iterdir()):
                    if not include_hidden and child.name.startswith("."):
                        continue
                    if child.name in ("node_modules", "__pycache__", ".git", "venv", ".venv"):
                        children.append(WorkspaceFile(
                            path=str(child.relative_to(self.workspace_path)),
                            name=child.name,
                            is_directory=True,
                            children=[]
                        ))
                    else:
                        children.append(
                            self._build_tree(child, max_depth, include_hidden, current_depth + 1)
                        )
            except PermissionError:
                pass
            
            file.children = children
        
        return file
    
    def list_files(
        self, 
        path: str = ".",
        recursive: bool = False,
        pattern: Optional[str] = None,
    ) -> List[WorkspaceFile]:
        dir_path = self._resolve_path(path)
        
        if not dir_path.exists():
            raise ValueError(f"Path not found: {path}")
        
        if not dir_path.is_dir():
            return [self._path_to_file(dir_path)]
        
        files = []
        
        if recursive:
            glob_pattern = pattern or "*"
            for item in dir_path.rglob(glob_pattern):
                if not any(part.startswith(".") for part in item.parts):
                    files.append(self._path_to_file(item))
        else:
            for item in dir_path.iterdir():
                if not item.name.startswith("."):
                    if pattern is None or item.match(pattern):
                        files.append(self._path_to_file(item))
        
        return sorted(files, key=lambda f: (not f.is_directory, f.name.lower()))
    
    def get_workspace_stats(self) -> dict:
        total_files = 0
        total_dirs = 0
        total_size = 0
        
        for item in self.workspace_path.rglob("*"):
            if any(part.startswith(".") for part in item.relative_to(self.workspace_path).parts):
                continue
            if item.name in ("node_modules", "__pycache__", "venv", ".venv"):
                continue
            
            if item.is_file():
                total_files += 1
                total_size += item.stat().st_size
            elif item.is_dir():
                total_dirs += 1
        
        return {
            "total_files": total_files,
            "total_directories": total_dirs,
            "total_size_bytes": total_size,
            "workspace_path": str(self.workspace_path),
        }
