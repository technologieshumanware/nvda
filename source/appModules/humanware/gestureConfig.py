# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Gesture configuration and locale-specific shortcut management.

Handles loading, caching, and retrieving keyboard shortcuts from
locale-specific gesturesFromCommandName.ini files.
"""

import os
from typing import Optional

import configobj

import globalVars
import keyboardHandler
import languageHandler
import winUser
from logHandler import log

from .gestureMap import GlobalGestureCommandNameMap


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
	# Handle both AppModule (has appModuleName) and NVDAObject (has appModule.appModuleName)
	appModuleName = getattr(self, 'appModuleName', None)
	if appModuleName is None and hasattr(self, 'appModule'):
		appModuleName = getattr(self.appModule, 'appModuleName', None)
	
	if appModuleName is None:
		log.error("getShortcutFromCommandName: Cannot determine appModuleName")
		return ""
	
	return getShortcutFromCommandNameAndAppModuleName(self, commandName, appModuleName)


def getConfigValueFromGestureIni(self, commandName: str) -> str:
	"""
	Get a configuration value from gesturesFromCommandName.ini for the current locale.
	
	This reads values directly from the .ini file (e.g., key sequences like "alt,m,l").
	Uses the same locale detection logic as loadLocaleGestureFromCommandNameMap.
	
	Args:
		commandName (str): Name of the command (e.g., "openMenuListKeys")
		
	Returns:
		str: The value from the .ini file, or empty string if not found
	"""
	if not commandName:
		return ""
	
	# Handle both AppModule (has appModuleName) and NVDAObject (has appModule.appModuleName)
	appModuleName = getattr(self, 'appModuleName', None)
	if appModuleName is None and hasattr(self, 'appModule'):
		appModuleName = getattr(self.appModule, 'appModuleName', None)
	
	if appModuleName is None:
		log.error("getConfigValueFromGestureIni: Cannot determine appModuleName")
		return ""
	
	lang = languageHandler.getLanguage()
	sectionName = f"appModules.{appModuleName}"
	
	# Build list of .ini file paths to check (same logic as loadLocaleGestureFromCommandNameMap)
	paths_to_check = []
	if "_" in lang:
		# Regional variant: check regional first, then base language
		baseLang = lang.split("_")[0]
		paths_to_check.append(os.path.join(globalVars.appDir, "locale", lang, "gesturesFromCommandName.ini"))
		paths_to_check.append(os.path.join(globalVars.appDir, "locale", baseLang, "gesturesFromCommandName.ini"))
	else:
		paths_to_check.append(os.path.join(globalVars.appDir, "locale", lang, "gesturesFromCommandName.ini"))
	
	# Try to find the value in the .ini files
	for iniPath in paths_to_check:
		if not os.path.exists(iniPath):
			continue
		try:
			conf = configobj.ConfigObj(iniPath, encoding="UTF-8")
			if sectionName in conf and commandName in conf[sectionName]:
				value = conf[sectionName][commandName]
				# Remove inline comments and quotes
				if "#" in value:
					value = value.split("#")[0]
				return value.strip().strip('"').strip("'")
		except Exception as e:
			log.debug(f"getConfigValueFromGestureIni: Error reading {iniPath}: {e}")
	
	return ""


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
