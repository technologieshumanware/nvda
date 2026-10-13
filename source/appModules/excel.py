# This file was modified for the BrailleNote evolve
# Technologies Humanware 2026

# -*- coding: UTF-8 -*-
# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2018-2025 NV Access Limited, Łukasz Golonka
# This file may be used under the terms of the GNU General Public License, version 2 or later.
# For more details see: https://www.gnu.org/licenses/gpl-2.0.html

import time
import config
import eventHandler
import core
import api
import UIAHandler
from NVDAObjects import NVDAObject
from NVDAObjects.UIA import UIA
import winUser
import controlTypes
import appModuleHandler
from scriptHandler import script
from NVDAObjects.window import DisplayModelEditableText
from NVDAObjects.window.edit import UnidentifiedEdit
from NVDAObjects.window import Window
from NVDAObjects.IAccessible import IAccessible
from appModules import humanware
from scriptHandler import script
from logHandler import log


class Excel6(Window):
	"""
	The Excel cell edit window.
	If it is not accessible (no displayModel) then wait for the CellEdit UIA element to get focus and redirect to that.
	"""

	def _get_focusRedirect(self):
		if self.role == controlTypes.Role.UNKNOWN:
			# The control is inaccessible, try several times to find the CellEdit UIA element with focus and use that instead.
			for count in range(10):
				if count >= 1:
					api.processPendingEvents(processEventQueue=False)
					if eventHandler.isPendingEvents("gainFocus"):
						return
					time.sleep(0.05)
				e = UIAHandler.handler.lastFocusedUIAElement
				if e and e.cachedAutomationID == "CellEdit":
					obj = UIA(UIAElement=e)
					# Set the UIA edit control's parent to the parent of self.
					# otherwise a whole bunch of UIA focus ancestors for the edit control will be reported.
					obj.parent = self.parent
					# Cache this for as long as this object exists.
					self.focusRedirect = obj
					return obj


class Excel6_WhenUIAEnabled(IAccessible):
	"""
	#12303: When accessing Microsoft Excel via UI Automation
	MSAA focus events on the old formula edit window should be completely ignored.
	UI Automation will fire its own ones.
	"""

	shouldAllowIAccessibleFocusEvent = False


class BrokenDataValidationSysListView32(UIA):
	"""
	#15138: Broken data validation SysListView32 control in Excel.
	If a cell has a data validation type of list, the dropdown list shown when pressing alt+down arrow is not accessible.
	IAccessibleObjectFromEvent fails for all focus winEvents (most likely proxied from a broken UIA implementation).
	Even when this appModule treats this window as native UIA,
	the parent chain loops between the SysListView32 and the `__XLACOOUTER` window causing a never ending focus ancestry.
	Therefore, this class is used to override the parent of the SysListView32 control to go straight to the desktop.
	"""

	@classmethod
	def windowMatches(cls, hwnd: int) -> bool:
		"""Identifies if the given window is a broken data validation SysListView32 control."""
		if winUser.getClassName(hwnd) == "SysListView32":
			parentHwnd = winUser.getAncestor(hwnd, winUser.GA_PARENT)
			if winUser.getClassName(parentHwnd) == "__XLACOOUTER":
				return True
		return False

	@classmethod
	def matchesNVDAObject(cls, obj: NVDAObject) -> bool:
		"""Identifies if the given NVDAObject is a broken data validation SysListView32 control."""
		if isinstance(obj, UIA) and obj.UIAIsWindowElement and cls.windowMatches(obj.windowHandle):
			return True
		return False

	def _get_parent(self) -> NVDAObject:
		return api.getDesktopObject()

	def _correctFocus(self):
		eventHandler.queueEvent("gainFocus", NVDAObject.objectWithFocus())

	@script(
		gestures=["kb:enter", "kb:space", "kb:escape"],
		canPropagate=True,
	)
	def script_close(self, gesture):
		"""Correct focus when the user presses Enter, Space or Escape."""
		gesture.send()
		core.callLater(100, self._correctFocus)


