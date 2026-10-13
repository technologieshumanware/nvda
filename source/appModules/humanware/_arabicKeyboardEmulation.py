# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Arabic keyboard layout support utilities.

This module provides Virtual Key (VK) code-based keyboard emulation
for Arabic keyboard layouts, where character-based shortcuts may fail.
"""

# NVDA imports
import keyboardHandler
import winUser
from logHandler import log


# Virtual Key Code constants for keyboard layout independence
# These represent physical key positions, not characters
virtualKeys = {
	'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45,
	'F': 0x46, 'G': 0x47, 'H': 0x48, 'I': 0x49, 'J': 0x4A,
	'K': 0x4B, 'L': 0x4C, 'M': 0x4D, 'N': 0x4E, 'O': 0x4F,
	'P': 0x50, 'Q': 0x51, 'R': 0x52, 'S': 0x53, 'T': 0x54,
	'U': 0x55, 'V': 0x56, 'W': 0x57, 'X': 0x58, 'Y': 0x59,
	'Z': 0x5A,
}

vkMap = {
	"pageup": winUser.VK_PRIOR,
	"pagedown": winUser.VK_NEXT,
	"home": winUser.VK_HOME,
	"end": winUser.VK_END,
	"insert": winUser.VK_INSERT,
	"space": winUser.VK_SPACE,
	"tab": winUser.VK_TAB,
	"enter": winUser.VK_RETURN,
	"escape": winUser.VK_ESCAPE,
	"delete": winUser.VK_DELETE,
	"backspace": winUser.VK_BACK,
	"uparrow": winUser.VK_UP,
	"downarrow": winUser.VK_DOWN,
	"leftarrow": winUser.VK_LEFT,
	"rightarrow": winUser.VK_RIGHT,
}

# Keys that require the extended key flag (KEYEVENTF_EXTENDEDKEY)
# These are navigation keys on the extended keypad and some special keys
# Regular keys like tab, space, enter, escape, backspace do NOT need this flag
extendedKeys = {
	"pageup", "pagedown", "home", "end", "insert", "delete",
	"uparrow", "downarrow", "leftarrow", "rightarrow"
}


def _getNvdaModifierKey() -> str:
	"""Get the current NVDA modifier key setting.
	
	Returns:
		str: "insert", "capslock", or "insert" as default
	"""
	if (keyboardHandler.isNVDAModifierKey(winUser.VK_INSERT, False) or
		keyboardHandler.isNVDAModifierKey(winUser.VK_INSERT, True)):
		return "insert"
	elif keyboardHandler.isNVDAModifierKey(winUser.VK_CAPITAL, False):
		return "capslock"
	
	return "insert"


def parseModifiers(parts: list) -> list:
	"""Parse modifier keys from keyboard identifier parts.
	
	Args:
		parts (list): List of modifier strings (e.g., ['control', 'shift', 'windows'])
		
	Returns:
		list: List of tuples [(vk_code, extended), ...]
	"""
	modifiers = []
	for part in parts:
		part = part.strip()
		if part == "control" or part == "ctrl":
			modifiers.append((winUser.VK_CONTROL, False))
		elif part == "alt":
			modifiers.append((winUser.VK_MENU, False))
		elif part == "shift":
			modifiers.append((winUser.VK_SHIFT, False))
		elif part == "windows" or part == "leftwindows":
			# Use left Windows key (VK_LWIN = 0x5B)
			modifiers.append((winUser.VK_LWIN, True))
		elif part == "nvda":
			# Detect which key is configured as NVDA modifier
			nvdaKey = _getNvdaModifierKey()
			if nvdaKey == "insert":
				modifiers.append((winUser.VK_INSERT, False))
			elif nvdaKey == "capslock":
				modifiers.append((winUser.VK_CAPITAL, False))
		else:
			log.warning(f"parseModifiers: Unknown modifier: {part}")
	return modifiers


def emulateKeyWithModifiers(vkCode: int, modifiers: list, extended: bool = False) -> None:
	"""Emulate a key press with modifiers using VK codes.
	
	Args:
		vkCode (int): Virtual key code to press
		modifiers (list): List of modifier tuples [(vk, extended), ...]
		extended (bool): Whether the main key is an extended key
	"""
	try:
		# Use ignoreInjection to prevent NVDA from capturing the injected keys
		with keyboardHandler.ignoreInjection():
			# Press modifiers down
			for modVk, modExt in modifiers:
				winUser.keybd_event(modVk, 0, 1 if modExt else 0, 0)

			# Press and release main key
			winUser.keybd_event(vkCode, 0, 1 if extended else 0, 0)
			winUser.keybd_event(vkCode, 0, (1 if extended else 0) | 2, 0)

			# Release modifiers in reverse order
			for modVk, modExt in reversed(modifiers):
				winUser.keybd_event(modVk, 0, (1 if modExt else 0) | 2, 0)
	except Exception as e:
		log.error(f"emulateKeyWithModifiers: Failed to emulate key 0x{vkCode:02X}: {e}")


def emulateFunctionKey(mainKey: str, modifiers: list) -> bool:
	"""Emulate a function key (F1-F12) press.
	
	Args:
		mainKey (str): Function key string (e.g., "f1", "f12")
		modifiers (list): List of modifier tuples
		
	Returns:
		bool: True if successfully handled, False otherwise
	"""
	try:
		fNumber = int(mainKey[1:])
		if 1 <= fNumber <= 12:
			vkCode = winUser.VK_F1 + (fNumber - 1)
			emulateKeyWithModifiers(vkCode, modifiers, extended=False)
			return True
		else:
			log.error(f"emulateFunctionKey: Invalid function key number: {fNumber}")
			return False
	except (ValueError, AttributeError) as e:
		log.error(f"emulateFunctionKey: Failed to parse function key: {mainKey}, {e}")
		return False


def emulateGestureWithVK(char: str, modifiers: list = [], extended: bool = False) -> None:
	"""Emulates a gesture using virtual key codes, independent of keyboard layout.
	
	This is useful for non-QWERTY keyboard layouts where character-based gestures may fail.
	
	Args:
		char (str): Character representing the main key (e.g., 'G', 'O', 'H')
		modifiers (list): List of modifier tuples [(vk, extended), ...], e.g., [(winUser.VK_CONTROL, False)]
		extended (bool): Whether the main key is an extended key
		
	Example:
		# Emulate Ctrl+Alt+O (independent of keyboard layout)
		emulateGestureWithVK('O', [(winUser.VK_CONTROL, False), (winUser.VK_MENU, False)])
	"""
	# Convert character to uppercase for consistency
	char = char.upper()

	# Get VK code from virtualKeys dictionary
	if char not in virtualKeys:
		log.error(f"emulateGestureWithVK: Unsupported character: {char!r}")
		return

	vkCode = virtualKeys[char]
	log.debug(f"emulateGestureWithVK: char={char!r}, vkCode=0x{vkCode:02X} ({vkCode}), modifiers={modifiers}, extended={extended}")

	# Use the shared function to emulate the key press
	emulateKeyWithModifiers(vkCode, modifiers, extended)

	log.debug(f"emulateGestureWithVK: Successfully sent keys for {char!r}")


def parseAndEmulateGestureWithVK(kbIdentifier: str) -> None:
	"""Parse a keyboard identifier string and emulate it using VK codes.
	
	Args:
		kbIdentifier (str): Keyboard identifier string (e.g., "control+w", "shift+f4", "nvda+i")
	"""
	if not kbIdentifier:
		log.error(f"parseAndEmulateGestureWithVK: No shortcut found for kbIdentifier: {kbIdentifier}")
		return

	# Parse the keyboard identifier
	parts = kbIdentifier.lower().split('+')
	if not parts:
		log.error(f"parseAndEmulateGestureWithVK: Invalid keyboard identifier: {kbIdentifier}")
		return

	mainKey = parts[-1].strip()
	modifiers = parseModifiers(parts[:-1])

	# Handle different key types
	if mainKey.upper() in virtualKeys:
		# Letter key (A-Z)
		emulateGestureWithVK(mainKey, modifiers)
	elif mainKey.startswith("f") and len(mainKey) <= 3:
		# Function keys (F1-F12)
		if not emulateFunctionKey(mainKey, modifiers):
			log.error(f"parseAndEmulateGestureWithVK: Failed to handle function key: {mainKey}")
	elif mainKey in vkMap:
		# Special keys (space, pageup, pagedown, home, end, tab, enter, escape, delete, backspace)
		vkCode = vkMap[mainKey]
		extended = mainKey in extendedKeys
		emulateKeyWithModifiers(vkCode, modifiers, extended=extended)
	else:
		# Try single letter
		if len(mainKey) == 1 and mainKey.isalpha():
			emulateGestureWithVK(mainKey, modifiers)
		else:
			log.error(f"parseAndEmulateGestureWithVK: Unsupported key: {mainKey}")
