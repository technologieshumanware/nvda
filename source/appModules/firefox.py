# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# FireFox App Module for NVDA

import appModuleHandler
import appModules.HWUtils
import api
import controlTypes
import brailleInput
from logHandler import log
from NVDAObjects import NVDAObject
from typing import Callable

from scriptHandler import script

class AppModule(appModuleHandler.AppModule):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		log.info("Firefox: Initialized with passive IME approach")

	def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable[[], None]):
		"""Analyze context and tell IME whether to enable translation.

		IME waits for explicit permission before translating.
		"""
		# Determine if this is a safe context
		isSafe = self._isSafeEditField(obj)

		# Enhanced logging for debugging
		log.debug(f"Firefox gainFocus: isSafe={isSafe}, role={obj.role}, name={obj.name}")
		log.debug(f"Firefox gainFocus: states={obj.states}, class={getattr(obj, 'windowClassName', 'N/A')}")
		try:
			if hasattr(obj, 'IA2Attributes'):
				log.debug(f"Firefox gainFocus: IA2Attributes={dict(obj.IA2Attributes)}")
		except:
			log.debug("Firefox gainFocus: Could not read IA2Attributes")

		# Send permission/block message to IME
		if isSafe:
			log.debug("Firefox: Sending BRLUCX_enabled to IME")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(True)
		else:
			reason = self._getBlockReason(obj)
			log.debug(f"Firefox: Sending BRLUCX_disabled to IME (reason: {reason})")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(False)

		nextHandler()

	def _supportsBRLUCX(self) -> bool:
		"""Check if current context supports BRLUCX."""
		return self._isSafeEditField(api.getFocusObject())

	def _isSafeEditField(self, obj: NVDAObject) -> bool:
		"""Determine if field is safe for IME translation.

		Returns True only for regular text inputs on web pages.
		Blocks: URL bars, combo boxes, password fields, search boxes.
		"""
		try:
			# First check for web form fields via IA2Attributes (before role check)
			# This is critical because textareas might have different roles
			try:
				if hasattr(obj, 'IA2Attributes'):
					ia2Attrs = obj.IA2Attributes

					# Check if it's a web form input or textarea
					isInput = 'tag:input' in ia2Attrs
					isTextarea = 'tag:textarea' in ia2Attrs

					if isTextarea:
						# Textareas are always safe (multi-line text)
						log.debug("Firefox: Detected textarea via IA2Attributes")
						return True

					if isInput:
						# Block autocomplete/combobox inputs
						if 'autocomplete:both' in ia2Attrs or 'xml-roles:combobox' in ia2Attrs:
							log.debug("Firefox: Blocking input with autocomplete")
							return False
						# Regular input is safe
						log.debug("Firefox: Detected regular input via IA2Attributes")
						return True
			except Exception as e:
				log.debug(f"Firefox: Error checking IA2Attributes: {e}")

			# Check if editable (might not be EDITABLETEXT role for textareas)
			if controlTypes.State.EDITABLE not in obj.states and controlTypes.State.FOCUSABLE not in obj.states:
				log.debug(f"Firefox: Not editable states={obj.states}")
				return False

			# Block password fields by state
			if controlTypes.State.PROTECTED in obj.states:
				log.debug("Firefox: Blocking password field (PROTECTED state)")
				return False

			# Block combo boxes by role
			if obj.role == controlTypes.Role.COMBOBOX:
				log.debug("Firefox: Blocking COMBOBOX role")
				return False

			# Block URL bar (check for toolbar parent)
			parent = obj.parent
			while parent:
				if parent.role == controlTypes.Role.TOOLBAR:
					log.debug("Firefox: Blocking toolbar descendant (likely URL bar)")
					return False
				if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
					break
				parent = parent.parent

			# Block search/address fields by name
			if obj.name and any(keyword in obj.name.lower()
			                    for keyword in ['search', 'address', 'url', 'rech']):
				log.debug(f"Firefox: Blocking by name keyword: {obj.name}")
				return False

			# If it has EDITABLETEXT role and passed all checks, allow it
			if obj.role == controlTypes.Role.EDITABLETEXT:
				log.debug("Firefox: Allowing EDITABLETEXT role")
				return True

			# Default: not safe unless verified
			log.debug(f"Firefox: Defaulting to unsafe role={obj.role}")
			return False

		except Exception as e:
			log.debug(f"Firefox: Error checking safe field: {e}")
			return False

	def _getBlockReason(self, obj: NVDAObject) -> str:
		"""Get reason why field is blocked."""
		if obj.role == controlTypes.Role.COMBOBOX:
			return "combo box"
		if obj.role == controlTypes.Role.PASSWORDEDIT:
			return "password field"
		if obj.name and 'search' in obj.name.lower():
			return "search field"
		if obj.name and any(k in obj.name.lower() for k in ['address', 'url']):
			return "URL bar"
		parent = obj.parent
		while parent:
			if parent.role == controlTypes.Role.TOOLBAR:
				return "toolbar (URL bar)"
			if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
				break
			parent = parent.parent
		return "not web form field"



	@script(
		description=_("Back"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot7"),	# Backspace+B -> Alt+leftArrow
	)
	def script_braille_back(self, gesture):
		appModules.HWUtils.emulateKeyPress("alt+leftarrow")

	@script(
		description=_("Forward"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"),	# Backspace+F -> Alt+rightArrow
	)
	def script_braille_forward(self, gesture):
		appModules.HWUtils.emulateKeyPress("alt+rightArrow")

	@script(
		description=_("Select address bar"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot8"),	# Enter+O -> Alt+D
	)
	def script_braille_selectAddressBar(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "firefox_selectAddressBar")

	@script(
		description=_("Manage bookmarks"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot8"),	# Enter+D235 -> Ctrl+Shift+O
	)
	def script_braille_manageBookmarks(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "firefox_manageBookmarks")

	@script(
		description=_("Add bookmark"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot8"),	# Enter+M -> Ctrl+D
	)
	def script_braille_addBookmark(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "firefox_addBookmark")

	@script(
		description=_("Perform a text search on the current page"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space+F -> Ctrl+NVDA+F
	)
	def script_braille_searchOnCurrentPage(self, gesture):
		appModules.HWUtils.emulateGesture("control+nvda+f")

	@script(
		description=_("Find next text search result"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"),	# Space+N -> NVDA+F3
	)
	def script_braille_findNextText(self, gesture):
		appModules.HWUtils.emulateGesture("nvda+f3")

	@script(
		description=_("Find previous text search result"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"),	# Space+P -> NVDA+Shift+F3
	)
	def script_braille_findPreviousText(self, gesture):
		appModules.HWUtils.emulateGesture("nvda+shift+f3")

	@script(
		description=_("Open browser history"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot6+dot8"),	# Enter+D236 -> Ctrl+H
	)
	def script_braille_openBrowserHistory(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "firefox_openBrowserHistory")

	@script(
		description=_("Makes the menu bar appear"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A -> Alt+F
	)
	def script_braille_makesMenuBarAppear(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "firefox_makesMenuBarAppear")

	@script(
		description=_("Open a new window"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot7"),	# Backspace+N -> Ctrl+N
	)
	def script_braille_openNewWindow(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "firefox_openNewWindow")

	@script(
		description=_("Toggle single letter navigation"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7"),	# Backspace+L -> NVDA+Shift+Space
	)
	def script_braille_toggleSingleLetterNavigation(self, gesture):
		appModules.HWUtils.emulateGesture("nvda+shift+space")