class AppModule(appModuleHandler.AppModule):
	def isGoodUIAWindow(self, hwnd: int) -> bool:
		if BrokenDataValidationSysListView32.windowMatches(hwnd):
			# #15138: Broken data validation SysListView32 control in Excel.
			# If a cell has a data validation type of list, the dropdown list shown when pressing alt+down arrow is not accessible.
			# IAccessibleObjectFromEvent fails for all focus winEvents (most likely proxied from a broken UIA implementation).
			# Therefore treat this window as native UIA.
			return True
		windowClass = winUser.getClassName(hwnd)
		versionMajor = int(self.productVersion.split(".")[0])
		if versionMajor >= 16 and windowClass == "RICHEDIT60W":
			# RICHEDIT60W In Excel 2016+ on Windows 10+
			# has a very good UI Automation implementation,
			# Though oddly IsServerSideProvider returns false for these windows.
			# Examples: Password field in the Protect sheet dialog.
			return True
		return False

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if BrokenDataValidationSysListView32.matchesNVDAObject(obj):
			clsList.insert(0, BrokenDataValidationSysListView32)
			return
		windowClass = obj.windowClassName
		# #9042: Edit fields in Excel have to be accessed via displayModel.
		if windowClass == "EDTBX":
			try:
				clsList.remove(UnidentifiedEdit)
			except ValueError:
				pass
			clsList.insert(0, DisplayModelEditableText)
		if windowClass == "EXCEL6":
			if config.conf["UIA"]["useInMSExcelWhenAvailable"]:
				# #12303: When accessing Microsoft Excel via UI Automation
				# MSAA focus events on the old formula edit window should be completely ignored.
				# UI Automation will fire its own ones.
				clsList.insert(0, Excel6_WhenUIAEnabled)
			else:
				# #12303: The old Formula Edit window in recent versions of Excel
				# may not be accessible with display models as GDI is no longer used.
				# However, UI Automation does expose an accessible edit control within the active cell,
				# So use a class that will redirect focus to that.
				clsList.insert(0, Excel6)

	# HumanWare section

	@script(
		description=_("New file"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot7"	# Backspace+N
	)
	def script_braille_newFile(self, gesture):
		self.emulateKeyPressFromCommandName("new")

	@script(
		description=_("Open file"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot5+dot7"	# Backspace+O
	)
	def script_braille_openFile(self, gesture):
		self.emulateKeyPressFromCommandName("open")

	@script(
		# Translators: Input Help message for the close file command.
		description=_("Close file"),
		gesture="br(hidBrailleStandard):space+dot2+dot4+dot5+dot6"	# Space+W
	)
	def script_braille_closeFile(self, gesture):
		self.emulateKeyPressFromCommandName("close")

	@script(
		# Translators: Input Help message for the info command.
		description=_("Info"),
		gestures=(
			"br(hidBrailleStandard):space+dot2+dot4", # Space+I
			"kb:control+shift+i")	 		          # Ctrl+Shift+I
	)
	def script_braille_info(self, gesture):
		time.sleep(0.5)
		# Use the locale-specific key sequence from gesturesFromCommandName.ini
		# English: "alt,f,i" / German: "alt,d,i"
		humanware.emulateKeySequenceFromCommandName(self, "openFileInfoKeys")

	@script(
		description=_("Open menu list"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A
	)
	def script_braille_openMenuList(self, gesture):
		time.sleep(0.5)
		focus = api.getFocusObject()
		# Add extra delay after Alt if focus is in a content area (cell, editable text, document)
		# so the ribbon can activate before the subsequent menu keystrokes are sent.
		delayAfterAlt = 0.5 if focus and focus.role in (
			controlTypes.Role.TABLECELL,
			controlTypes.Role.EDITABLETEXT,
			controlTypes.Role.DOCUMENT,
		) else 0.0
		humanware.emulateKeySequenceFromCommandName(self, "openMenuListKeys", delayAfterAlt=delayAfterAlt)

	@script(
		description=_("Find"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4"	# Space+F
	)
	def script_braille_find(self, gesture):
		self.emulateKeyPressFromCommandName("find")

	@script(
		description=_("Find previous"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"	# Space+P
	)
	def script_braille_findPrevious(self, gesture):
		self.emulateKeyPressFromCommandName("findPrevious")

	@script(
		description=_("Find next"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"	# Space+N
	)
	def script_braille_findNext(self, gesture):
		# In the HumanWare custom "Save As" dialog, Space+N must create a new folder
		# instead of finding the next search result.
		if humanware.isInHumanWareSaveAsDialog():
			self.emulateKeyPressFromCommandName("new")
		else:
			self.emulateKeyPressFromCommandName("findNext")

	@script(
		description=_("Replace"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"	# Backspace+F
	)
	def script_braille_replace(self, gesture):
		self.emulateKeyPressFromCommandName("replace")

	@script(
		description=_("Insert hyperlink"),
		gesture="br(hidBrailleStandard):space+dot1+dot3"	# Space+K
	)
	def script_braille_insertHyperlink(self, gesture):
		self.emulateKeyPressFromCommandName("insertHyperlink")

	@script(
		# Translators: Input Help message for the edit current cell command.
		description=_("Edit current cell"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot7"), # Backspace+E
	)
	def script_braille_editCurrentCell(self, gesture):
		self.emulateKeyPressFromCommandName("editCurrentCell")

	@script(
		# Translators: Input Help message for the go to command.
		description=_("Go To"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot5+dot8"), # Enter+G
	)
	def script_braille_goTo(self, gesture):
		self.emulateKeyPressFromCommandName("goTo")

	@script(
		description=_("Bold"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot8"	# Enter+B
	)
	def script_braille_bold(self, gesture):
		kbIdentifier = humanware.getShortcutFromCommandNameAndAppModuleName(self, "bold", "excel")
		humanware.emulateGesture(kbIdentifier)

	@script(
		description=_("Italics"),
		gesture="br(hidBrailleStandard):space+dot2+dot4+dot8"	# Enter+I
	)
	def script_braille_italics(self, gesture):
		kbIdentifier = humanware.getShortcutFromCommandNameAndAppModuleName(self, "italics", "excel")
		humanware.emulateGesture(kbIdentifier)

	@script(
		description=_("Underline"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot6+dot8"	# Enter+U
	)
	def script_braille_underline(self, gesture):
		kbIdentifier = humanware.getShortcutFromCommandNameAndAppModuleName(self, "underline", "excel")
		humanware.emulateGesture(kbIdentifier)

	@script(
		description=_("Open font dialog"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot8"	# Enter+F
	)
	def script_braille_openFontDialog(self, gesture):
		self.emulateKeyPressFromCommandName("openFontDialog")

	@script(
		# Translators: Input Help message for the previous sheet command.
		description=_("Previous sheet"),
		gesture="br(hidBrailleStandard):space+dot2+dot3"  # Space+2+3
	)
	def script_braille_previousSheet(self, gesture):
		self.emulateKeyPressFromCommandName("previousSheet")
		core.callLater(100, self._correctFocus)

	@script(
		# Translators: Input Help message for the next sheet command.
		description=_("Next sheet"),
		gesture="br(hidBrailleStandard):space+dot5+dot6"  # Space+5+6
	)
	def script_braille_nextSheet(self, gesture):
		self.emulateKeyPressFromCommandName("nextSheet")
		core.callLater(100, self._correctFocus)

	def emulateKeyPressFromCommandName(self, commandName):
		humanware.emulateKeyPressFromCommandNameAndAppModuleName(self, commandName, "excel")

	def _correctFocus(self):
		"""Queue a focus event to ensure the current object is announced."""
		api.processPendingEvents(processEventQueue=True)
		eventHandler.queueEvent("gainFocus", NVDAObject.objectWithFocus())

	# HumanWare section end
