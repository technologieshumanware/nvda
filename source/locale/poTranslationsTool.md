# PO Translation Tool

A tool to manage NVDA translations by finding missing translations and updating .po files.

## Package to install 

To use poTranslationTool.py you have to install `polib` This library can manipulate po files.
https://pypi.org/project/polib/

Command for installation:  `pip install polib` 

## Requirement

To generate nvda.pot run `.\scons pot`. This file contains all strings that need to be translated. 

## What does poTranslationsTool.py

This tool can find missing translations in .po files and update them back.
The tool has 3 features:

# 1. Extract Missing Translations
It can find all missing translations in po files and creates a po file for each language that contain all the missing translations for this language. Those po files will be placed in `source\localemissingTranslations`

- Scans all language .po files in `source\locale\*\LC_MESSAGES\nvda.po`
- Identifies untranslated entries (empty `msgstr` values)
- Creates separate .po files for each language in `source\locale\missingTranslations\`
- File naming pattern: `<language>_missingTranslations.po`

# 2. Merge Translated Entries
Merge translated entries from the missingTranslations directory in main po files `locale\*\LC_MESSAGES\nvda.po`.

- Takes completed translations from `source\locale\missingTranslations\` files
- Updates the main .po files with newly translated strings
- Only updates entries that were previously untranslated

# 3. Update .po Files from nvda.pot
Update all the main po files with the nvda.pot file. This ensures every po file has all the translations of the nvda project.

- Adds new translatable strings from `nvda.pot` to all language .po files
- Ensures all .po files contain the latest strings from the source code

## How to use the tool 

To use the tool you just have to run the script directly. A menu will appear in the terminal with 3 options. 

	1.If you want to extract all the missing translations from the po files, enter 1
	2.If you want to merge new translated entries form the missingTranslations directory, enter 2
	3.If you want to update .po files with new entries from nvda.pot, enter 3

**Important:** It's important to run the command line `.\scons pot` before updating .po files with new entries from nvda.pot. This command line will generate the nvda.pot in `nvda\output` directory. This file will contain all the strings that need to be translated in the nvda project. The third feature will not work if this step is not done previously. 

## File Locations

- **Main .po files:** `source\locale\<language>\LC_MESSAGES\nvda.po`
- **Translation template:** `output\nvda.pot`
- **Missing translations:** `source\locale\missingTranslations\<language>_missingTranslations.po`

## Notes

- The tool only processes files named `nvda.po` in the standard locale directory structure
- Missing translation files are automatically created/overwritten when extracting
- When merging, only entries that have translations (non-empty `msgstr`) are updated
