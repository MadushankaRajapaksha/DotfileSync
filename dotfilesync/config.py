import os
import platform
from pathlib import Path 

class ConfigFile:
    def __init__(self):
        self.home = Path.home()
        self.os = platform.system()

        # create a config files relevent os
        # for windows
        if self.os == "Windows":
            self.config_dir = self.home / "AppData" / "Local" / "DotfileSync"
        # for Linux and Macos XDG standerd
        else: 
            self.config_dir = self.home / ".config" / "dotfilesync"

        # create profile folder
        self.profile_dir = self.config_dir / "profiles"
        self.backup_dir = self.config_dir / "backup"

        # check already exsit and if not create
        self.ensure_dir()

    def ensure_dir(self):
        """if not exsit a folder create"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # debug : test working
        if os.getenv("DEBUG"):
            print(f"config dir : {self.config_dir}")
