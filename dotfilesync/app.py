import os
import shutil
import string
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, TextArea

from .core import Database, backup_file, restore_backup_file,backup_rewrite
from .config import ConfigFile
from pyfiglet import Figlet


# ---------------------------------------------------------------------------
# Helper: strip emoji row-label prefix so we get the bare profile name
# ---------------------------------------------------------------------------
def _strip_row_label(raw: str) -> str:
    return raw.strip().lstrip("👉").strip()


# ===========================================================================
# Main Application
# ===========================================================================


class DotfileSyncApp(App):
    CSS = """
    #baner { margin-left: 1; }

    DataTable { max-height: 40vh; height: 40vh; }

    #main { margin: 1; }

    #fileTable { margin-left: 1; }

    #table1, #table2 {
        display: block;
        content-align: center middle;
    }

    #tables {
        padding: 1;
        border: ascii;
        display: block;
    }

    #tables Button { margin: 1; }

    #sync {
        margin-top: 1;
        width: 100%;
        margin-left: 1;
    }

    #activeProfile { margin-left: 1; }
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config_data = config
        self._db = Database()
        # button_actions is one of: "Link" | "Unlink" | "Activate"
        self.button_actions = "Link"
        self.selected_profile_name: str = ""

    # ------------------------------------------------------------------
    # Properties — always read fresh data so UI stays in sync
    # ------------------------------------------------------------------

    @property
    def data(self):
        return self._db.data

    def _reload_db(self):
        self._db.reload()

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        f = Figlet(font="slant", width=100)
        banner = f.renderText("DOTFILE SYNC")
        with Container(id="main"):
            yield Label(banner, id="baner")
            with Vertical(id="main"):
                with Horizontal(id="tables"):
                    with Vertical(id="table1"):
                        yield DataTable(id="profileTable")
                        yield Button("Add Profile", id="addProfile")
                    with Vertical(id="table2"):
                        yield DataTable(id="fileTable")
                        yield Button("Manage Files", id="manageFiles")
            yield Label("ACTIVE PROFILE : ", id="activeProfile")
            yield Button("Link Profile", id="sync")

    # ------------------------------------------------------------------
    # Mount — populate tables and restore correct button state
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._reload_db()
        self._build_profile_table()
        self._build_file_table()
        self._refresh_active_label()
        self._sync_link_state()

    # ------------------------------------------------------------------
    # Table builders
    # ------------------------------------------------------------------

    def _build_profile_table(self):
        table = self.query_one("#profileTable", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_column("Profiles", width=60)
        table.add_column("", width=1)

        profiles = self.data.get("profiles", [])
        if not profiles:
            table.add_row("No profiles", "")
        else:
            active = self.data.get("active_profile", "")
            for p in profiles:
                name = p["profile_name"]
                label = f"👉 {name}" if name == active else name
                table.add_row(label, "")

    def _build_file_table(self):
        table = self.query_one("#fileTable", DataTable)
        table.clear(columns=True)
        table.cursor_type = "none"
        table.add_column("Alias", width=30)
        table.add_column("Real Path", width=40)

        files = self.data.get("managed_files", [])
        if not files:
            table.add_row("no managed files", "")
        else:
            for f in files:
                table.add_row(f.get("alias", ""), f.get("real_path", ""))

    def _refresh_active_label(self):
        self.query_one("#activeProfile", Label).update(
            f"ACTIVE PROFILE : {self.data.get('active_profile', '')}"
        )

    # ------------------------------------------------------------------
    # Determine whether files are already symlinked and set UI accordingly
    # ------------------------------------------------------------------

    def _any_symlinked(self) -> bool:
        for mf in self.data.get("managed_files", []):
            p = Path(mf.get("real_path", ""))
            if p.is_symlink():
                return True
        return False

    def _sync_link_state(self):
        """Lock/unlock UI controls based on whether files are currently linked."""
        linked = self._any_symlinked()
        profile_table = self.query_one("#profileTable", DataTable)
        add_p_btn = self.query_one("#addProfile", Button)
        mf_btn = self.query_one("#manageFiles", Button)

        if linked:
            self._set_action_btn("Unlink")
            profile_table.cursor_type = "none"
            profile_table.zebra_stripes = True
            add_p_btn.disabled = True
            mf_btn.disabled = True
        else:
            self._set_action_btn("Link")
            profile_table.cursor_type = "row"
            profile_table.zebra_stripes = False
            add_p_btn.disabled = False
            mf_btn.disabled = False

    # ------------------------------------------------------------------
    # Button handler
    # ------------------------------------------------------------------

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "manageFiles":

            def on_close(res):
                if res:
                    self._reload_db()
                    self._build_file_table()

            self.app.push_screen(FileManager(self.config_data), callback=on_close)

        elif btn_id == "addProfile":

            def on_close(res):
                if res:
                    self._reload_db()
                    self._build_profile_table()
                    self._refresh_active_label()

            self.app.push_screen(AddProfile(), callback=on_close)

        elif btn_id == "sync":
            if self.button_actions == "Link":
                ok, err = self._link()
                if err:
                    self.notify(f"Link error: {err}", severity="error", timeout=8)
                else:
                    self.notify("✅ Profile linked!", timeout=3)
                    self._sync_link_state()

            elif self.button_actions == "Unlink":
                ok, err = self._unlink()
                if err:
                    self.notify(f"Unlink error: {err}", severity="error", timeout=8)
                else:
                    self.notify("✅ Profile unlinked!", timeout=3)
                    self._sync_link_state()

            elif self.button_actions == "Activate":
                clean_name = _strip_row_label(self.selected_profile_name)
                if self._db.set_active_profile(clean_name):
                    self._reload_db()
                    self._build_profile_table()
                    self._refresh_active_label()
                    self._set_action_btn("Link")
                    self.notify(f"✅ Active profile → {clean_name}", timeout=3)
                else:
                    self.notify(f"Profile '{clean_name}' not found!", severity="error")

    # ------------------------------------------------------------------
    # Row selection
    # ------------------------------------------------------------------

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.cursor_row is None:
            return
        table = event.data_table
        if table.id not in ("profileTable"):
            return
        row = table.get_row_at(event.cursor_row)
        if not row:
            return
        self.selected_profile_name = str(row[0])

        if self.button_actions != "Unlink":
            self.button_actions = "Activate"
            clean = _strip_row_label(self.selected_profile_name)
            self.query_one("#sync", Button).label = f"Activate Profile : {clean}"

    # ------------------------------------------------------------------
    # Link / Unlink logic
    # ------------------------------------------------------------------

    def _get_active_profile_dir(self) -> Path | None:
        active = self.data.get("active_profile")
        for p in self.data.get("profiles", []):
            if p["profile_name"] == active:
                return Path(p["profile_path"])
        return None

    def _link(self) -> tuple[bool, str | None]:
        """
        Replace each managed file's real path with a symlink pointing into
        the active profile directory.
        """
        profile_dir = self._get_active_profile_dir()
        if profile_dir is None:
            return False, "No active profile set."
        if not profile_dir.exists():
            return False, f"Profile directory not found: {profile_dir}"

        errors = []
        for mf in self.data.get("managed_files", []):
            real_path = Path(mf["real_path"])
            alias = mf["alias"]
            profile_file = profile_dir / alias

            if not profile_file.exists():
                errors.append(f"Profile file missing: {profile_file}")
                continue

            # Remove original file (it's already backed up)
            try:
                if real_path.exists() and not real_path.is_symlink():
                    backup_rewrite(real_path, Path(mf["backup_path"]))
                    real_path.unlink()

                elif real_path.is_symlink():
                    real_path.unlink()  # remove stale symlink
            except Exception as e:
                errors.append(f"Could not remove {real_path}: {e}")
                continue

            try:
                real_path.symlink_to(profile_file)
            except Exception as e:
                errors.append(f"Symlink failed {real_path} → {profile_file}: {e}")

        if errors:
            return False, "\n".join(errors)
        return True, None

    def _unlink(self) -> tuple[bool, str | None]:
        """
        Remove symlinks and restore original files from backups.
        """
        errors = []
        for mf in self.data.get("managed_files", []):
            real_path = Path(mf["real_path"])
            backup_path = Path(mf.get("backup_path", ""))

            # Remove symlink
            try:
                if real_path.is_symlink() or real_path.exists():
                    real_path.unlink()
            except Exception as e:
                errors.append(f"Could not remove symlink {real_path}: {e}")
                continue

            # Restore from backup
            if not backup_path.exists():
                errors.append(f"Backup not found: {backup_path}")
                continue

            ok = restore_backup_file(real_path, backup_path)
            if not ok:
                errors.append(f"Restore failed: {backup_path} → {real_path}")

        if errors:
            return False, "\n".join(errors)
        return True, None

    # ------------------------------------------------------------------
    # Action button helper
    # ------------------------------------------------------------------

    def _set_action_btn(self, action: str):
        btn = self.query_one("#sync", Button)
        if action == "Link":
            btn.label = "Link Profile"
            self.button_actions = "Link"
        elif action == "Unlink":
            btn.label = "Unlink Profile"
            self.button_actions = "Unlink"
        elif action == "Activate":
            btn.label = "Activate Profile"
            self.button_actions = "Activate"


# ===========================================================================
# File Manager Modal
# ===========================================================================


class FileManager(ModalScreen):
    CSS = """
    FileManager { align: center middle; }

    #modal-container {
        width: 90;
        height: auto;
        max-height: 80vh;
        border: ascii green;
        background: $surface;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        padding: 1 0;
    }

    #table-container {
        width: 100%;
        height: 30vh;
        margin: 1 0;
        border: ascii $primary;
    }

    #file-table { width: 100%; height: 100%; }

    DataTable { border: none; padding: 0 1; }

    #file-content {
        width: 100%;
        height: 30vh;
        margin: 1 0;
        border: ascii $secondary;
    }

    TextArea { width: 100%; height: 100%; }

    #button-row {
        align: center middle;
        margin: 1 0 0 0;
        padding: 1 0;
        height: 10vh;
    }

    Button { margin: 0 2; min-width: 15; }
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config_data = config
        self._db = Database()
        # Guard attributes so we never access them uninitialized
        self._selected_file_path: Path | None = None
        self._editor_content: str = ""

    @property
    def data(self):
        return self._db.data

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="modal-container"):
            yield Label(
                f"📁 MANAGED FILES : {self.data.get('active_profile', 'default')}",
                id="title",
            )
            with Container(id="table-container"):
                table = DataTable(id="file-table")
                table.cursor_type = "row"
                table.zebra_stripes = True
                table.add_columns("Status", "Alias", "Real Path", "ID")
                self._populate_table(table)
                yield table

            yield Label("📄 Edit File")
            with Container(id="file-content"):
                yield TextArea(language="text", id="file-editor")

            with Horizontal(id="button-row"):
                yield Button("❌ Close", id="close", variant="error")
                yield Button("💾 Save", id="save", variant="primary")
                yield Button("➕ Add File", id="add_file", variant="success")

    def _populate_table(self, table: DataTable):
        table.clear()
        for f in self.data.get("managed_files", []):
            status = "🟢" if Path(f.get("real_path", "")).exists() else "🔴"
            table.add_row(
                status,
                f.get("alias", "N/A"),
                f.get("real_path", "N/A"),
                f.get("id", "N/A"),
            )

    def _get_profile_dir(self) -> Path | None:
        active = self.data.get("active_profile")
        for p in self.data.get("profiles", []):
            if p["profile_name"] == active:
                return Path(p["profile_path"])
        return None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        if event.cursor_row is None:
            return

        table = self.query_one("#file-table", DataTable)
        row = table.get_row_at(event.cursor_row)
        if not row:
            return

        alias = row[1]
        profile_dir = self._get_profile_dir()
        if profile_dir is None:
            self.notify("No active profile found.", severity="error")
            return

        file_path = profile_dir / alias
        self._selected_file_path = file_path
        content = self._read_file(file_path)
        self.query_one("#file-editor", TextArea).load_text(content)

    def _read_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"# Could not read file: {e}"

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._editor_content = event.text_area.text

    def _save_file(self):
        if self._selected_file_path is None:
            self.notify("No file selected.", severity="warning")
            return
        try:
            self._selected_file_path.write_text(self._editor_content, encoding="utf-8")
            self.notify("💾 Saved!", timeout=2)
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save_file()
        elif event.button.id == "close":
            self.dismiss(True)
        elif event.button.id == "add_file":

            def on_close(res):
                if res:
                    self._db.reload()
                    self._populate_table(self.query_one("#file-table", DataTable))
                    self.dismiss(True)

            self.app.push_screen(
                AddFileBrowser(start_path=Path("/")), callback=on_close
            )


