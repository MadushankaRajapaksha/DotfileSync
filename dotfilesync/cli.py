from .config import ConfigFile
from .app import DotfileSyncApp
from .core import Database,backup_file
from pathlib import Path

def main():
    # cheack have config folder
    configs = ConfigFile()

    datas = Database()
    # app TUI opens
    # print(f"before add {datas.data}")

    # datas.add_manged_files(Path(r"F:\Hackclub\DotfileSync\.gitconfig"))
    # print(f"after add {datas.data}")

    # backup = backup_file(Path(r"F:\Hackclub\DotfileSync\.gitconfig"))
    # if backup:
    #     print(str(backup))

    # datas.add_profile("name", Path(r"F:\Hackclub\DotfileSync\.gitconfig"))

    app = DotfileSyncApp(configs)
    app.run()

    # TODO :
    # impliment core - symlink link coustem directory to home directory
    # test with .gitcongif
