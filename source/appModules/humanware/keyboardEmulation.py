# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Keyboard emulation utilities for Humanware devices.

Provides functions to emulate keyboard input, including individual keys,
key sequences, and special handling for Arabic layouts.
"""

import time

import inputCore
import keyboardHandler
import languageHandler
import winUser
from keyboardHandler import KeyboardInputGesture
from logHandler import log
from winBindings import user32 as winBindings_user32

from . import _arabicKeyboardEmulation
from .gestureConfig import getShortcutFromCommandName, getShortcutFromCommandNameAndAppModuleName, getConfigValueFromGestureIni


def _sendUnicodeChar(char: str) -> None:
	"""Send a single Unicode character using SendInput with KEYEVENTF.UNICODE.
	
	This is used for Arabic characters that cannot be sent via KeyboardInputGesture.
	
	Args:
		char (str): Single Unicode character to send
	"""
	try:
		log.debug(f"_sendUnicodeChar: Sending Unicode char: {char!r} (U+{ord(char):04X})")
		
		inputs = []
		with keyboardHandler.ignoreInjection():
			# Press and release the character
			for direction in (0, winBindings_user32.KEYEVENTF.KEYUP):
				input_struct = winBindings_user32.INPUT()
				input_struct.type = winBindings_user32.INPUT_TYPE.KEYBOARD
				input_struct.ii.ki = winBindings_user32.KEYBDINPUT()
				input_struct.ii.ki.wScan = ord(char)
				input_struct.ii.ki.dwFlags = winBindings_user32.KEYEVENTF.UNICODE | direction
				inputs.append(input_struct)
			winUser.SendInput(inputs)
	except Exception as e:
		log.error(f"_sendUnicodeChar failed for {char!r}: {e}")


def _isArabicLayout() -> bool:
	"""Check if the current keyboard layout is Arabic.
	
	Returns:
		bool: True if the current layout is Arabic (ar, ar_SA, ar_EG, etc.)
	"""
	lang = languageHandler.getLanguage()
	return lang.startswith("ar")


def emulateKeyPress(kbIdentifier: str) -> None:
	"""
	Emulates a keyboard press using the specified identifier.
	
	Args:
		kbIdentifier (str): Keyboard identifier (e.g., "alt+f", "ctrl+c")
	"""
	if not kbIdentifier or not isinstance(kbIdentifier, str):
		log.error("emulateKeyPress: Invalid keyboard identifier: %r" % kbIdentifier)
		return
	
	# For Arabic keyboard layout, handle both Arabic characters and Latin keys
	if _isArabicLayout():
		# Check if this is an Arabic character (single character in Arabic Unicode range)
		# Arabic characters: U+0600 to U+06FF
		isArabicChar = (len(kbIdentifier) == 1 and '\u0600' <= kbIdentifier <= '\u06FF')
		
		if isArabicChar:
			# For Arabic characters, use Unicode input method
			log.debug("emulateKeyPress: Sending Arabic character via Unicode: %s" % kbIdentifier)
			_sendUnicodeChar(kbIdentifier)
		else:
			# For non-Arabic characters on Arabic layout, use VK codes
			# This ensures Latin characters are sent via VK codes (e.g., 'h' sends VK_H)
			log.debug("emulateKeyPress: Using VK codes for Arabic layout: %s" % kbIdentifier)
			_arabicKeyboardEmulation.parseAndEmulateGestureWithVK(kbIdentifier)
		return
	
	# For non-Arabic layouts, use standard method
	try:
		log.debug("emulateKeyPress: %s" % kbIdentifier)
		# Note: gesture.send() already uses ignoreInjection() internally
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
	
	# For Arabic keyboard layout, handle both Arabic characters and Latin keys
	if _isArabicLayout():
		# Check if this is an Arabic character (single character in Arabic Unicode range)
		# Arabic characters: U+0600 to U+06FF
		isArabicChar = (len(kbIdentifier) == 1 and '\u0600' <= kbIdentifier <= '\u06FF')
		
		if isArabicChar:
			# For Arabic characters, use Unicode input method
			log.debug("emulateGesture: Sending Arabic character via Unicode: %s" % kbIdentifier)
			_sendUnicodeChar(kbIdentifier)
		else:
			# For non-Arabic characters on Arabic layout, use VK codes
			# This ensures Latin characters are sent via VK codes (e.g., 'h' sends VK_H)
			log.debug("emulateGesture: Using VK codes for Arabic layout: %s" % kbIdentifier)
			_arabicKeyboardEmulation.parseAndEmulateGestureWithVK(kbIdentifier)
		return
	
	# For non-Arabic layouts, use standard method
	try:
		# Note: emulateGesture() will internally use send() which already uses ignoreInjection()
		gesture = KeyboardInputGesture.fromName(kbIdentifier)
		inputCore.manager.emulateGesture(gesture)
	except Exception as e:
		log.error("emulateGesture failed for %s: %s" % (kbIdentifier, e))


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


def emulateAltKeyPress() -> None:
	"""
	Emulates a single Alt key press using keybd_event.
	
	This is specifically designed to activate the menu bar without blocking.
	Using KeyboardInputGesture.fromName("alt") would put the application in 
	menu mode and wait for the next key, causing NVDA to freeze.
	"""
	try:
		log.info("emulateAltKeyPress: Sending Alt key press/release")
		
		# Use ignoreInjection to prevent NVDA from capturing the injected keys
		with keyboardHandler.ignoreInjection():
			# Press Alt down
			winUser.keybd_event(winUser.VK_MENU, 0, 0, 0)  # VK_MENU = Alt
			
			# Release Alt immediately
			winUser.keybd_event(winUser.VK_MENU, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
	except Exception as e:
		log.error(f"emulateAltKeyPress failed: {e}")


def emulateKeySequence(keySequence: str, delay: float = 0.0, delayAfterAlt: float = 0.0) -> None:
	"""
	Emulates a sequence of key presses from a comma-separated string.
	
	This is useful for navigating menus where the key sequence differs by language.
	For example:
	- English Word: "alt,m,l" (Alt, then M, then L)
	- German Word: "alt,y,2,l" (Alt, then Y, then 2, then L)
	
	Args:
		keySequence (str): Comma-separated list of keys (e.g., "alt,y,2,l")
		delay (float): Delay in seconds between each key press (default: 0.0)
		delayAfterAlt (float): Additional delay after pressing 'alt' key (default: 0.0)
	"""
	if not keySequence or not isinstance(keySequence, str):
		log.error("emulateKeySequence: Invalid key sequence: %r" % keySequence)
		return
	
	try:
		# Parse the sequence by splitting on commas and removing whitespace
		keys = [key.strip() for key in keySequence.split(",") if key.strip()]
		
		if not keys:
			log.error("emulateKeySequence: No keys found in sequence: %r" % keySequence)
			return
		
		log.info(f"emulateKeySequence: Starting sequence with {len(keys)} keys: {keys}, delay={delay}, delayAfterAlt={delayAfterAlt}")
		
		# Execute each key in sequence with a delay between them
		for i, key in enumerate(keys):
			log.info(f"emulateKeySequence: Pressing key {i+1}/{len(keys)}: '{key}'")
			
			# Special handling for "alt" key to avoid blocking
			if key.lower() == "alt":
				emulateAltKeyPress()
			else:
				emulateKeyPress(key)
			
			# Add delay between keys (but not after the last key)
			if i < len(keys) - 1:
				# Add extra delay after 'alt' key if specified
				if key.lower() == "alt" and delayAfterAlt > 0:
					log.info(f"emulateKeySequence: Sleeping {delayAfterAlt}s after Alt")
					time.sleep(delayAfterAlt)
				elif delay > 0:
					log.info(f"emulateKeySequence: Sleeping {delay}s between keys")
					time.sleep(delay)
				
		log.info(f"emulateKeySequence: Completed sequence: {keySequence}")
		
	except Exception as e:
		log.error(f"emulateKeySequence failed for '{keySequence}': {e}", exc_info=True)


def emulateKeySequenceFromCommandName(self, commandName: str, delay: float = 0.0, delayAfterAlt: float = 0.0) -> None:
	"""
	Emulate a key sequence from gesturesFromCommandName.ini.
	
	Reads a comma-separated key sequence (e.g., "alt,m,l") and executes each key.
	
	Args:
		commandName (str): Name of the command in the .ini file (e.g., "openMenuListKeys")
		delay (float): Delay in seconds between each key press (default: 0.0)
		delayAfterAlt (float): Additional delay after pressing 'alt' key (default: 0.0)
	"""
	log.info(f"emulateKeySequenceFromCommandName: Looking for '{commandName}' with delay={delay}, delayAfterAlt={delayAfterAlt}")
	keySequence = getConfigValueFromGestureIni(self, commandName)
	log.info(f"emulateKeySequenceFromCommandName: Found key sequence: '{keySequence}'")
	if keySequence:
		emulateKeySequence(keySequence, delay, delayAfterAlt)
	else:
		log.error(f"emulateKeySequenceFromCommandName: No value found for '{commandName}'")
