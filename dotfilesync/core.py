import os
import json
import platform
import shutil
from pathlib import Path


# Lazy import to avoid circular
def _get_config():
    from .config import ConfigFile

    return ConfigFile()


class Database:
    def __init__(self) -> None:
        self.os = platform.system()

        if self.os == "Windows":
            self.db_path = Path.home() / "AppData" / "Local" / "DotfileSync" / "data"
        else:
            self.db_path = Path.home() / ".config" / "dotfilesync" / "data"

        self.db_file = self.db_path / "state.json"
        self.db_path.mkdir(parents=True, exist_ok=True)

        if not self.db_file.exists():
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"active_profile": "default", "profiles": [], "managed_files": []},
                    f,
                    indent=2,
                )

        self.data = self._load_data()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_data(self):
        try:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print("Database save failed:", e)

    def _load_data(self):
        """Load state from disk.  Returns a safe default on any error."""
        default = {"active_profile": "default", "profiles": [], "managed_files": []}
        try:
            if self.db_file.exists():
                with open(self.db_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Ensure required keys exist (forward-compat)
                for key, val in default.items():
                    data.setdefault(key, val)
                return data
        except Exception as e:
            print("Data load failed:", e)
        return default

    def reload(self):
        """Re-read from disk and refresh self.data in-place."""
        self.data = self._load_data()

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------

    def add_profile(self, name: str, path: Path):
        """Add a new named profile."""
        if self.profile_is_exists(name):
            return False
        profile = {
            "profile_name": name,
            "profile_path": str(path),
        }
        self.data.setdefault("profiles", []).append(profile)
        self._save_data()
        return True

    def profile_is_exists(self, name: str) -> bool:
        for p in self.data.get("profiles", []):
            if p["profile_name"].strip().lower() == name.strip().lower():
                return True
        return False

    # Keep old typo as alias so existing callers don't break
    def profile_is_exsists(self, name: str) -> bool:
        return self.profile_is_exists(name)

    def set_active_profile(self, name: str):
        # Strip any leading emoji / whitespace that the UI row label may include
        clean = name.strip().lstrip("👉").strip()
        # Verify the profile actually exists before setting
        for p in self.data.get("profiles", []):
            if p["profile_name"] == clean:
                self.data["active_profile"] = clean
                self._save_data()
                return True
        print(f"set_active_profile: '{clean}' not found in profiles")
        return False

    def get_active_profile(self) -> dict | None:
        """Return the full profile dict for the currently active profile."""
        name = self.data.get("active_profile", "")
        for p in self.data.get("profiles", []):
            if p["profile_name"] == name:
                return p
        return None

    # ------------------------------------------------------------------
    # Managed files
    # ------------------------------------------------------------------

    def add_managed_file(self, id: str, alias: str, file_dir: Path, backup_dir: Path):
        """Add a tracked dotfile entry."""
        entry = {
            "id": id,
            "alias": alias,
            "real_path": str(file_dir),
            "backup_path": str(backup_dir),
        }
        self.data.setdefault("managed_files", []).append(entry)
        self._save_data()

    # Old typo kept as alias
    def add_manged_files(self, id: str, alias: str, file_dir: Path, backup_dir: Path):
        return self.add_managed_file(id, alias, file_dir, backup_dir)

    def remove_managed_file(self, alias: str):
        self.data["managed_files"] = [
            f for f in self.data.get("managed_files", []) if f.get("alias") != alias
        ]
        self._save_data()


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def backup_file(file_path: Path) -> Path | None:
    """Copy *file_path* to the configured backup directory.

    Fixed bug: original code produced double-dots in the suffix, e.g.
    ``name.backup0..txt`` because ``Path.suffix`` already includes the dot.
    """
    config = _get_config()
    backup_dir: Path = config.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)

    stem = file_path.stem  # e.g. ".bashrc" → ".bashrc" (no suffix)
    suffix = file_path.suffix  # e.g. ".txt"  (includes leading dot)

    i = 0
    while True:
        candidate = backup_dir / f"{stem}.backup{i}{suffix}"
        if not candidate.exists():
            break
        i += 1

    try:
        shutil.copy2(file_path, candidate)
        return candidate
    except Exception as e:
        print(f"backup_file failed: {e}")
        return None


def restore_backup_file(dest_path: Path, backup_path: Path) -> bool:
    """Restore *backup_path* → *dest_path*, creating parent dirs as needed."""
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, dest_path)
        return True
    except Exception as e:
        print(f"restore_backup_file failed: {e}")
        return False


# Old typo kept for backward compat
def restore_baclkup_file(dest_path: Path, backup_path: Path) -> bool:
    return restore_backup_file(dest_path, backup_path)

def backup_rewrite(og_path : Path, backup_path : Path):
    
    if og_path.exists() and backup_path.exists():
        shutil.copy2(og_path, backup_path)
        
     