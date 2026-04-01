# DotfileSync 🚀

DotfileSync is a lightweight, intuitive **Terminal User Interface (TUI)** designed to manage your configuration files (.bashrc, .vimrc, .gitconfig, etc.) without the complexity of traditional symlink managers. 

Unlike other tools, DotfileSync allows you to maintain multiple named profiles (e.g., "Work", "Home", "Minimal") and switch between them instantly using a clean, interactive interface.

---

## ✨ Features

- **📂 Multi-Profile Support**: Create and manage distinct profiles for different environments.
- **🖥️ Interactive TUI**: Built with [Textual](https://textual.textualize.io/) for a smooth terminal experience.
- **🔗 Intelligent Symlinking**: Seamlessly link and unlink your configurations without manual `ln -s` commands.
- **📝 Built-in Editor**: View and edit your managed files directly within the TUI.
- **🛡️ Automatic Backups**: Every file you add is automatically backed up before any changes are made.
- **🚀 Cross-Platform**: Works on both Windows and Linux/macOS, following OS-specific configuration standards.

---

## 🛠️ Installation

### Using pip (Recommended)
Install the latest version directly from PyPI:
```bash
pip install DotfileSync
```

### From Source
1. **Clone the repository:**
   ```bash
   git clone https://github.com/MadushankaRajapaksha/DotfileSync.git
   cd DotfileSync
   ```
2. **Install the package:**
   ```bash
   pip install .
   ```

### Post-Installation
After installation, the `dotSync` command will be available in your terminal.

---

## 📖 User Guide & Tutorial

This section walks you through a complete workflow with DotfileSync.

### 1. Launching the App
Open your terminal and type:
```bash
dotSync
```
You will see the main dashboard with a banner and two main tables: **Profiles** and **Managed Files**.

### 2. Setting Up Your First Profile
A profile represents a set of configurations. For example, you might have one for "Work" and another for "Personal".
- Click the **"Add Profile"** button.
- Enter a name (e.g., `Work`) and confirm.
- This creates a dedicated folder in your config directory to store this profile's version of your dotfiles.

### 3. Adding Files to Manage
To start tracking a file (like your `.bashrc`):
- Click **"Manage Files"** on the main screen.
- In the file manager modal, click **"Add File"**.
- Use the built-in file browser to navigate to your home directory or wherever your config is located.
- Select the file and click **"Add File"**.
- **What happens next?**
  1. DotfileSync creates a **backup** of the original file.
  2. It copies the file into **every existing profile** directory.
  3. It registers the file in the internal database.

### 4. Editing Files in the TUI
You don't need to leave the app to make changes:
- In the **Manage Files** modal, select a file from the list.
- Its content will appear in the editor below.
- Make your changes and click **"Save"**. 
- *Note: Changes are saved to the copy within the active profile directory.*

### 5. Activating and Linking
This is where the magic happens.
- On the main screen, select the profile you want to use from the **Profiles** table.
- Click **"Activate Profile"**.
- Click **"Link Profile"**.
- **Result**: DotfileSync replaces the actual file on your system with a **symlink** pointing to the file inside your active profile's folder. Your system now uses the "Work" version of your `.bashrc`.

### 6. Switching or Reverting
- **To switch profiles**: Select a new profile, "Activate", and "Link".
- **To revert to originals**: Click **"Unlink Profile"**. The symlinks will be removed, and your original files (restored from backup) will be put back in their place.

 
---

## 🧪 Development

To run the project in development mode:
```bash
pip install -e .
python -m dotfilesync.cli
```

### Dependencies
- `textual`: Core TUI framework.
- `rich`: Beautiful CLI formatting.
- `pyfiglet`: Banner generation.

---

## 📄 License
This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

### 👨‍💻 Author
**Madushanaka Rajapaksha**  
[GitHub](https://github.com/MadushankaRajapaksha) | [Email](mailto:MadushankaRajapaksha999@gmail.com)
