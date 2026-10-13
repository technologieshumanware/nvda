# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

#
# Tool to extract missing translations from .po files and update main.po files with new translations.
#
# The script creates a "missingTranslations" directory in source/local to store the missing translation in .po files.
# It can also merge updated translations back into the main .po files from the missingTranslations files.
# It also can update .po files with new entries from nvda.pot.


from pathlib import Path
import polib 


# Extract missing translations from all .po files
def extractMissingTranslations():

    localeDirectory = Path(__file__).parent
    outputDirectory = localeDirectory/"missingTranslations"
    outputDirectory.mkdir(exist_ok=True)
    
    print("Extracting missing translations\n")
    
    poFiles = list(localeDirectory.glob('*/LC_MESSAGES/nvda.po'))
    
    if not poFiles:
        print(f"No .po files found in {localeDirectory}")
        return
    
    for poFile in sorted(poFiles):
        language = poFile.parent.parent.name
        outputFile = outputDirectory/f"{language}_missingTranslations.po"
        
        count = extractMissingTranslationToFile(poFile, outputFile)
        
        if count > 0:
            print(f"{language} - Extracted {count} missing translations to: {outputFile.relative_to(localeDirectory)}")
    
    print(f"\nMissing translation files saved to: {outputDirectory.relative_to(localeDirectory.parent)}\n")


# Create .po file containing only untranslated entries
def extractMissingTranslationToFile(sourcePoPath, outputPoPath):
        
        po = polib.pofile(str(sourcePoPath))
        
        # Create a new .po file for missing translations
        outputPo = polib.POFile()
        outputPo.metadata = po.metadata.copy()
        
        # Add untranslated entries
        for entry in po.untranslated_entries():
            outputPo.append(entry)
        
        if len(outputPo) > 0:
            outputPo.wrapwidth = -1
            outputPo.save(str(outputPoPath))
            return len(outputPo)
        
        return 0


# Update untranslated strings of main .po files with translated strings from *_missingTranslations .po files
def mergeMissingTranslations():
    
    localeDirectory = Path(__file__).parent
    missingTranslationDirectory = localeDirectory/"missingTranslations"
    
    if not missingTranslationDirectory.exists():
        print(f"Error: missingTranslations directory not found: {missingTranslationDirectory}")
        return
    
    print("Merging translated strings back into main .po files\n")
    
    missingTranslationFiles = list(missingTranslationDirectory.glob('*_missingTranslations.po'))
    
    if not missingTranslationFiles:
        print(f"No *_missingTranslations.po files found in {missingTranslationDirectory}")
        return
    
    for missingFile in sorted(missingTranslationFiles):
        # Get the name of the main .po 
        language = missingFile.stem.replace('_missingTranslations', '')
        mainPoFile = localeDirectory/language/"LC_MESSAGES"/"nvda.po"
        
        if not mainPoFile.exists():
            print(f"{language} main .po file not found: {mainPoFile}")
            continue
        
        count = mergeTranslations(missingFile, mainPoFile)
        
        if count > 0:
            print(f"{missingFile.name} merged {count} translations into {mainPoFile}")


# Merge translated strings back into main .po file
def mergeTranslations(missingTranslationPoPath, mainPoPath):

        missingTranslationPo = polib.pofile(str(missingTranslationPoPath))
        mainPo = polib.pofile(str(mainPoPath))
        
        updatedCount = 0
        
        # Create a dictionary that contain all translated entries from missingTranslationPo
        translations = {}
        for entry in missingTranslationPo:
            if entry.msgstr:
                translations[entry.msgid] = entry
        
        # Update mainPo with new translations
        for entry in mainPo:
            if entry.msgid in translations:
                newEntry = translations[entry.msgid]
                if newEntry.msgstr != entry.msgstr:
                    entry.msgstr = newEntry.msgstr
                    updatedCount += 1
        
        if updatedCount > 0:
            mainPo.wrapwidth = -1
            mainPo.save(str(mainPoPath))
        
        return updatedCount


# Update .po files with new entries from nvda.pot
def updatePoFiles():

    localeDirectory = Path(__file__).parent
    poFilesPath = list(localeDirectory.glob("*/LC_MESSAGES/nvda.po"))

    # Get all the entries in nvda
    try:
        potFile = polib.pofile(str(localeDirectory.parent.parent/"output"/"nvda.pot"))
    except:
        print("\nError: nvda.pot file not found in output directory.")
        print("Run '.\\scons pot' first to generate the pot file.\n")
        return

    allEntries = list(potFile)

    print("\nUpdating .po files\n")

    for poFile in sorted(poFilesPath):
        po = polib.pofile(str(poFile))
        count = 0

        #Add all entries that are missing in every .po file
        for entry in allEntries:
            if not po.find(entry.msgid, msgctxt=entry.msgctxt):
                po.append(entry)
                count += 1

        print(f"Updated {poFile.parent.parent.name} with {count} new entries from nvda.pot")
        po.wrapwidth = -1
        po.save(str(poFile))


def main():
    # Guide of the tool
    print("\n1. Extract missing translations in .po files")
    print("2. Merge translated strings back into main .po files")
    print("3. Update .po files with new entries from nvda.pot")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        extractMissingTranslations()
    elif choice == '2':
        mergeMissingTranslations()
    elif choice == "3":
        updatePoFiles()
    elif choice == '4':
        print("Exiting poTranslationsTool.py")
    else:
        print("Invalid choice. Try again using 1, 2, 3, or 4")

# Run main() function only if this script is executed directly
if __name__ == "__main__":
    main()
