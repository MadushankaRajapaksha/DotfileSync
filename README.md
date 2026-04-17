# 📂 DotfileSync

#### *stop manually copying your configs. Switch environments in a heartbeat* 

`DotfileSync` is a lightweight, Python-powerd TUI that manages your configuration files using *Symbolic Links*. Whether your moving from your office desk to switching from "Work Mode" to "Gaming Mode", this tool swaps your `.gitconfig`,`.vimrc` like all config or any file instantly.

# ✨Why use this?

Most of dotfile managers are either too simple(manual copuing) or too complex.

DotfileSync sits right in the middle:
 - *Profile Based* : Create Profiles like `work`,`home` like.
 - *safe by design* : automaticaly backups ur exsits files before touching them.
 - *Zero Logic Loss* : your files stay where they are. app just change where OS looks for Them
 - Built-in Editor: Tweak your settings directly inside the app.
# 🚀 Getting Started

### 1. Installation
Once the package is published to PyPI, anyone can install it with a single command:
```
pip install DotfileSync-cli
```

 

## 📖 Simple App Guide (TUI)
### 1. Launch the App
Open your terminal and type:
```
dotSync
```
You’ll see a clean dashboard with your Profiles and Files.

### 2. Create a Profile
- Click "Add Profile".
- Give it a name (like Work or Home).
- This creates a safe folder to store those specific settings.

### 3. Add Your Files
- Choose the file you want to manage (e.g., .bashrc, .).
- The app takes a copy and keeps it safe inside your profiles.
 
### 4. Activate & Link (The Magic)
- Select your profile (e.g., Work).
- Click "Activate Profile".
- Then Click "Link Profile"


### 5. Revert to Normal
If you want to stop using the app and go back to exactly how things were:
- Click "Unlink Profile".
- Now you can chage profile and re-link
 

## 🛡️ A Note for Windows Users
If you're on Windows, make sure you have Developer Mode enabled in your settings. This allows Python to create symbolic links without needing to run as Administrator every single time. Do not delete or uninstall app when linked Profile(That can miss u file)
# 🤝 Contributing
Contributions are welcome! If you find a bug or want a new feature, open an issue or submit a PR.