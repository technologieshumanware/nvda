# This file was modified for the BrailleNote evolve
# Technologies Humanware 2026

# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2022-2025 NV Access Limited, Joseph Lee
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""App module for Windows Notepad.
While this app module also covers older Notepad releases,
this module provides workarounds for Windows 11 Notepad."""

from comtypes import COMError
import appModuleHandler
import api
import braille
import controlTypes
import eventHandler
import speech
import UIAHandler
from logHandler import log
from NVDAObjects.UIA import UIA
from NVDAObjects import NVDAObject
from typing import Callable
import brailleInput
import winUser

class AppModule(appModuleHandler.AppModule):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		log.info("Notepad: Initialized with passive IME approach")

	def event_UIA_elementSelected(self, obj: NVDAObject, nextHandler: Callable[[], None]):
		# Announce currently selected tab when it changes.
		if (
			obj.role == controlTypes.Role.TAB
			# this is done because 2 selection events are sent for the same object, so to prevent double speaking.
			and not eventHandler.isPendingEvents("UIA_elementSelected")
			and controlTypes.State.SELECTED in obj.states
		):
			speech.cancelSpeech()
			speech.speakObject(obj, reason=controlTypes.OutputReason.FOCUS)
			braille.handler.message(
				braille.getPropertiesBraille(
					name=obj.name,
					role=obj.role,
					states=obj.states,
					positionInfo=obj.positionInfo,
				),
			)
		nextHandler()

	def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable[[], None]):
		"""Control IME based on focus context.
		
		For Notepad: Enable in main edit area, disable in dialogs/UI.
		"""
		# Determine if IME should be enabled
		shouldEnable = self._shouldEnableIME(obj)
		
		log.debug(f"Notepad gainFocus: shouldEnable={shouldEnable}, role={obj.role}, windowClass={obj.windowClassName if hasattr(obj, 'windowClassName') else 'N/A'}")
		
		# Always send the appropriate message (not just on state change)
		if shouldEnable:
			log.debug("Notepad: Sending BRLUCX_enabled to IME")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(True)
		else:
			reason = self._getDisableReason(obj)
			log.debug(f"Notepad: Sending BRLUCX_disabled to IME (reason: {reason})")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(False)
		
		nextHandler()
	
	def _shouldEnableIME(self, obj: NVDAObject) -> bool:
		"""Determine if IME should be enabled.
		
		Enable for main Notepad edit field, disable for dialogs and UI elements.
		"""
		try:
			# If in a dialog, disable
			if self._isInDialog(obj):
				return False
			
			# Enable for the main edit field
			# Windows 11 Notepad uses RichEditD2DPT
			if hasattr(obj, 'windowClassName'):
				if obj.windowClassName in ('RichEditD2DPT', 'RichEdit20WPT'):
					log.debug(f"Notepad: Enabling main edit field (class={obj.windowClassName})")
					return True
			
			# Enable for editable text roles
			if obj.role == controlTypes.Role.EDITABLETEXT:
				# The Find toolbar and other XAML UI fields use InputSiteWindowClass
				# but are not the document editor.
				if getattr(obj, 'windowClassName', None) == 'InputSiteWindowClass':
					log.debug("Notepad: Disabling XAML UI field (InputSiteWindowClass)")
					return False
				log.debug("Notepad: Enabling editable text")
				return True
			
			# Check if it's a document role (Notepad editing area)
			if obj.role == controlTypes.Role.DOCUMENT:
				log.debug("Notepad: Enabling document area")
				return True
			
			# Disable for UI elements
			if obj.role in (
				controlTypes.Role.BUTTON,
				controlTypes.Role.MENUITEM,
				controlTypes.Role.MENUBAR,
				controlTypes.Role.TOOLBAR,
				controlTypes.Role.TAB,
			):
				log.debug(f"Notepad: Disabling UI element (role={obj.role})")
				return False
			
			# Default: Enable if it seems like editable content
			log.debug(f"Notepad: Enabling by default (role={obj.role})")
			return True
			
		except Exception as e:
			log.debug(f"Notepad: Error checking IME enable: {e}")
			return True
	
	def _isInDialog(self, obj: NVDAObject) -> bool:
		"""Check if object is within a dialog."""
		# Walk the Win32 HWND chain to the root window and check its class.
		# #32770 is the standard Win32 common dialog class (Save As, Open, etc.).
		try:
			hwnd = getattr(obj, 'windowHandle', None)
			if hwnd:
				root_hwnd = winUser.getAncestor(hwnd, winUser.GA_ROOT)
				if root_hwnd and winUser.getClassName(root_hwnd) == '#32770':
					log.debug("Notepad: Dialog detected via GA_ROOT #32770")
					return True
		except Exception as e:
			log.debug(f"Notepad: GA_ROOT check failed: {e}")

		# NVDA parent chain for in-app dialogs (e.g. Go to line, Find/Replace)
		# where GA_ROOT is the Notepad window itself, not a #32770 frame.
		current = obj
		while current:
			if current.role == controlTypes.Role.DIALOG:
				log.debug("Notepad: Dialog detected via NVDA parent chain (role=DIALOG)")
				return True
			if isinstance(current, UIA) and current.windowClassName in UIAHandler.UIADialogClassNames:
				log.debug("Notepad: Dialog detected via NVDA parent chain (UIADialogClassName)")
				return True
			if current.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
				break
			current = current.parent
		return False
	
	def _getDisableReason(self, obj: NVDAObject) -> str:
		"""Get reason why IME is disabled."""
		if self._isInDialog(obj):
			return "in dialog"
		if obj.role in (controlTypes.Role.BUTTON, controlTypes.Role.MENUITEM, controlTypes.Role.TOOLBAR):
			return f"UI element ({obj.role})"
		return "not edit field"

	def _supportsBRLUCX(self) -> bool:
		"""Check if current context supports BRLUCX."""
		return not self._isInDialog(api.getFocusObject()) 


	def _get_statusBar(self) -> NVDAObject:
		"""Retrieves Windows 11 Notepad status bar.
		In Windows 10 and earlier, status bar can be obtained by looking at the bottom of the screen.
		Windows 11 Notepad uses Windows 11 UI design (top-level window is labeled "DesktopWindowXamlSource",
		therefore status bar cannot be obtained by position alone.
		If visible, a child of the foreground window hosts the status bar elements.
		Status bar child position must be checked whenever Notepad is updated on stable Windows 11 releases
		as Notepad is updated through Microsoft Store as opposed to tied to specific Windows releases.
		L{api.getStatusBar} will resort to position lookup if C{NotImplementedError} is raised.
		"""
		# #13688: Notepad 11 uses Windows 11 user interface, therefore status bar is harder to obtain.
		# This does not affect earlier versions.
		notepadVersion = int(self.productVersion.split(".")[0])
		if notepadVersion < 11:
			raise NotImplementedError()
		# And no, status bar is shown when editing documents.
		# Thankfully, of all the UIA objects encountered, document window has a unique window class name.
		if api.getFocusObject().windowClassName != "RichEditD2DPT":
			raise NotImplementedError()
		# Obtain status bar text across Notepad 11 releases.
		clientObject = UIAHandler.handler.clientObject
		condition = clientObject.createPropertyCondition(
			UIAHandler.UIA_AutomationIdPropertyId,
			"ContentTextBlock",
		)
		walker = clientObject.createTreeWalker(condition)
		notepadWindow = clientObject.elementFromHandle(api.getForegroundObject().windowHandle)
		try:
			element = walker.getFirstChildElement(notepadWindow)
			# Is status bar even showing?
			element = element.buildUpdatedCache(UIAHandler.handler.baseCacheRequest)
		except (ValueError, COMError):
			raise NotImplementedError
		statusBar = UIA(UIAElement=element).parent
		return statusBar

	def event_NVDAObject_init(self, obj: NVDAObject):
		# #18208: "go to line" edit field is classified as a dialog.
		if isinstance(obj, UIA) and obj.UIAAutomationId == "LineNumberBox":
			obj.role = controlTypes.Role.EDITABLETEXT
