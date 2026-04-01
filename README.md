# 📂 DotfileSync

#### *stop manually copying your configs. Switch environments in a heartbeat* 

`DotfileSync` is a lightweight, Python-powerd TUI that manages your configuration files using *Symbolic Links*. Whether your moving from your office desk to switching from "Work Mode" to "Gaming Mode", this tool swaps your `.gitconfig`, and `.vimrc` instantly.

# ✨Why use this?

Most of dotfile managers are either too simple(manual copuing) or too complex.

DotfileSync sits right in the middle:
 - *Profile Based* : Create Profiles like `work`,`home` like.
 - *safe by design* : automaticaly backups ur exsits files before touching them.
 - *Zero Logic Loss* : your files stay where they are. app just change where OS looks for Them

# 🚀 Getting Started

### 1. Installation
Once the package is published to PyPI, anyone can install it with a single command:
```
pip install DotfileSync-cli
```

### 2. Launching the App
Simply run the core app to start managing your profiles.
```
dotSync
```
## 🛡️ A Note for Windows Users
If you're on Windows, make sure you have Developer Mode enabled in your settings. This allows Python to create symbolic links without needing to run as Administrator every single time.
# 🤝 Contributing
Contributions are welcome! If you find a bug or want a new feature, open an issue or submit a PR.