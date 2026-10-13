# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# KeySoftHome App Module for NVDA

import appModuleHandler
import appModules.HWUtils
from scriptHandler import script
from NVDAObjects import NVDAObject
from logHandler import log
import brailleInput
from typing import Callable
import api
import controlTypes

class AppModule(appModuleHandler.AppModule):
	@script(
		description=_("Pin/Unpin Item To Favorites"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot8"), # Enter+M
	)
	def script_braille_pinUnpinItem(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "pinUnpinItem")

	@script(
		description=_("Search"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space + F
	)
	def script_braille_mainMenuSearch(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "mainMenuSearch")


	def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable[[], None]):
		"""Control IME based on focus context.

		For Main Menu: Enable IME only in search bar.
		"""
		# Check if we should enable IME
		shouldEnable = self._shouldEnableIME(obj)

		log.debug(f"keysofthome gainFocus: shouldEnable={shouldEnable}, role={obj.role}, class={obj.__class__.__name__}")

		# Send message to IME
		if shouldEnable:
			log.debug("keysofthome: Sending BRLUCX_enabled to IME")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(True)
		else:
			log.debug(f"keysofthome: Sending BRLUCX_disabled to IME (reason: {obj.role})")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(False)

		nextHandler()

	def _supportsBRLUCX(self) -> bool:
		"""Check if current context supports BRLUCX."""
		return self._shouldEnableIME(api.getFocusObject())



	def _shouldEnableIME(self, obj: NVDAObject) -> bool:
		"""Determine if IME should be enabled for this object.

		In KeySoftHome, only enable for edittext
		"""
		try:
			# Check if in the search bar. (the only editable one in there? Do we need to be more restrictive?)
			if  obj.role == controlTypes.Role.EDITABLETEXT:
				log.debug("keysofthome: Enabling in editable text")
				return True

			# For anything else, disable to be safe
			log.debug(f"keysofthome: Disabling by default (role={obj.role})")
			return False

		except Exception as e:
			log.debug(f"keysofthome: Error checking IME enable: {e}")
			# Disable by default to be safe in keysofthome
			return False
