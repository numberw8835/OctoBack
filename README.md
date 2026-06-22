# 🐙 OctoBack

<img src="assets/octoback_logo_clean.png" alt="OctoBack logo" width="144" />

OctoBack is a lightweight CLI backup manager that separates the **intent** (what to back up) from the **action** (the actual backup process). By maintaining a curated index of files and folders, OctoBack ensures your backup vault remains organized, predictable, and clean.

---

## 🚀 Features

- **Decoupled Architecture**: Specify what you want to track separately from when and how you back it up.
- **Selective & Global Backup**: Run backups for specific paths, files under the current directory, or back up all indexed paths at once.
- **Context-Aware Restoration**: Restore folders or files contextually based on your shell's current working directory (`pwd`), with safety protections blocking accidental root (`/`) or home directory (`~`) restores.
- **Interactive TUI Restore Mode**: Visually browse, select, and restore backed-up items inside the current directory, including a direct shortcut to restore the configuration directory `~/.octoback`.
- **Aesthetic Logic Formatting**: Clean command-line feedback with formal mathematical logic symbols (`⊤`, `⊥`, `∴`, `¬`) and thin-line progress indicators.
- **Safe Archiving & Extraction**: Compress/expand your vault on demand into a single package (`Vault.tar.gz`) with Zip Slip protection and automatic file cleanups on interrupt or abort.
- **Easy Installation**: Comes with a quick installation script.

---

## 📦 Installation

To install OctoBack globally to your local user binary directory (`~/.local/bin`), run the following command in the project root:

```bash
./install.sh
```

Ensure that `~/.local/bin` is in your shell's environment `$PATH`. If it is not, add the following to your `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$PATH:$HOME/.local/bin"
```

---

## 🛠️ Usage

### 1. Setup
To initialize your environment and generate the default `octo.yaml` configuration file, run:

```bash
octoback init
```

By default, this sets up configuration files under `~/.octoback/` and a default vault at `~/Vault`.

#### Default Configuration (`~/.octoback/octo.yaml`)
```yaml
storage:
  index_path: "~/.octoback/index.json"
  vault_path: "~/Vault"
```

### 2. The Indexing Phase
Rather than transferring files on the fly, you curate an index of important folders and files you want to track.

* **Add a folder/file to the index**:
  ```bash
  octoback add folder/
  ```
  If no directory is specified, it defaults to the current directory (`.`). Multiple paths can be passed in a single command.
  > [!NOTE]
  > This indexes the folder itself as a single unit. It dynamically tracks and backs up any new files added to the folder in the future. However, in the interactive TUI restore screen, the folder can only be restored as a single unit.

* **Granular Indexing**:
  ```bash
  octoback add -g folder/
  ```
  The `-g` flag scans the directory and indexes all subfolders and files individually.
  > [!NOTE]
  > This allows you to selectively restore individual files in the TUI restore mode. However, newly created files inside this folder will not be tracked or backed up in the future unless you re-run `octoback add -g`.

* **Remove from index**:
  ```bash
  octoback remove folder/
  ```
  *(Alias: `octoback rm folder/`)*

* **Prune index**:
  ```bash
  octoback prune
  ```
  Removes non-existent or deleted paths from the index database.

* **List all indexed files**:
  ```bash
  octoback list
  ```
  Prints the sorted index database (utilizes `bat` for colorized JSON formatting if installed, otherwise defaults to standard output).

### 3. The Execution Phase
Trigger the backup sync using rsync:

* **Backup specific paths/current directory**:
  ```bash
  octoback backup [paths...]
  ```
  If no paths are specified, it defaults to the current directory (`.`).
  > [!NOTE]
  > The first time you run a backup, OctoBack automatically indexes and tracks your config folder `~/.octoback` so that your settings and indexes are safely backed up too!

* **Backup all indexed files/folders**:
  ```bash
  octoback backup --all
  ```

* **Compress the entire backup vault**:
  ```bash
  octoback compress
  ```
  Compresses your `~/Vault` directory into `~/Vault.tar.gz` and removes the uncompressed directory.

* **Expand the backup vault**:
  ```bash
  octoback expand
  ```
  Extracts `~/Vault.tar.gz` back into the standard `~/Vault` directory structure and deletes the archive.

### 4. The Recovery Phase
Restoring files is fast, safe, and can be done selectively. 

> [!IMPORTANT]
> **Safety First**: Directly restoring the home directory root (`~`) or system root (`/`) is blocked to protect active configuration files and system locks. Specify subdirectories to restore, or use TUI restore instead.

* **Restore a specific file/folder**:
  ```bash
  octoback restore path/to/file_or_folder
  ```
  If no path is specified, it defaults to restoring the current directory from the backup archive.

* **Interactive TUI Restore**:
  Run this command to visually browse, select (using `Space`), and restore tracked items inside the current folder:
  ```bash
  octoback restore list
  ```
  > [!TIP]
  > **Quick Setup Recovery**: Inside the TUI restore screen, you can press **`o`** to directly restore your configuration directory `~/.octoback`.

* **Full Restore**:
  Restore all indexed folders and files recorded in the database to their original paths:
  ```bash
  octoback restore --all
  ```

---

## 🎨 Minimalist Feedback & Symbols

OctoBack uses a clean, formal mathematical logic style for feedback symbols in console outputs:

| Symbol | Representation | Meaning |
| :---: | :--- | :--- |
| `⊤` | **True (Top)** | Operation succeeded successfully |
| `⊥` | **False (Bottom)** | An error occurred or command failed |
| `∴` | **Therefore** | General informational message |
| `¬` | **Negation** | A warning or path not found |

Progress bars are kept clean, thin, and non-intrusive (e.g. `backing up ━━━── 60% | filename.txt`).

---

## 🗺️ Roadmap & Configuration Options

The configuration file is designed to support the following engine extensions, currently planned for future release:
- **`copy_tool`**: Toggle backup engines between `rsync` and `cp`.
- **`compression`**: Choose archive compression algorithm (`none`, `gzip`, `zstd`).
- **`security`**: Enable AES-256 encryption.
- **`track_history`**: Enable versioned vault history.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
