# Gesture Translation Tool

Translation tool for NVDA's `gesturesFromCommandName.ini` files. Converts keyboard shortcuts between INI format and PO format to facilitate translation.

### Prerequisites
```bash
pip install polib
```

## Usage

### Interactive Mode

Run the script and it will wait for your commands:

You will see:

```
=== Gesture Translation Tool ===
Type 'help' for available commands or 'exit'/'quit' to leave

gesture-tool>
```

### Available Commands
- For every commands arguments are optional

#### `ini2po` - Export to PO

Converts INI files to PO files for translation.

**Syntax:**
```bash
ini2po
ini2po -s "<path_to_locale>" -o "<po_output_path>"
```

**Default values:**
- `-s` / `--source`: `./source/locale` 
- `-o` / `--output`: `./source/locale/missing_gesturesFromCommandName_translations`

**Example:**
```bash
ini2po -s "C:/user/nvda/source/locale" -o "C:/user/translations/PO"
```

**What it does:**
- It will create PO files for all the maintain languages at the default or given PO directory output


#### `po2ini` - Import from PO

Converts translated PO files to INI files.

**Syntax:**
```bash
po2ini
po2ini -s "<path_to_po>" -o "<path_to_locale>"
```

**Default values:**
- `-s` / `--source`: `./source/locale/missing_gesturesFromCommandName_translations`
- `-o` / `--output`: `./source/locale`

**Example:**
```bash
po2ini -s "C:/user/translations/PO" -o "C:/user/nvda/source/locale"
```

**What it does:**
- It will update all the gesturesFromCommandName.ini at the default or given PO directory with the translated value of the PO directory. 
- Invariant values will also be added in INI files. 

---

#### Display Help
Shows complete help for available commands.

```bash
h
-h
help
--help
```


#### Exiting the tool
Closes the tool.

```bash
exit
quit 
e
q
```

## File Format

### Directory Structure
- The INI directory should contain language subdirectory containing gesturesFromCommandName.ini file.

```
source/locale/
├── en/
│   └── gesturesFromCommandName.ini    # English reference file
├── fr/
│   └── gesturesFromCommandName.ini    # French translation
├── de/
│   └── gesturesFromCommandName.ini    # German translation
└── missing_gesturesFromCommandName_translations/
    ├── gesturesFromCommandName_fr.po  # French PO file
    └── gesturesFromCommandName_de.po  # German PO file
```

## Workflow Examples

### 1. Export existing files to PO
```bash
gesture-tool> ini2po
```
Result: PO files created in `source/locale/missing_gestureFromCommandName_translations/`

### 2. Translate the PO files
Translate the entries of generated PO files. 

### 3. Import translations
```bash
gesture-tool> po2ini
```
Result: Updated INI files in `source/locale/<language>/gesturesFromCommandName.ini`


## Advanced Features

### Comment Handling

**To write comments for translators:**

Add a comment line above the entry in the PO file starting with `# Translators:`

**Example:**
```ini
[section]
  # Translators: This is the keyboard shortcut for saving a document
  entry = 'shortcut'
```

**To mark an entry as INVARIANT:**

Add `# Translators: INVARIANT` above the entry. Invariant entries will be automatically copied without requiring translation.

**Example:**
```ini
[section]
  # Translators: INVARIANT
  entry = 'shortcut'
``` 

### New Languages

To create a translation for a new language:

1. Create a INI file in the directory of this language: `./source/locale/<language_code>/gesturesFromCommandName.ini`
2. Run `ini2po`
3. Translate generate po files
4. Run `po2ini`
5. The INI file will be updated with the translated values
