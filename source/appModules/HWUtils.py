# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# Standard library imports
import os
from typing import Optional

# NVDA imports
import globalVars
import inputCore
import keyboardHandler
import languageHandler
import winUser
from keyboardHandler import KeyboardInputGesture
from logHandler import log

ScriptNameT = str

# Virtual Key Code constants for keyboard layout independence
# These represent physical key positions, not characters
virtualKeys = {
    'A': 0x41,  # 'A' key
    'D': 0x44,  # 'D' key
    'G': 0x47,  # 'G' key
    'H': 0x48,  # 'H' key
    'I': 0x49,  # 'I' key
    'N': 0x4E,  # 'N' key
    'O': 0x4F,  # 'O' key
    'W': 0x57,  # 'W' key
}


def init(self) -> None:
	"""Initialize locale gesture mapping for the app module."""
	initLocaleGesture(self)


def initLocaleGesture(self) -> None:
	"""Initialize the locale gesture map if not already initialized."""
	try:
		self.localeGestureFromCommandNameMap
	except AttributeError:
		# localeGestureFromCommandNameMap is not initialized
		self.localeGestureFromCommandNameMap = GlobalGestureCommandNameMap()
		loadLocaleGestureFromCommandNameMap(self)


def getShortcutFromCommandNameAndAppModuleName(self, commandName: str, appModuleName: str) -> str:
	"""
	Get keyboard shortcut for a specific command and app module.
	
	Args:
		commandName (str): Name of the command to find
		appModuleName (str): Name of the app module
		
	Returns:
		str: Keyboard shortcut string, or empty string if not found
	"""
	if not commandName or not appModuleName:
		log.error("getShortcutFromCommandName: Invalid parameters: %r, %r" % (commandName, appModuleName))
		return ""
	
	log.debug("getShortcutFromCommandName %s, %s" % (commandName, appModuleName))
	initLocaleGesture(self)
	
	for commandInfo in self.localeGestureFromCommandNameMap._map.items():
		# parse all commands with the same keyboard shortcut
		for commandObject in commandInfo[1]:
			className = commandObject[1]	# ex: WordDocument
			scriptName = commandObject[2]		# ex: insertOrEditEquation
			if appModuleName == className and commandName == scriptName:
				kbShortcut = commandInfo[0]	# ex: alt+=
				moduleName = commandObject[0]	# ex: NVDAObjects.window.winword
				if "nvda" in kbShortcut:
					kbShortcut = kbShortcut.replace("nvda", getNvdaModifierKey(self), 1)

				log.debug("commandObject %s, %s, %s, %s" % (moduleName, className, scriptName, kbShortcut))
				return kbShortcut
	
	log.error("Shortcut not found for command: %s, appModule: %s" % (commandName, appModuleName))
	return ""


def getShortcutFromCommandName(self, commandName: str) -> str:
	"""Get keyboard shortcut for a command in the current app module.
	
	Args:
		commandName (str): Name of the command to find
		
	Returns:
		str: Keyboard shortcut string, or empty string if not found
	"""
	return getShortcutFromCommandNameAndAppModuleName(self, commandName, self.appModuleName)


def emulateKeyPressFromCommandNameAndAppModuleName(self, commandName: str, appModuleName: str) -> None:
	"""Emulate a key press for a command in a specific app module.
	
	Args:
		commandName (str): Name of the command
		appModuleName (str): Name of the app module
	"""
	emulateKeyPress(getShortcutFromCommandNameAndAppModuleName(self, commandName, appModuleName))


def emulateKeyPressFromCommandName(self, commandName: str) -> None:
	"""Emulate a key press for a command in the current app module.
	
	Args:
		commandName (str): Name of the command
	"""
	emulateKeyPress(getShortcutFromCommandName(self, commandName))

def emulateGestureFromCommandName(self, commandName: str) -> None:
	"""Emulate a gesture for a command in the current app module.
	
	Args:
		commandName (str): Name of the command
	"""
	kbIdentifier = getShortcutFromCommandName(self, commandName)
	emulateGesture(kbIdentifier)

