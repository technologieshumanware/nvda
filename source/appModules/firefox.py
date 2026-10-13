# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# FireFox App Module for NVDA

from appModules.browserBase import BrowserAppModule
import api
import controlTypes
import brailleInput
from logHandler import log
from NVDAObjects import NVDAObject
from typing import Callable

from scriptHandler import script

class AppModule(BrowserAppModule):
	browserName = "firefox"
	
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
