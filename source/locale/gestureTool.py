# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Gesture Translation Tool

Convert NVDA gesturesFromCommandName.ini files to/from PO format for translation
"""

import argparse
import shlex
from pathlib import Path
from typing import Dict, Tuple
from datetime import date
import logging
import polib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('GestureTool')


def parse_ini_file(iniFile: Path) -> Dict[str, Dict[str, Tuple[str, list, bool]]]:
    """
    Parse a gesturesFromCommandName.ini file.
    
    Args:
        iniFile: Path to the INI file to parse
        
    Returns:
        Dictionary structure: {section: {key: (value, [comments], isInvariant)}}
        - section: INI section name (example "GlobalCommands")
        - key: Command identifier
        - value: Gesture shortcut
        - comments: Translator comments for this entry
        - isInvariant: True if this entry is marked as INVARIANT
    """
    if not iniFile.exists():
        raise FileNotFoundError(f"INI file not found: {iniFile}")
    
    with open(iniFile, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    content: Dict[str, Dict[str, Tuple[str, list, bool]]] = {}
    currentSection = None
    isNextInvariant = False
    comments = []
    
    for line in lines:
        line = line.strip()
        
        # Check for INVARIANT marker
        if line.startswith('#') and "INVARIANT" in line.upper():
            isNextInvariant = True
            continue    
        
        # Collect translator comments
        if line.startswith('#') and "TRANSLATORS" in line.upper():
            currentComment = line[1:].strip()
            comments.append(currentComment)
            continue
        
        # Check for section header
        if line.startswith('[') and line.endswith(']'):
            currentSection = line[1:-1]
            content[currentSection] = {}
            comments = []  
            isNextInvariant = False
            continue
        
        # Parse key-value pair
        if '=' in line and currentSection is not None:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            content[currentSection][key] = (value, comments.copy(), isNextInvariant)
            comments = []  
            isNextInvariant = False

    return content


def export_ini_to_po(
    defaultContent:  Dict[str, Dict[str, Tuple[str, list, bool]]],
    iniFile: Path,
    poFileOutput: Path
):
    """
    Export gesture shortcuts from INI to PO file

    Args:
    defaultContent: Parsed content of the default INI file used as reference
    iniFile: Path to the INI file to export
    poFileOutput: Path where the PO file will be created
    """

    language = iniFile.parent.name
    iniContent = parse_ini_file(iniFile)
    
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'NVDA GesturesFromCommandName',
        'Report-Msgid-Bugs-To': '',
        'PO-Creation-Date': str(date.today()),
        'PO-Revision-Date': '',
        'Last-Translator': '',
        'Language-Team': '',
        'Language': language,
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
    }
    
    # Iterate over all entries from English (default) to ensure all keys are exported
    # Skip INVARIANT entries, they will be added during po2ini
    for section in defaultContent:
        for key in defaultContent[section]:
            defaultValue, defaultComments, isInvariant = defaultContent[section][key]
            
            if isInvariant:
                continue
            
            # Check if this entry exists in the target language
            if section in iniContent and key in iniContent[section]:
                value, comments, _ = iniContent[section][key]
            else:
                value = ""
                comments = []
            
            poComment = f'Section: {section}\nCommand: {key}'
            if defaultComments:
                poComment += '\n' + '\n'.join(defaultComments)
            
            entry = polib.POEntry(
                msgctxt=f'{section}.{key}',
                msgid=defaultValue,
                msgstr=value,
                comment=poComment
            )
            po.append(entry)
    
    poFileOutput.parent.mkdir(parents=True, exist_ok=True)
    po.wrapwidth = -1 
    po.save(str(poFileOutput))
    
    logger.info(f"Exported {len(po)} entries to: {poFileOutput}")


def import_po_to_ini(poPath: Path, iniPath: Path, englishContent: Dict[str, Dict[str, Tuple[str, list, bool]]]):
    """
    Import translated shortcuts from PO file back to INI file.
    Creates new sections and keys as needed for new or incomplete translations.
 
    Args:
        poPath: Path to the translated PO file
        iniPath: Path to the INI file to update
        englishContent: Parsed English INI content to get INVARIANT entries
    """
    
    poFile = polib.pofile(str(poPath))
    
    # Build complete final state for the INI file
    finalState: Dict[str, Dict[str, str]] = {}
    
    for section in englishContent:
        finalState[section] = {}
        for key in englishContent[section]:
            value, comments, isInvariant = englishContent[section][key]

            finalState[section][key] = value if isInvariant else ""
    
    # Override with translations from PO file (non-INVARIANT entries only)
    for entry in poFile:
        section, key = entry.msgctxt.rsplit('.', 1)
        # Added translated values
        finalState[section][key] = entry.msgstr
    
    # Write the complete final state to file
    write_ini_file(iniPath, finalState)


def write_ini_file(iniPath: Path, translations: Dict[str, Dict[str, str]]):
    """
    Write an INI file with all translations, preserving comments from existing file.
    
    Args:
        iniPath: Path to the INI file to create/update
        translations: Dictionary of translations {section: {key: value}}
    """
    iniPath.parent.mkdir(parents=True, exist_ok=True)
    
    
    # File exists - preserve comments and structure
    with open(iniPath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    defaultIndent = '\t'
    outputLines = []
    currentSection = None
    # Track written keys per section
    writtenKeys: Dict[str, set] = {} 
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == "":
            # Blank line, add missing keys from previous section before continuing
            if currentSection and currentSection in translations and currentSection in writtenKeys:
                for key, value in translations[currentSection].items():
                    if key not in writtenKeys[currentSection]:
                        outputLines.append(f'{defaultIndent}{key} = "{value}"\n')
                        writtenKeys[currentSection].add(key)

            if currentSection :
                outputLines.append(line)
            continue

        # Section header
        elif stripped.startswith('[') and stripped.endswith(']'):
            # Start new section
            currentSection = stripped[1:-1]
            writtenKeys[currentSection] = set() 
            outputLines.append(line)
            
        # Key-value pair
        elif '=' in stripped and currentSection:
            key = stripped.split('=', 1)[0].strip()
            # Mark this key as written for the current section
            writtenKeys[currentSection].add(key)
            
            # Update value if we have a translation for it
            if currentSection in translations and key in translations[currentSection]:
                outputLines.append(f'{defaultIndent}{key} = "{translations[currentSection][key]}"\n')
            else:
                # Keep original line if no translation available
                outputLines.append(line)
        else:
            outputLines.append(line)
    
    # Add missing keys from last section
    if currentSection and currentSection in translations and currentSection in writtenKeys:
        for key, value in translations[currentSection].items():
            if key not in writtenKeys[currentSection]:
                outputLines.append(f'{defaultIndent}{key} = "{value}"\n')
                writtenKeys[currentSection].add(key)
    
    # Add completely new sections that weren't in original file
    for section, keys in translations.items():
        if section not in writtenKeys:
            outputLines.append(f'\n[{section}]\n')
            for key, value in keys.items():
                outputLines.append(f'{defaultIndent}{key} = "{value}"\n')
    
    # Write updated content
    with open(iniPath, 'w', encoding='utf-8') as f:
        f.writelines(outputLines)


def ini2po_command(args):
    """
    Handle the ini2po export command
    
    Args:
        args: Command line arguments
    """

    iniDir = Path(args.source)
    defaultIniFile = iniDir/'en'/'gesturesFromCommandName.ini'
    
    if not defaultIniFile.exists():
        logger.error(f"English .ini file not found : {defaultIniFile}")
        return 
    
    if not iniDir.is_dir():
        logger.error(f"Source path is not a directory: {iniDir}")
        return 
    
    defaultValue = parse_ini_file(defaultIniFile)

    outputDir = Path(args.output)
    outputDir.mkdir(parents=True, exist_ok=True)
 
    exportedCount = 0
    for iniFile in iniDir.glob('*/gesturesFromCommandName.ini'):
        language = iniFile.parent.name
        poFileOutput = outputDir/f'gesturesFromCommandName_{language}.po'
        
        try:
            export_ini_to_po(defaultValue, iniFile, poFileOutput)
            exportedCount += 1
        except Exception as e:
            logger.error(f"Failed to export {language}: {e}")
    
    logger.info(f"Exported {exportedCount} PO files to: {outputDir}")
    return 


def po2ini_command(args):
    """
    Handle the po2ini import command
    
    Args:
        args: Command-line arguments containing:
    """

    poDir = Path(args.source)
    iniDir = Path(args.output)
    
    if not poDir.exists():
        logger.error(f"PO folder not found: {poDir}")
        return
    
    # Load English INI to get INVARIANT entries
    englishIniFile = iniDir/'en'/'gesturesFromCommandName.ini'
    if not englishIniFile.exists():
        logger.error(f"English INI file not found: {englishIniFile}")
        return
    
    englishContent = parse_ini_file(englishIniFile)
    
    importedCount = 0
    for poFile in poDir.glob('gesturesFromCommandName_*.po'):

        language = poFile.stem.replace('gesturesFromCommandName_', '')
        iniFile = iniDir/language/'gesturesFromCommandName.ini'
        
        try:
            import_po_to_ini(poFile, iniFile, englishContent)
            logger.info(f"Updated: {iniFile}")

            importedCount += 1
        except Exception as e:
            logger.error(f"Failed to import {language}: {e}")
    
    logger.info(f"Imported {importedCount} PO files")
    return 



def main():
    """
    Interactive mode - waits for user input and parses commands
    """
    parser = argparse.ArgumentParser(
        prog='gesture-tool',
        description='Gesture Translation Tool - Convert gesturesFromCommandName.ini files to/from PO format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        exit_on_error=False,  
        epilog=
    """Commands:
        ini2po - Export INI files to PO files:
            ini2po (uses defaults)
            ini2po -s "<ini_directory_path>" -o "<output_directory_path>"
            ini2po --source "<ini_directory_path>" --output "<output_directory_path>"
            
            Defaults: -s ./source/locale  -o ./source/locale/missing_gesturesFromCommandName_translations

        po2ini - Import PO files back to INI files:
            po2ini (uses defaults)
            po2ini -s "<po_directory_path>" -o "<locale_directory_path>"
            po2ini --source "<po_directory_path>" --output "<locale_directory_path>"
            
            Defaults: -s ./source/locale/missing_gesturesFromCommandName_translations  -o ./source/locale

        exit / quit - Exit the program

        Expected folder structure:
            <locale_folder>/<language_code>/gesturesFromCommandName.ini
            Example: locale/fr/gesturesFromCommandName.ini

        Examples:
            Export with defaults:
                ini2po
                
            Export with custom paths:
                ini2po -s "C:/user/nvda/source/locale" -o "C:/user/translations/output"

            Import with defaults:
                po2ini
                
            Import with custom paths:
                po2ini -s "C:/user/translations/output" -o "C:/user/nvda/source/locale"
        """
    )
    
    subParsers = parser.add_subparsers(dest='command', help='Command to execute')

    localeDirectory = Path(__file__).parent
    defaultPoDirectory = localeDirectory/'missing_gesturesFromCommandName_translations'
    
    # Export subcommand: ini2po
    exportParser = subParsers.add_parser(
        'ini2po',
        help='Export INI files to PO format'
    )
    exportParser.add_argument(
        '-s', '--source',
        required=False,
        default=str(localeDirectory),
        help='Directory path containing language subdirectories (default: ./source/locale)'
    )
    exportParser.add_argument(
        '-o', '--output',
        required=False,
        default=str(defaultPoDirectory),
        help='Directory path where PO files will be created (default: ./source/locale/missing_gestureFromCommandName_translations)'
    )
    
    # Import subcommand: po2ini
    importParser = subParsers.add_parser(
        'po2ini',
        help='Import PO files back to INI format'
    )
    importParser.add_argument(
        '-s', '--source',
        required=False,
        default=str(defaultPoDirectory),
        help='Directory path containing translated PO files (default: ./source/locale/missing_gesturesFromCommandName_translations)'
    )
    importParser.add_argument(
        '-o', '--output',
        required=False,
        default=str(localeDirectory),
        help='Directory path where INI files will be updated (default: ./source/locale)'
    )
    
    print("=== Gesture Translation Tool ===")
    print("Type 'help' for available commands or 'exit'/'quit' to leave\n")
    
    # Interactive loop
    while True:
        try:
            # Get user input
            userInput = input("gesture-tool> ").strip()
            
            if not userInput:
                continue
            
            # Check for exit commands
            if userInput.lower() in ['exit', 'quit', 'q', 'e']:
                print("Exiting Gesture Translation Tool")
                break
            
            # Check for help command
            if userInput.lower() in ['help', 'h', '-h', '--help']:
                parser.print_help()
                continue
            
            # Parse the input as command-line arguments
            try:
                argsList = shlex.split(userInput)
                args = parser.parse_args(argsList)
                
                if not args.command:
                    parser.print_help()
                    continue
                
                # Dispatch to appropriate command handler
                if args.command == 'ini2po':
                    ini2po_command(args)
                elif args.command == 'po2ini':
                    po2ini_command(args)
                    
            except Exception as e:
                logger.error(f" Unexpected error: {e}")
                print("Type 'help' for usage information")
                
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    return 


if __name__ == '__main__':
    main()