def emulateKeyPress(kbIdentifier: str) -> None:
	"""
	Emulates a keyboard press using the specified identifier.
	
	Args:
		kbIdentifier (str): Keyboard identifier (e.g., "alt+f", "ctrl+c")
	"""
	if not kbIdentifier or not isinstance(kbIdentifier, str):
		log.error("emulateKeyPress: Invalid keyboard identifier: %r" % kbIdentifier)
		return
	
	try:
		log.debug("emulateKeyPress: %s" % kbIdentifier)
		gesture = KeyboardInputGesture.fromName(kbIdentifier)
		gesture.send()
	except Exception as e:
		log.error("emulateKeyPress failed for %s: %s" % (kbIdentifier, e))


def emulateGesture(kbIdentifier: str) -> None:
	"""
	Emulates a gesture using the input core manager.
	
	Args:
		kbIdentifier (str): Keyboard identifier (e.g., "shift+1", "nvda+f3")
	"""
	if not kbIdentifier or not isinstance(kbIdentifier, str):
		log.error("emulateGesture: Invalid keyboard identifier: %r" % kbIdentifier)
		return
	
	try:
		gesture = KeyboardInputGesture.fromName(kbIdentifier)
		inputCore.manager.emulateGesture(gesture)
	except Exception as e:
		log.error("emulateGesture failed for %s: %s" % (kbIdentifier, e))


def emulateGestureWithVK(char: str, modifiers: list = None, extended: bool = False) -> None:
	"""
	Emulates a gesture using virtual key codes, independent of keyboard layout.
	This is useful for non-QWERTY keyboard layouts where character-based gestures may fail.
	
	Args:
		char (str): Character representing the main key (e.g., 'G', 'O', 'H')
		modifiers (list): List of modifier tuples [(vk, extended), ...], e.g., [(winUser.VK_CONTROL, False)]
		extended (bool): Whether the main key is an extended key
	
	Example:
		# Emulate Ctrl+Alt+O (independent of keyboard layout)
		emulateGestureWithVK('O', [(winUser.VK_CONTROL, False), (winUser.VK_MENU, False)])
	"""
	if modifiers is None:
		modifiers = []
	
	try:
		# Convert character to uppercase for consistency
		char = char.upper()
		
		# Get VK code from virtualKeys dictionary, or use ord() for A-Z
		if char in virtualKeys:
			vkCode = virtualKeys[char]
		else:
			log.error(f"emulateGestureWithVK: Unsupported character: {char!r}")
			return
		
		log.debug(f"emulateGestureWithVK: char={char!r}, vkCode=0x{vkCode:02X} ({vkCode}), modifiers={modifiers}, extended={extended}")
		
		# Send the keys directly using keybd_event for maximum compatibility
		# Press modifiers down
		for modVk, modExt in modifiers:
			winUser.keybd_event(modVk, 0, 1 if modExt else 0, 0)
		
		# Press main key down
		winUser.keybd_event(vkCode, 0, 1 if extended else 0, 0)
		
		# Release main key
		winUser.keybd_event(vkCode, 0, (1 if extended else 0) | 2, 0)
		
		# Release modifiers in reverse order
		for modVk, modExt in reversed(modifiers):
			winUser.keybd_event(modVk, 0, (1 if modExt else 0) | 2, 0)
		
		log.debug(f"emulateGestureWithVK: Successfully sent keys for {char!r}")
	except Exception as e:
		log.error(f"emulateGestureWithVK failed for char={char!r}: {e}", exc_info=True)