# ===========================================================================
# File Browser Modal
# ===========================================================================


class AddFileBrowser(ModalScreen):
    CSS = """
    AddFileBrowser { align: center middle; }

    #browser-container {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 85vh;
        min-height: 25;
        border: thick green;
        background: $surface;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin: 0 0 1 0;
    }

    #mode-label {
        text-align: center;
        color: $success;
        text-style: italic;
        width: 100%;
        margin: 0 0 1 0;
    }

    #path-bar {
        width: 100%;
        height: 2;
        margin: 1 0;
        padding: 0 1;
        background: $primary;
        color: $text;
    }

    #file-list-section {
        width: 100%;
        height: 12;
        min-height: 8;
        margin: 1 0;
        border: solid $primary;
    }

    #file-table { width: 100%; height: 100%; }

    DataTable { border: none; padding: 0 1; }

    #preview-section {
        width: 100%;
        height: 4;
        min-height: 3;
        margin: 1 0;
        border: solid $secondary;
        padding: 0 1;
    }

    #preview-label { width: 100%; color: $text-muted; }

    #stats-bar {
        width: 100%;
        height: 2;
        text-align: center;
        color: $text-muted;
        margin: 1 0;
        border-top: solid green;
    }

    #button-row {
        align: center middle;
        width: 100%;
        height: 3;
        margin: 1 0 0 0;
        border-top: double green;
    }

    Button { margin: 0 2; min-width: 12; }
    """

    def __init__(self, start_path: str = None, **kwargs):
        super().__init__(**kwargs)
        self.current_path: Path | None = (
            Path(start_path).expanduser() if start_path else None
        )
        self.selected_file: Path | None = None
        self.show_hidden = False
        self.browsing_drives = True
        self._db = Database()

    @property
    def data(self):
        return self._db.data

    def compose(self) -> ComposeResult:
        with Container(id="browser-container"):
            yield Label("🖥️ SELECT DRIVE OR BROWSE FILES", id="title")
            yield Label("📀 Select a drive to browse", id="mode-label")
            yield Input(placeholder="Type path here...", id="path-input")
            yield Label("📍 Select a drive below", id="path-bar")

            with ScrollableContainer(id="file-list-section"):
                table = DataTable(id="file-table")
                table.cursor_type = "row"
                table.zebra_stripes = True
                table.add_columns("Type", "Drive", "Free Space", "Label")
                yield table

            with Container(id="preview-section"):
                yield Label("💾 Select a drive to browse files", id="preview-label")

            yield Label("", id="stats-bar")

            with Horizontal(id="button-row"):
                back_btn = Button(
                    "⬆️ Back to Drives", id="back-drives", variant="default"
                )
                back_btn.display = False
                yield back_btn

                go_up_btn = Button("⬆️ Up One Level", id="go-up", variant="default")
                go_up_btn.display = False
                yield go_up_btn

                yield Button("🔄 Refresh", id="refresh", variant="warning")
                yield Button(
                    "➕ Add File", id="add-file", variant="success", disabled=True
                )
                yield Button("❌ Cancel", id="cancel", variant="error")

    def on_mount(self) -> None:
        self.browsing_drives = True
        self._populate_file_table()
        self.notify("🖥️ Select a drive | Enter to browse | Esc to close", timeout=3)

    # ------------------------------------------------------------------
    # Drive helpers
    # ------------------------------------------------------------------

    def _get_all_drives(self) -> list:
        drives = []
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        import ctypes

                        free_bytes = ctypes.c_ulonglong(0)
                        total_bytes = ctypes.c_ulonglong(0)
                        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                            ctypes.c_wchar_p(drive),
                            None,
                            ctypes.pointer(total_bytes),
                            ctypes.pointer(free_bytes),
                        )
                        drives.append(
                            {
                                "letter": drive,
                                "free": free_bytes.value,
                                "total": total_bytes.value,
                            }
                        )
                    except Exception:
                        drives.append({"letter": drive, "free": 0, "total": 0})
        else:
            # Linux/macOS: use / as the single "drive"
            drives.append({"letter": "/", "free": 0, "total": 0})
        return drives

    def _get_drive_label(self, drive: str) -> str:
        try:
            if os.name == "nt":
                import ctypes

                buf = ctypes.create_unicode_buffer(261)
                ctypes.windll.kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(drive), buf, 261, None, None, None, None, 0
                )
                return buf.value or "Local Disk"
        except Exception:
            pass
        return "/"

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_file_table(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.clear(columns=True)

        if self.browsing_drives:
            table.add_columns("Type", "Drive", "Free Space", "Label")
            drives = self._get_all_drives()
            for d in drives:
                table.add_row(
                    "💾",
                    d["letter"],
                    self._fmt_size(d["free"]),
                    self._get_drive_label(d["letter"]),
                    key=f"drive:{d['letter']}",
                )
            self._update_stats(len(drives), 0, mode="drives")
        else:
            table.add_columns("Type", "Name", "Size", "Modified")
            if not self.current_path:
                table.add_row("⚠️", "No path selected", "", "")
                return
            try:
                items = list(self.current_path.iterdir())
            except PermissionError:
                table.add_row("⚠️", "Permission Denied", "", "")
                return

            folders, files = [], []

            for item in items:
                # Skip hidden files/folders only if show_hidden is disabled
                if not self.show_hidden and item.name.startswith("."):
                    continue

                try:
                    if item.is_dir():
                        folders.append(item)

                    elif (
                        item.suffix in [
                            ".cfg",
                            ".conf",
                            ".ini",
                            ".toml",
                            ".yaml",
                            ".yml",
                            ".json",
                            ".txt",
                            ".md",
                        ]
                        or item.name.startswith(".")   # show dotfiles like .gitconfig
                        or item.suffix == ""           # show files without extension
                    ):
                        files.append(item)

                except Exception:
                    continue

            # Parent entry
            if (
                self.current_path != self.current_path.parent
                and len(self.current_path.parts) > 1
            ):
                table.add_row("📁", "..", "", "", key="parent")

            for folder in sorted(folders, key=lambda x: x.name.lower()):
                try:
                    table.add_row(
                        "📁",
                        folder.name,
                        "",
                        self._fmt_time(folder.stat().st_mtime),
                        key=str(folder),
                    )
                except Exception:
                    pass

            for file in sorted(files, key=lambda x: x.name.lower()):
                try:
                    table.add_row(
                        "📄",
                        file.name,
                        self._fmt_size(file.stat().st_size),
                        self._fmt_time(file.stat().st_mtime),
                        key=str(file),
                    )
                except Exception:
                    pass

            self._update_stats(len(folders), len(files), mode="files")

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_size(size: int) -> str:
        if size == 0:
            return "N/A"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @staticmethod
    def _fmt_time(ts: float) -> str:
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ""

    def _update_stats(self, folders: int, files: int, mode: str = "files") -> None:
        try:
            lbl = self.query_one("#stats-bar", Label)
            if mode == "drives":
                lbl.update(f"💾 Available Drives: {folders}")
            else:
                lbl.update(
                    f"📊 Folders: {folders} | Files: {files} | Total: {folders + files}"
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate_to(self, path: Path) -> None:
        if path.exists() and path.is_dir():
            self.current_path = path
            self.query_one("#path-bar", Label).update(f"📍 {path}")
            self.query_one("#path-input", Input).value = str(path)
            self._populate_file_table()
            self._clear_selection()

    def _clear_selection(self) -> None:
        self.selected_file = None
        lbl = self.query_one("#preview-label", Label)
        lbl.update(
            "💾 Select a drive to browse files"
            if self.browsing_drives
            else "👆 Select a file to preview"
        )
        self.query_one("#add-file", Button).disabled = True

    def _switch_to_drive_mode(self) -> None:
        self.browsing_drives = True
        self.current_path = None
        self._clear_selection()
        self.query_one("#title", Label).update("🖥️ SELECT DRIVE OR BROWSE FILES")
        self.query_one("#mode-label", Label).update("📀 Select a drive to browse")
        self.query_one("#path-bar", Label).update("📍 Select a drive below")
        self.query_one("#path-input", Input).value = ""
        self.query_one("#back-drives").display = False
        self.query_one("#go-up").display = False
        self._populate_file_table()
        self.notify("💾 Showing all drives", timeout=2)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "path-input":
            return
        path = Path(event.value).expanduser()
        if path.exists() and path.is_dir():
            self.browsing_drives = False
            self._navigate_to(path)
            self.query_one("#title", Label).update("📁 BROWSE FILES")
            self.query_one("#mode-label", Label).update(f"📍 {self.current_path}")
            self.query_one("#back-drives").display = True
            self.query_one("#go-up").display = True
        else:
            self.notify(f"⚠️ Invalid path: {event.value}", severity="error")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.cursor_row is None:
            return
        table = self.query_one("#file-table", DataTable)
        try:
            row = table.get_row_at(event.cursor_row)
            if not row:
                return

            if self.browsing_drives:
                self.query_one("#preview-label", Label).update(
                    f"💾 {row[1]} - {row[3]} | Free: {row[2]}"
                )
                self.selected_file = None
                self.query_one("#add-file", Button).disabled = True
            else:
                if row[1] == "..":
                    self.query_one("#preview-label", Label).update(
                        "📁 Go to parent directory"
                    )
                    self.selected_file = None
                    self.query_one("#add-file", Button).disabled = True
                else:
                    fp = self.current_path / row[1]
                    self.selected_file = fp
                    is_dir = fp.is_dir() if fp.exists() else False
                    self.query_one("#add-file", Button).disabled = is_dir
                    if fp.is_file():
                        self.query_one("#preview-label", Label).update(
                            f"📄 {row[1]} | {self._fmt_size(fp.stat().st_size)}"
                        )
                    else:
                        self.query_one("#preview-label", Label).update(
                            f"📁 Folder: {row[1]}"
                        )
        except Exception:
            self.query_one("#add-file", Button).disabled = True

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        if event.cursor_row is None:
            return
        table = self.query_one("#file-table", DataTable)
        try:
            row = table.get_row_at(event.cursor_row)
            if not row:
                return

            if self.browsing_drives:
                drive_path = Path(row[1])
                if drive_path.exists():
                    self.current_path = drive_path
                    self.browsing_drives = False
                    self.query_one("#title", Label).update("📁 BROWSE FILES")
                    self.query_one("#mode-label", Label).update(f"📍 {drive_path}")
                    self.query_one("#path-bar", Label).update(f"📍 {drive_path}")
                    self.query_one("#back-drives").display = True
                    self.query_one("#go-up").display = True
                    self._populate_file_table()
                    self.notify(f"💾 Opened {row[1]}", timeout=2)
            else:
                if row[1] == "..":
                    if len(self.current_path.parts) <= 1:
                        self._switch_to_drive_mode()
                    else:
                        self._navigate_to(self.current_path.parent)
                else:
                    fp = self.current_path / row[1]
                    if fp.is_dir():
                        self._navigate_to(fp)
                    else:
                        self.selected_file = fp
                        self.query_one("#add-file", Button).disabled = False
                        self.notify(f"📄 Selected: {row[1]}", timeout=2)
        except Exception as e:
            self.notify(f"⚠️ Error: {e}", severity="error", timeout=2)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "cancel":
            self.dismiss(None)
        elif btn_id == "refresh":
            self._populate_file_table()
            self.notify("🔄 Refreshed!", timeout=2)
        elif btn_id == "add-file":
            self._action_select_file()
        elif btn_id == "back-drives":
            self._switch_to_drive_mode()
        elif btn_id == "go-up":
            self._action_go_up()

    # ------------------------------------------------------------------
    # File add logic
    # ------------------------------------------------------------------

    def _action_select_file(self) -> None:
        if self.browsing_drives:
            self.notify(
                "⚠️ Select a drive first, then choose a file!",
                severity="warning",
                timeout=2,
            )
            return
        if not (self.selected_file and self.selected_file.is_file()):
            self.notify("⚠️ Please select a file first!", severity="warning", timeout=2)
            return

        source_file = self.selected_file
        stem = source_file.stem
        suffix = source_file.suffix
        alias = source_file.name

        profile_dirs = [Path(p["profile_path"]) for p in self.data.get("profiles", [])]

        # Make alias unique across all profile dirs
        i = 0
        while any((pd / alias).exists() for pd in profile_dirs):
            alias = f"{stem}_{i}{suffix}"
            i += 1

        file_id = (
            alias.replace(".", "_") if alias.startswith(".") else alias.split(".")[0]
        )

        # 1. Backup original
        backup_path = backup_file(source_file)
        if backup_path is None:
            self.notify("❌ Backup failed!", severity="error")
            return

        # 2. Copy into every profile dir
        errors = []
        for pd in profile_dirs:
            dest = pd / alias
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest)
            except Exception as e:
                errors.append(str(e))

        if errors:
            self.notify(f"Copy errors: {'; '.join(errors)}", severity="error")
            return

        # 3. Register in database
        self._db.add_managed_file(file_id, alias, source_file, backup_path)
        self.notify(f"✅ Added: {alias}", timeout=3)
        self.dismiss(True)

    def _action_go_up(self) -> None:
        if not self.browsing_drives and self.current_path:
            parent = self.current_path.parent
            if parent == self.current_path or len(parent.parts) <= 1:
                self._switch_to_drive_mode()
            else:
                self._navigate_to(parent)


# ===========================================================================
# Add Profile Modal
# ===========================================================================


class AddProfile(ModalScreen):
    CSS = """
    AddProfile { align: center middle; }

    #profile-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }

    .field-label { margin: 1 0 0 1; color: $text-muted; }

    Input { margin: 0 1 1 1; }

    #button-row {
        align: center middle;
        margin-top: 1;
        height: 3;
    }

    Button { margin: 0 1; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._db = Database()
        self._config = ConfigFile()

    @property
    def data(self):
        return self._db.data

    def compose(self) -> ComposeResult:
        with Vertical(id="profile-container"):
            yield Label("📁 ADD NEW PROFILE", id="title")
            yield Label("Profile Name:", classes="field-label")
            yield Input(placeholder="e.g. Work-PC, Laptop", id="profile-name")
            with Horizontal(id="button-row"):
                yield Button("Cancel", id="cancel", variant="error")
                yield Button("Create", id="create", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "create":
            name = self.query_one("#profile-name", Input).value.strip()
            if not name:
                self.notify("Profile name cannot be empty.", severity="warning")
                return

            if self._db.profile_is_exists(name):
                self.notify(
                    "Profile name already exists — try a different name.",
                    severity="warning",
                )
                return

            path: Path = self._config.profile_dir / name
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.notify(f"Could not create directory: {e}", severity="error")
                return

            # Copy managed files backups into new profile dir so it has its own copies
            for mf in self.data.get("managed_files", []):
                backup_path = Path(mf.get("backup_path", ""))
                if backup_path.exists():
                    dest = path / mf["alias"]
                    restore_backup_file(dest, backup_path)

            self._db.add_profile(name, path)
            self.notify(f"✅ Profile '{name}' created!")
            self.dismiss(True)