def emulateTabKeyPress(withShift: bool = False) -> None:
	"""
	Emulates a Tab or Shift+Tab key press using keybd_event for maximum compatibility.
	This is specifically designed to work with wx dialogs where the shift modifier
	may no longer be physically pressed (e.g., with Perkins braille keyboard firmware).
	
	Uses keybd_event() instead of SendInput() because it works better with wx dialogs
	when the original key modifier is no longer physically held down.
	
	Args:
		withShift (bool): If True, emulates Shift+Tab; if False, emulates Tab
	"""
	try:
		log.debug(f"emulateTabKeyPress: withShift={withShift}")
		
		# Use ignoreInjection context manager to prevent NVDA from capturing
		# the injected keys and causing an infinite loop
		with keyboardHandler.ignoreInjection():
			# Press shift down if needed
			if withShift:
				winUser.keybd_event(winUser.VK_SHIFT, 0, 0, 0)
			
			# Press Tab down
			winUser.keybd_event(winUser.VK_TAB, 0, 0, 0)
			
			# Release Tab
			winUser.keybd_event(winUser.VK_TAB, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
			
			# Release shift if it was pressed
			if withShift:
				winUser.keybd_event(winUser.VK_SHIFT, 0, 2, 0)
	except Exception as e:
		log.error(f"emulateTabKeyPress failed: {e}")


def loadLocaleGestureFromCommandNameMap(self) -> None:
	"""Load the locale-specific gesture map from configuration files.
	
	For regional variants (e.g., fr_CA, en_GB), this loads the base language file first (fr, en)
	and then overlays the regional variant file, allowing fallback for commands not defined
	in the regional variant.
	"""
	self.localeGestureFromCommandNameMap.clear()
	lang = languageHandler.getLanguage()
	
	# Check if this is a regional variant (contains underscore)
	if "_" in lang:
		baseLang = lang.split("_")[0]
		# First, try to load the base language file
		try:
			basePath = os.path.join(globalVars.appDir, "locale", baseLang, "gesturesFromCommandName.ini")
			self.localeGestureFromCommandNameMap.load(basePath)
			log.debug("Loaded base gesture map for language: %s" % baseLang)
		except IOError:
			log.debugWarning("No base gesture map for language %s" % baseLang)
		
		# Then, try to load the regional variant file (will override base language commands)
		try:
			regionalPath = os.path.join(globalVars.appDir, "locale", lang, "gesturesFromCommandName.ini")
			self.localeGestureFromCommandNameMap.load(regionalPath)
			log.debug("Loaded regional gesture map for language: %s" % lang)
		except IOError:
			log.debug("No regional gesture map for language %s, using base language only" % lang)
	else:
		# Not a regional variant, just load the language file
		try:
			self.localeGestureFromCommandNameMap.load(
				os.path.join(globalVars.appDir, "locale", lang, "gesturesFromCommandName.ini")
			)
			log.debug("Loaded gesture map for language: %s" % lang)
		except IOError:
			log.debugWarning("No locale gesture map for language %s" % lang)


def getNvdaModifierKey(self) -> str:
	"""
	Get the current NVDA modifier key setting.
	
	Returns:
		str: "insert", "capslock", or "insert" as default
	"""
	if (keyboardHandler.isNVDAModifierKey(winUser.VK_INSERT, False) or
		keyboardHandler.isNVDAModifierKey(winUser.VK_INSERT, True)):
		return "insert"
	elif keyboardHandler.isNVDAModifierKey(winUser.VK_CAPITAL, False):
		return "capslock"

	return "insert"

class GlobalGestureCommandNameMap(inputCore.GlobalGestureMap):
	def add(
		self,
		gesture: str,
		module: str,
		className: str,
		script: Optional[ScriptNameT],
		replace: bool = False,
	):
		# For regional locale fallback: remove any existing bindings for this command
		# before adding the new one (e.g., fr_CA overriding fr)
		if not replace:
			# Search all gestures for this command and remove them
			for existingGesture, existingScripts in list(self._map.items()):
				self._map[existingGesture] = [
					(m, c, s) for (m, c, s) in existingScripts
					if not (m == module and c == className and s == script)
				]
				# Clean up empty gesture entries
				if not self._map[existingGesture]:
					del self._map[existingGesture]
		
		try:
			scripts = self._map[gesture]
		except KeyError:
			scripts = self._map[gesture] = []
		if replace:
			del scripts[:]
		scripts.append((module, className, script))
