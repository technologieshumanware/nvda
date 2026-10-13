# This file was modified for the BrailleNote evolve
# Technologies Humanware 2026

# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2006-2025 NV Access Limited, Yogesh Kumar, Manish Agrawal, Joseph Lee, Davy Kager,
# Babbage B.V., Leonard de Ruijter
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

import time
from comtypes import COMError
from comtypes.hresult import S_OK
import comtypes.client
import comtypes.automation
import ctypes
from scriptHandler import script
import winBindings.kernel32
import winKernel
import comHelper
import NVDAHelper
import winUser
from logHandler import log
import textInfos
import braille
import brailleInput
import appModuleHandler
import eventHandler
import UIAHandler
from UIAHandler.utils import createUIAMultiPropertyCondition
import api
import controlTypes
import config
from config.configFlags import ReportTableHeaders
import speech
import ui
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.window import Window
from NVDAObjects.window.winword import (
	WordDocument as BaseWordDocument,
	WordDocumentTreeInterceptor,
	BrowseModeWordDocumentTextInfo,
	WordDocumentTextInfo,
)
from NVDAObjects.IAccessible.winword import WordDocument
from NVDAObjects.IAccessible.MSHTML import MSHTML
from NVDAObjects.behaviors import RowWithFakeNavigation, Dialog
from NVDAObjects.UIA import UIA
from NVDAObjects.UIA.wordDocument import WordDocument as UIAWordDocument
from NVDAObjects import NVDAObject
import languageHandler
from typing import Generator, Callable
import documentBase
import browseMode
import appModules.HWUtils
import vision

PR_LAST_VERB_EXECUTED = 0x10810003
VERB_REPLYTOSENDER = 102
VERB_REPLYTOALL = 103
VERB_FORWARD = 104
executedVerbLabels = {
	# Translators: the last action taken on an Outlook mail message
	VERB_REPLYTOSENDER: _("replied"),
	# Translators: the last action taken on an Outlook mail message
	VERB_REPLYTOALL: _("replied all"),
	# Translators: the last action taken on an Outlook mail message
	VERB_FORWARD: _("forwarded"),
}


#: The number of seconds in a day, used to make all day appointments and selections less verbose.
#: Type: float
SECONDS_PER_DAY = 86400.0

importanceLabels = {
	# Translators: for a high importance email
	2: _("high importance"),
	# Translators: For a low importance email
	0: _("low importance"),
}


def getContactString(obj):
	return ", ".join(
		[
			x
			for x in [obj.fullName, obj.companyName, obj.jobTitle, obj.email1address]
			if x and not x.isspace()
		],
	)


def getReceivedMessageString(obj):
	nameList = []
	nameList.append(obj.senderName)
	# Translators: This is presented in outlook or live mail, email subject
	nameList.append(_("subject: %s") % obj.subject)
	# Translators: This is presented in outlook or live mail, email received time
	nameList.append(_("received: %s") % obj.receivedTime)

	text = ", ".join(nameList)
	if obj.unread:
		text = "%s %s" % (_("unread"), text)
	if obj.attachments.count > 0:
		# Translators: This is presented in outlook or live mail, indicating email attachments
		text = "%s %s" % (_("attachment"), text)
	return text


def getSentMessageString(obj):
	nameList = []
	nameList.append(obj.to)
	nameList.append(_("subject: %s") % obj.subject)
	# Translators: This is presented in outlook or live mail, email sent date
	nameList.append(_("sent: %s") % obj.sentOn)
	return ", ".join(nameList)


def isOutlookWordDocument():
	return isinstance(NVDAHelper.api.globalVars.focusObject, OutlookUIAWordDocument)


class AppModule(appModuleHandler.AppModule):
	def isGoodUIAWindow(self, hwnd: int) -> bool:
		windowClass = winUser.getClassName(hwnd)
		versionMajor = int(self.productVersion.split(".")[0])
		if versionMajor >= 16 and windowClass == "RICHEDIT60W":
			# #12726: RICHEDIT60W In Outlook 2016+ on Windows 10+
			# has a very good UI Automation implementation,
			# Though oddly IsServerSideProvider returns false for these windows.
			# Examples: date picker in the Outlook Advanced search dialog
			return True
		return False

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		# Explicitly allow gainFocus events for the window class that hosts the active Outlook DatePicker cell
		# This object gets focus but its window does not conform to our GUI thread info window checks
		eventHandler.requestEvents("gainFocus", processId=self.processID, windowClassName="rctrl_renwnd32")
		appModules.HWUtils.init(self)
		log.info("Outlook: Initialized with passive IME approach")

	_hasTriedoutlookAppSwitch = False

	def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable[[], None]):
		"""Control IME based on focus context.

		For Outlook: Enable IME in email composition/editing, disable in dialogs/UI elements.
		"""
		# Check if we should enable IME
		shouldEnable = self._shouldEnableIME(obj)

		log.debug(f"Outlook gainFocus: shouldEnable={shouldEnable}, role={obj.role}, class={obj.__class__.__name__}")

		# Send message to IME
		if shouldEnable:
			log.debug("Outlook: Sending BRLUCX_enabled to IME")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(True)
		else:
			reason = self._getDisableReason(obj)
			log.debug(f"Outlook: Sending BRLUCX_disabled to IME (reason: {reason})")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(False)

		nextHandler()

	def _supportsBRLUCX(self) -> bool:
		"""Check if current context supports BRLUCX."""
		return self._shouldEnableIME(api.getFocusObject())

	def _shouldEnableIME(self, obj: NVDAObject) -> bool:
		"""Determine if IME should be enabled for this object.

		In Outlook: Enable for email composition/editing, disable for dialogs/UI.
		"""
		try:
			# Check if in Outlook Word document (email composition)
			if isinstance(obj, (OutlookUIAWordDocument, WordDocument, BaseWordDocument)):
				log.debug("Outlook: Enabling email composition window")
				return True

			# Check if parent is Outlook Word document
			parent = obj.parent
			while parent:
				if isinstance(parent, (OutlookUIAWordDocument, WordDocument, BaseWordDocument)):
					log.debug("Outlook: Enabling content within email composition")
					return True
				if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
					break
				parent = parent.parent

			# Check for HTML message viewing/editing
			if isinstance(obj, MSHTML) and controlTypes.State.EDITABLE in obj.states:
				log.debug("Outlook: Enabling HTML editable content")
				return True

			# Recipient fields (To=4117, CC=4126), disable IME. addresses are not braille text
			# because outlook converts typed adresses into tokens which are not compatible with braille input
			if isinstance(obj, ContactEditField) and obj.windowControlID in (4117, 4126):
				log.debug("Outlook: Disabling contact/recipient field")
				return False

			# Subject and other RichEdit compose fields (RichEdit20W, RichEdit20WPT, etc.)
			if obj.windowClassName.startswith("RichEdit20W") and obj.role == controlTypes.Role.EDITABLETEXT:
				log.debug("Outlook: Enabling RichEdit message composition")
				return True

			# Check for dialogs
			if obj.role == controlTypes.Role.DIALOG:
				log.debug("Outlook: Disabling dialog")
				return False

			# Check if in a dialog by walking up
			parent = obj.parent
			while parent:
				if parent.role == controlTypes.Role.DIALOG:
					log.debug("Outlook: Disabling inside dialog")
					return False
				if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
					break
				parent = parent.parent

			# Check for various UI elements that should be disabled
			if obj.role in (
				controlTypes.Role.BUTTON,
				controlTypes.Role.MENUITEM,
				controlTypes.Role.MENUBAR,
				controlTypes.Role.TOOLBAR,
				controlTypes.Role.TAB,
				controlTypes.Role.TABCONTROL,
				controlTypes.Role.LISTITEM,  # Folder list, email list
				controlTypes.Role.TREEVIEWITEM,  # Folder tree
			):
				log.debug(f"Outlook: Disabling UI element (role={obj.role})")
				return False

			# Check for autocomplete list items
			if isinstance(obj, AutoCompleteListItem):
				log.debug("Outlook: Disabling autocomplete list")
				return False

			# Check for search boxes in ribbon
			if obj.role == controlTypes.Role.EDITABLETEXT:
				if obj.name and any(keyword in obj.name.lower()
				                    for keyword in ['search', 'find']):
					log.debug(f"Outlook: Disabling search field (name={obj.name})")
					return False

			# Enable for other editable content
			if obj.role in (controlTypes.Role.EDITABLETEXT, controlTypes.Role.DOCUMENT):
				if controlTypes.State.EDITABLE in obj.states:
					log.debug("Outlook: Enabling editable content")
					return True

			# For anything else, disable to be safe
			log.debug(f"Outlook: Disabling by default (role={obj.role})")
			return False

		except Exception as e:
			log.debug(f"Outlook: Error checking IME enable: {e}")
			# Disable by default to be safe in Outlook
			return False

	def _getDisableReason(self, obj: NVDAObject) -> str:
		"""Get reason why IME is disabled."""
		if obj.role == controlTypes.Role.DIALOG:
			return "dialog"
		parent = obj.parent
		while parent:
			if parent.role == controlTypes.Role.DIALOG:
				return "inside dialog"
			if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
				break
			parent = parent.parent
		if obj.role in (controlTypes.Role.BUTTON, controlTypes.Role.MENUITEM,
		                controlTypes.Role.TOOLBAR):
			return f"UI element ({obj.role})"
		if obj.role in (controlTypes.Role.LISTITEM, controlTypes.Role.TREEVIEWITEM):
			return "folder/email list"
		if isinstance(obj, AutoCompleteListItem):
			return "autocomplete list"
		if obj.name and 'search' in obj.name.lower():
			return "search field"
		return "not email composition or editable content"

	def _registerCOMWithFocusJuggle(self):
		import wx
		import gui

		# Translators: The title for the dialog shown while Microsoft Outlook initializes.
		d = wx.Dialog(None, title=_("Waiting for Outlook..."))
		d.CentreOnScreen()
		gui.mainFrame.prePopup()
		d.Show()
		self._hasTriedoutlookAppSwitch = True
		# Make sure NVDA detects and reports focus on the waiting dialog
		api.processPendingEvents()
		try:
			comtypes.client.PumpEvents(1)
		except WindowsError:
			log.debugWarning("Error while pumping com events", exc_info=True)
		d.Destroy()
		gui.mainFrame.postPopup()

	def _get_nativeOm(self):
		try:
			nativeOm = comHelper.getActiveObject("outlook.application", dynamic=True)
		except (COMError, WindowsError, RuntimeError):
			if self._hasTriedoutlookAppSwitch:
				log.error("Failed to get native object model", exc_info=True)
			nativeOm = None
		if not nativeOm and not self._hasTriedoutlookAppSwitch:
			self._registerCOMWithFocusJuggle()
			return None
		self.nativeOm = nativeOm
		return self.nativeOm

	def _get_outlookVersion(self):
		nativeOm = self.nativeOm
		if nativeOm:
			outlookVersion = int(nativeOm.version.split(".")[0])
		else:
			outlookVersion = 0
		return outlookVersion

	def isBadUIAWindow(self, hwnd):
		windowClass = winUser.getClassName(hwnd)
		# #2816: Outlook versions before 2016 auto complete does not fire enough UIA events, IAccessible is better.
		if windowClass == "NetUIHWND":
			parentHwnd = winUser.getAncestor(hwnd, winUser.GA_ROOT)
			if winUser.getClassName(parentHwnd) == "Net UI Tool Window":
				versionMajor = int(self.productVersion.split(".")[0])
				if versionMajor < 16:
					return True
		if windowClass in ("WeekViewWnd", "DayViewWnd"):
			return True
		return False

	def event_NVDAObject_init(self, obj):
		role = obj.role
		windowClassName = obj.windowClassName
		controlID = obj.windowControlID
		# The control showing plain text messages has very stuffed parents
		# Use the grandparent window as its parent
		if role == controlTypes.Role.EDITABLETEXT and windowClassName == "RichEdit20W" and controlID == 8224:
			obj.parent = Window._get_parent(Window._get_parent(obj))
		# The control that shows HTML messages has stuffed parents. Use the control's parent window as its parent
		if (
			windowClassName == "Internet Explorer_Server"
			and role == controlTypes.Role.PANE
			and not isinstance(obj, MSHTML)
		):
			obj.parent = Window._get_parent(Window._get_parent(obj))
		if role in (controlTypes.Role.MENUBAR, controlTypes.Role.MENUITEM):
			obj.description = None
		if role in (
			controlTypes.Role.TREEVIEW,
			controlTypes.Role.TREEVIEWITEM,
			controlTypes.Role.LIST,
			controlTypes.Role.LISTITEM,
		):
			obj.shouldAllowIAccessibleFocusEvent = True
		if (
			(windowClassName == "SUPERGRID" and controlID == 4704)
			or (windowClassName == "rctrl_renwnd32" and controlID == 109)
		) and role == controlTypes.Role.UNKNOWN:
			obj.role = controlTypes.Role.LISTITEM

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if UIAWordDocument in clsList:
			# Overlay class for Outlook message viewer when UI Automation for MS Word is enabled.
			clsList.insert(0, OutlookUIAWordDocument)
		if isinstance(obj, UIA) and obj.UIAElement.cachedClassName in (
			"LeafRow",
			"ThreadItem",
			"ThreadHeader",
		):
			clsList.insert(0, UIAGridRow)
		role = obj.role
		windowClassName = obj.windowClassName
		# AutoComplete listItems.
		# This class is abstract enough to  support both UIA and MSAA
		if role == controlTypes.Role.LISTITEM and (
			windowClassName.startswith("REListBox") or windowClassName.startswith("NetUIHWND")
		):
			clsList.insert(0, AutoCompleteListItem)
		if role == controlTypes.Role.EDITABLETEXT and windowClassName.startswith("RichEdit20W"):
			clsList.insert(0, ContactEditField)

		#  all   remaining classes are IAccessible
		if not isinstance(obj, IAccessible):
			return
		# Outlook uses dialogs for many forms such as appointment / meeting creation. In these cases, there is no sane dialog caption that can be calculated as the dialog inly contains controls.
		# Therefore remove the Dialog behavior for these imbedded dialog forms so as to not announce junk as the caption
		if Dialog in clsList:
			parentWindow = winUser.getAncestor(obj.windowHandle, winUser.GA_PARENT)
			if parentWindow and winUser.getClassName(parentWindow) == "AfxWndW":
				clsList.remove(Dialog)
		if WordDocument in clsList:
			clsList.insert(0, OutlookWordDocument)
		controlID = obj.windowControlID
		# Support the date picker in Outlook Meeting / Appointment creation forms
		if controlID == 4352 and role == controlTypes.Role.BUTTON:
			clsList.insert(0, DatePickerButton)
		elif role == controlTypes.Role.TABLECELL and windowClassName == "rctrl_renwnd32":
			clsList.insert(0, DatePickerCell)
		elif windowClassName == "REListBox20W" and role == controlTypes.Role.CHECKBOX:
			clsList.insert(0, REListBox20W_CheckBox)
		if role == controlTypes.Role.LISTITEM and windowClassName == "OUTEXVLB":
			clsList.insert(0, AddressBookEntry)
			return
		if (windowClassName == "SUPERGRID" and controlID == 4704) or (
			windowClassName == "rctrl_renwnd32" and controlID == 109
		):
			outlookVersion = self.outlookVersion
			if (
				outlookVersion
				and outlookVersion > 9
				and obj.event_objectID == winUser.OBJID_CLIENT
				and obj.event_childID == 0
			):
				clsList.insert(0, SuperGridClient2010)
		if (windowClassName == "AfxWndW" and controlID == 109) or (
			windowClassName in ("WeekViewWnd", "DayViewWnd")
		):
			clsList.insert(0, CalendarView)

	# HumanWare section

	@script(
		# Translators: Input help message for the copy command.
		description=_("Copy"),
		gestures=(
			"br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot6+dot7", # Backspace+Y
			"kb:control+c"),
	)
	def script_copy(self, gesture):
		# Translators: Input help message for the copy command.
		ui.message(_("Copy"))
		appModules.HWUtils.emulateKeyPressFromCommandNameAndAppModuleName(self, "copy", "HumanwareCommands")

	@script(
		# Translators: Input help message for the cut command.
		description=_("Cut"),
		gestures=(
			"br(hidBrailleStandard):space+dot1+dot3+dot4+dot6+dot7", # Backspace+X
			"kb:control+x"),
	)
	def script_cut(self, gesture):
		# Translators: Input help message for the cut command.
		ui.message(_("Cut"))
		appModules.HWUtils.emulateKeyPressFromCommandNameAndAppModuleName(self, "cut", "HumanwareCommands")

	@script(
		# Translators: Input help message for the paste command.
		description=_("Paste"),
		gestures=(
			"br(hidBrailleStandard):space+dot1+dot2+dot3+dot6+dot7",	# Backspace+V
			"kb:control+v"),
	)
	def script_paste(self, gesture):
		# Translators: Input help message for the paste command.
		ui.message(_("Paste"))
		appModules.HWUtils.emulateKeyPressFromCommandNameAndAppModuleName(self, "paste", "HumanwareCommands")

	@script(
		# Translators: Input help message for the jump to search bar command.
		description=_("Jump to search bar"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4"	# Space+F
	)
	def script_braille_jumpToSearchBar(self, gesture):
		if isOutlookWordDocument():
			self.emulateKeyPressFromCommandName("find")				# Ctrl+F
		else:
			self.emulateKeyPressFromCommandName("jumpToSearchBar")	# F3

	@script(
		description=_("Justify alignment"),
		gesture="br(hidBrailleStandard):space+dot2+dot4+dot5+dot8"	# Enter+J
	)
	def script_braille_justifyAligment(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "justifyAlignment", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)	# Ctrl+J

	@script(
		# Translators: Input help message for the go to folder command.
		description=_("Go to folder"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot5+dot8"	# Enter+G
	)
	def script_braille_goToFolder(self, gesture):
		self.emulateKeyPressFromCommandName("goToFolder")		# Ctrl+Y

	@script(
		# Translators: Input help message for the new command.
		description=_("New"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"	# Space+N
	)
	def script_braille_new(self, gesture):
		self.emulateKeyPressFromCommandName("new")	# Ctrl+N

	@script(
		# Translators: Input help message for the reply command.
		description=_("Reply"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot7"	# Backspace+R
	)
	def script_braille_reply(self, gesture):
		self.emulateKeyPressFromCommandName("reply")	# Ctrl+R

	@script(
		# Translators: Input help message for the reply all command.
		description=_("Reply all"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot7+dot8"	# Backspace+Enter+R
	)
	def script_braille_replyAll(self, gesture):
		self.emulateKeyPressFromCommandName("replyAll")	# Ctrl+shift+R

	@script(
		# Translators: Input help message for the send message command.
		description=_("Send message"),
		gesture="br(hidBrailleStandard):space+dot2+dot3+dot4+dot7"	# Backspace+S
	)
	def script_braille_sendMessage(self, gesture):
		self.emulateKeyPressFromCommandName("sendMessage")

	@script(
		# Translators: Input help message for the mark/unmark message command.
		description=_("Mark/Unmark message"),
		gestures=[
			"br(hidBrailleStandard):space+dot1+dot2+dot3+dot7", # Backspace+L
			"kb:control+space"
			]
	)
	def script_braille_markMessage(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "leftAlignment", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)	# Ctrl+L
		else:
			focusedObject = api.getFocusObject()
			if not focusedObject.UIASelectionItemPattern:
				log.debug("Current object does not support SelectionItem pattern.")
				return

			isSelected = focusedObject.UIASelectionItemPattern.CurrentIsSelected
			if isSelected:
				focusedObject.UIASelectionItemPattern.RemoveFromSelection()
			else:
				focusedObject.UIASelectionItemPattern.AddToSelection()

			# Update the state (sel vs nsel + add/remove dots 7-8)
			eventHandler.queueEvent("stateChange", focusedObject)

	@script(
		description=_("Right alignment"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot8"	# Enter+R
	)
	def script_braille_rightAlignment(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "rightAlignment", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)	# Ctrl+R
		else:
			self.emulateKeyPressFromCommandName("refresh")			# F9

	@script(
		description=_("Forward"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"	# Backspace+F
	)
	def script_braille_forward(self, gesture):
		if isOutlookWordDocument():
			self.emulateKeyPressFromCommandName("replace")	# Ctrl+H
		else:
			self.emulateKeyPressFromCommandName("forward")	# Ctrl+F

	@script(
		# Translators: Input help message for the new meeting command.
		description=_("New meeting"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot5"	# Space+Q
	)
	def script_braille_newMeeting(self, gesture):
		self.emulateKeyPressFromCommandName("newMeeting")	# Ctrl+shift+Q

	@script(
		# Translators: Input help message for the open command.
		description=_("Open"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot5+dot7"	# Backspace+O
	)
	def script_braille_open(self, gesture):
		self.emulateKeyPressFromCommandName("open")	# Ctrl+F12

	@script(
		description=_("Read mode"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot6"	# Space+X
	)
	def script_braille_readMode(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "readMode", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input help message for the open address book command.
		description=_("Open address book"),
		gesture="br(hidBrailleStandard):space+dot1+dot5+dot7"	# Backspace+E
	)
	def script_braille_openAddressBook(self, gesture):
		self.emulateKeyPressFromCommandName("openAddressBook")	# Ctrl+shift+B

	@script(
		description=_("Exit"),
		gesture="br(hidBrailleStandard):space+dot1+dot5"	# Space+E
	)
	def script_braille_exit(self, gesture):
		self.emulateKeyPressFromCommandName("exit")

	@script(
		description=_("Center alignment"),
		gesture="br(hidBrailleStandard):space+dot1+dot4+dot8"	# Enter+C
	)
	def script_braille_centerAlignment(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "centerAlignment", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		description=_("Bold"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot8"	# Enter+B
	)
	def script_braille_bold(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "bold", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		description=_("Italics"),
		gesture="br(hidBrailleStandard):space+dot2+dot4+dot8"	# Enter+I
	)
	def script_braille_italics(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "italics", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		description=_("Underline"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot6+dot8"	# Enter+U
	)
	def script_braille_underline(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "underline", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		description=_("Increase font size"),
		gesture="br(hidBrailleStandard):space+dot3+dot4+dot5"	# Space+dots345
	)
	def script_braille_increaseFontSize(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "increaseFontSize", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		description=_("Decrease font size"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot6"	# Space+dots126
	)
	def script_braille_decreaseFontSize(self, gesture):
		if isOutlookWordDocument():
			kbIdentifier = appModules.HWUtils.getShortcutFromCommandNameAndAppModuleName(self, "decreaseFontSize", "outlook")
			appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		description=_("Open font dialog"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot8"	# Enter+F
	)
	def script_braille_openMessageFontDialog(self, gesture):
		if isOutlookWordDocument():
			self.emulateKeyPressFromCommandName("openMessageFontDialog")

	@script(
		description=_("Insert hyperlink"),
		gesture="br(hidBrailleStandard):space+dot1+dot3"	# Space+K
	)
	def script_braille_insertHyperlink(self, gesture):
		if isOutlookWordDocument():
			self.emulateKeyPressFromCommandName("insertHyperlink")

	def emulateKeyPressFromCommandName(self, commandName):
		appModules.HWUtils.emulateKeyPressFromCommandNameAndAppModuleName(self, commandName, "outlook")

	@script(
		description=_("Open menu list"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A
	)
	def script_braille_openMenuList(self, gesture):
		time.sleep(0.5)
		focus = api.getFocusObject()
		appModules.HWUtils.emulateKeyPress("alt")
		# In document view (message reading/composing), an additional delay is required
		# to allow focus to transition from the document to the menu bar before processing
		# the menu item keystrokes (M and L), otherwise they get intercepted by the document.
		if focus and focus.role == controlTypes.Role.DOCUMENT:
			time.sleep(0.5)
		appModules.HWUtils.emulateKeyPress("m")
		appModules.HWUtils.emulateKeyPress("l")

	# HumanWare end section

class REListBox20W_CheckBox(IAccessible):
	def script_checkbox(self, gesture):
		gesture.send()
		self.event_stateChange()

	__gestures = {
		"kb:space": "checkbox",
	}


class SuperGridClient2010(IAccessible):
	def isDuplicateIAccessibleEvent(self, obj):
		return False

	def _get_shouldAllowIAccessibleFocusEvent(self):
		# The window must really have focus.
		# Outlook can sometimes fire invalid focus events when showing daily tasks within the calendar.
		if winUser.getGUIThreadInfo(self.windowThreadID).hwndFocus != self.windowHandle:
			return False
		return super(SuperGridClient2010, self).shouldAllowIAccessibleFocusEvent

	def event_gainFocus(self):
		# #3834: UIA has a much better implementation for rows, so use it if available.
		if self.appModule.outlookVersion < 14 or not UIAHandler.handler:
			return super(SuperGridClient2010, self).event_gainFocus()
		try:
			kwargs = {}
			UIA.kwargsFromSuper(kwargs, relation="focus", ignoreNonNativeElementsWithFocus=False)
			obj = UIA(**kwargs)
		except Exception:
			log.error("Retrieving UIA focus failed", exc_info=True)
			return super(SuperGridClient2010, self).event_gainFocus()
		if not isinstance(obj, UIAGridRow):
			return super(SuperGridClient2010, self).event_gainFocus()
		obj.parent = self.parent
		eventHandler.executeEvent("gainFocus", obj)


class AddressBookEntry(IAccessible):
	def script_moveByEntry(self, gesture):
		gesture.send()
		eventHandler.queueEvent("nameChange", self)

	__moveByEntryGestures = (
		"kb:downArrow",
		"kb:upArrow",
		"kb:home",
		"kb:end",
		"kb:delete",
	)

	def initOverlayClass(self):
		for gesture in self.__moveByEntryGestures:
			self.bindGesture(gesture, "moveByEntry")


class ContactEditField(NVDAObject):
	@script(gestures=["kb:escape"])
	def script_hide(self, gesture):
		"""The auto-complete list is getting closed, set focus back to the edit field."""
		if vision.handler:
			vision.handler.handleGainFocus(self)
			api.setNavigatorObject(self)
		gesture.send()

	def event_valueChange(self):
		"""Set focus back to the edit field when an auto-complete list item is confirmed."""
		if vision.handler:
			vision.handler.handleGainFocus(self)
			api.setNavigatorObject(self, isFocus=True)
		super().event_valueChange()


class AutoCompleteListItem(Window):
	def event_stateChange(self):
		states = self.states
		focus = api.getFocusObject()
		if (
			(focus.role == controlTypes.Role.EDITABLETEXT or focus.role == controlTypes.Role.BUTTON)
			and controlTypes.State.SELECTED in states
			and controlTypes.State.INVISIBLE not in states
			and controlTypes.State.UNAVAILABLE not in states
			and controlTypes.State.OFFSCREEN not in states
		):
			speech.cancelSpeech()
			text = self.name
			# Some newer versions of Outlook don't put the contact as the name of the listItem, rather it is on the parent
			if not text:
				text = self.parent.name
			ui.message(text)

			if vision.handler:
				vision.handler.handleGainFocus(self)
			api.setNavigatorObject(self)


class CalendarView(IAccessible):
	"""Support for announcing time slots and appointments in Outlook Calendar."""

	_lastStartDate = None

	def _generateTimeRangeText(self, startTime, endTime):
		startText = winKernel.GetTimeFormatEx(
			winKernel.LOCALE_NAME_USER_DEFAULT,
			winKernel.TIME_NOSECONDS,
			startTime,
			None,
		)
		endText = winKernel.GetTimeFormatEx(
			winKernel.LOCALE_NAME_USER_DEFAULT,
			winKernel.TIME_NOSECONDS,
			endTime,
			None,
		)
		startDate = startTime.date()
		endDate = endTime.date()
		if (
			not CalendarView._lastStartDate
			or startDate != CalendarView._lastStartDate
			or endDate != startDate
		):
			startDateText = winKernel.GetDateFormatEx(
				winKernel.LOCALE_NAME_USER_DEFAULT,
				winKernel.DATE_LONGDATE,
				startTime,
				None,
			)
			startText = "%s %s" % (startDateText, startText)
		CalendarView._lastStartDate = startDate
		if endDate != startDate:
			if (startTime.hour, startTime.minute, startTime.second) == (0, 0, 0) and (
				endDate - startDate
			).total_seconds() == SECONDS_PER_DAY:
				# Translators: a message reporting the date of a all day Outlook calendar entry
				return _("{date} (all day)").format(date=startDateText)
			endText = "%s %s" % (
				winKernel.GetDateFormatEx(
					winKernel.LOCALE_NAME_USER_DEFAULT,
					winKernel.DATE_LONGDATE,
					endTime,
					None,
				),
				endText,
			)
		# Translators: a message reporting the time range (i.e. start time to end time) of an Outlook calendar entry
		return _("{startTime} to {endTime}").format(startTime=startText, endTime=endText)

	@staticmethod
	def _generateCategoriesText(appointment):
		categories = appointment.Categories
		if not categories:
			return None
		# Categories is a delimited string of category names that have been assigned to an Outlook item.
		# This property uses the user locale's list separator to separate entries.
		# See also https://docs.microsoft.com/en-us/office/vba/api/outlook.appointmentitem.categories
		bufLength = 4
		separatorBuf = ctypes.create_unicode_buffer(bufLength)
		if (
			winBindings.kernel32.GetLocaleInfo(
				languageHandler.LOCALE_USER_DEFAULT,
				languageHandler.LOCALE.SLIST,
				separatorBuf,
				bufLength,
			)
			== 0
		):
			raise ctypes.WinError()
		categoriesCount = len(categories.split(f"{separatorBuf.value} "))

		# Translators: Part of a message reported when on a calendar appointment with one or more categories
		# in Microsoft Outlook.
		categoriesText = ngettext("category {categories}", "categories {categories}", categoriesCount)
		return categoriesText.format(categories=categories)

	def isDuplicateIAccessibleEvent(self, obj):
		return False

	def event_nameChange(self):
		pass

	def event_stateChange(self):
		pass

	def reportFocus(self):
		if self.appModule.outlookVersion >= 13 and self.appModule.nativeOm:
			e = self.appModule.nativeOm.activeExplorer()
			s = e.selection
			if s.count > 0:
				p = s.item(1)
				try:
					start = p.start
					end = p.end
				except COMError:
					return super(CalendarView, self).reportFocus()
				t = self._generateTimeRangeText(start, end)
				# Translators: A message reported when on a calendar appointment with category in Microsoft Outlook
				message = _("Appointment {subject}, {time}").format(subject=p.subject, time=t)
				try:
					categoriesText = self._generateCategoriesText(p)
				except COMError:
					categoriesText = None
				if categoriesText is not None:
					message = f"{message}, {categoriesText}"
				ui.message(message)
			else:
				v = e.currentView
				try:
					selectedStartTime = v.selectedStartTime
					selectedEndTime = v.selectedEndTime
				except COMError:
					return super(CalendarView, self).reportFocus()
				timeSlotText = self._generateTimeRangeText(selectedStartTime, selectedEndTime)
				startDate = winKernel.GetDateFormatEx(
					winKernel.LOCALE_NAME_USER_DEFAULT,
					winKernel.DATE_LONGDATE,
					selectedStartTime,
					None,
				)
				startTime = winKernel.GetTimeFormatEx(
					winKernel.LOCALE_NAME_USER_DEFAULT,
					winKernel.TIME_NOSECONDS,
					selectedStartTime,
					None,
				)
				endDate = winKernel.GetDateFormatEx(
					winKernel.LOCALE_NAME_USER_DEFAULT,
					winKernel.DATE_LONGDATE,
					selectedEndTime,
					None,
				)
				endTime = winKernel.GetTimeFormatEx(
					winKernel.LOCALE_NAME_USER_DEFAULT,
					winKernel.TIME_NOSECONDS,
					selectedEndTime,
					None,
				)
				query = f'[Start] < "{endDate} {endTime}" And [End] > "{startDate} {startTime}"'
				i = e.currentFolder.items
				i.sort("[Start]")
				i.IncludeRecurrences = True
				if i.find(query):
					# Translators: a message when the current time slot on an Outlook Calendar has an appointment
					timeSlotText = _("Has appointment") + " " + timeSlotText
				ui.message(timeSlotText)
		else:
			self.event_valueChange()


class UIAGridRow(RowWithFakeNavigation, UIA):
	rowHeaderText = None
	columnHeaderText = None

	def _get_name(self):
		# Translators: Column header in the Outlook inbox message list for the sender's name
		columnHeaderFrom = _("From")
		# Translators: Column header in the Outlook inbox message list for the email subject
		columnHeaderSubject = _("Subject")
		# Translators: Column header in the Outlook inbox message list for the received date/time
		columnHeaderReceived = _("Received")

		textList = []
		if controlTypes.State.EXPANDED in self.states:
			textList.append(controlTypes.State.EXPANDED.displayString)
		elif controlTypes.State.COLLAPSED in self.states:
			textList.append(controlTypes.State.COLLAPSED.displayString)
		selection = None
		if self.appModule.nativeOm:
			try:
				selection = self.appModule.nativeOm.activeExplorer().selection.item(1)
			except COMError:
				pass
		if selection:
			try:
				unread = selection.unread
			except COMError:
				unread = False
			# Translators: when an email is unread
			if unread:
				textList.append(_("unread"))
			try:
				mapiObject = selection.mapiObject
			except COMError:
				mapiObject = None
			if mapiObject:
				v = comtypes.automation.VARIANT()
				res = NVDAHelper.localLib.nvdaInProcUtils_outlook_getMAPIProp(
					self.appModule.helperLocalBindingHandle,
					self.windowThreadID,
					mapiObject,
					PR_LAST_VERB_EXECUTED,
					ctypes.byref(v),
				)
				if res == S_OK:
					verbLabel = executedVerbLabels.get(v.value, None)
					if verbLabel:
						textList.append(verbLabel)
			# try:
			# 	attachmentCount = selection.attachments.count
			# except COMError:
			# 	attachmentCount = 0
			# # Translators: when an email has attachments
			# if attachmentCount > 0:
			# 	textList.append(_("has attachment"))
			try:
				importance = selection.importance
			except COMError:
				importance = 1
			importanceLabel = importanceLabels.get(importance)
			if importanceLabel:
				textList.append(importanceLabel)
			try:
				messageClass = selection.messageClass
			except COMError:
				messageClass = None
			if messageClass == "IPM.Schedule.Meeting.Request":
				# Translators: the email is a meeting request
				textList.append(_("meeting request"))
		childrenCacheRequest = UIAHandler.handler.baseCacheRequest.clone()
		childrenCacheRequest.addProperty(UIAHandler.UIA_NamePropertyId)
		childrenCacheRequest.addProperty(UIAHandler.UIA_TableItemColumnHeaderItemsPropertyId)
		childrenCacheRequest.TreeScope = UIAHandler.TreeScope_Children
		# We must filter the children for just text and image elements otherwise getCachedChildren fails completely in conversation view.
		childrenCacheRequest.treeFilter = createUIAMultiPropertyCondition(
			{
				UIAHandler.UIA_ControlTypePropertyId: [
					UIAHandler.UIA_TextControlTypeId,
					UIAHandler.UIA_ImageControlTypeId,
				],
			},
		)
		cachedChildren = self.UIAElement.buildUpdatedCache(childrenCacheRequest).getCachedChildren()
		if not cachedChildren:
			# There are no children
			# This is unexpected here.
			log.debugWarning("Unable to get relevant children for UIAGridRow", stack_info=True)
			return super(UIAGridRow, self).name
		for index in range(cachedChildren.length):
			e = cachedChildren.getElement(index)
			UIAControlType = e.cachedControlType
			UIAClassName = e.cachedClassName
			# We only want to include particular children.
			# We only include the flagField if the object model's flagIcon or flagStatus is set.
			# Stops us from reporting "unflagged" which is too verbose.
			if selection and UIAClassName == "FlagField":
				try:
					if not selection.flagIcon and not selection.flagStatus:
						continue
				except COMError:
					continue
			# the category field should only be reported if the objectModel's categories property actually contains a valid string.
			# Stops us from reporting "no categories" which is too verbose.
			elif selection and UIAClassName == "CategoryField":
				try:
					if not selection.categories:
						continue
				except COMError:
					continue
			# And we don't care about anything else that is not a text element.
			elif UIAControlType != UIAHandler.UIA_TextControlTypeId:
				continue
			name = e.cachedName
			columnHeaderTextList = []
			if name and config.conf["documentFormatting"]["reportTableHeaders"] in (
				ReportTableHeaders.ROWS_AND_COLUMNS,
				ReportTableHeaders.COLUMNS,
			):
				columnHeaderItems = e.getCachedPropertyValueEx(
					UIAHandler.UIA_TableItemColumnHeaderItemsPropertyId,
					True,
				)
			else:
				columnHeaderItems = None
			if columnHeaderItems:
				columnHeaderItems = columnHeaderItems.QueryInterface(UIAHandler.IUIAutomationElementArray)
				for index in range(columnHeaderItems.length):
					columnHeaderItem = columnHeaderItems.getElement(index)
					columnHeaderTextList.append(columnHeaderItem.currentName)
			columnHeaderText = " ".join(columnHeaderTextList)
			# if columnHeaderText:
			# 	text = "{header} {name}".format(header=columnHeaderText, name=name)
			# else:
			# 	text = name
			# Check if this is a standard column header that should be included
			text = name if columnHeaderText in (columnHeaderFrom, columnHeaderSubject, columnHeaderReceived) or not columnHeaderText else None
			if text:
				if UIAClassName == "FlagField":
					textList.insert(0, text)
				else:
					text += ","
					textList.append(text)
		return " ".join(textList)

	value = None

	def _get_positionInfo(self):
		info = super(UIAGridRow, self).positionInfo
		if info is None:
			info = {}
		UIAClassName = self.UIAElement.cachedClassName
		if UIAClassName == "ThreadHeader":
			info["level"] = 1
		elif UIAClassName == "ThreadItem" and isinstance(super(UIAGridRow, self).parent, UIAGridRow):
			info["level"] = 2
		return info

	def _get_role(self):
		role = super(UIAGridRow, self).role
		if role == controlTypes.Role.TREEVIEW:
			role = controlTypes.Role.TREEVIEWITEM
		elif role == controlTypes.Role.DATAITEM:
			role = controlTypes.Role.LISTITEM
		return role

	def setFocus(self):
		super(UIAGridRow, self).setFocus()
		eventHandler.queueEvent("gainFocus", self)


class MailViewerTextInfoForTreeInterceptor(WordDocumentTextInfo):
	def _get_shouldIncludeLayoutTables(self):
		return config.conf["documentFormatting"]["includeLayoutTables"]


class MailViewerTreeInterceptorTextInfo(BrowseModeWordDocumentTextInfo):
	InnerTextInfoClass = MailViewerTextInfoForTreeInterceptor


class MailViewerTreeInterceptor(WordDocumentTreeInterceptor):
	"""A BrowseMode treeInterceptor specifically for readonly emails, where tab and shift+tab are safe and we know will not edit the document."""

	TextInfo = MailViewerTreeInterceptorTextInfo

	def script_tab(self, gesture):
		bookmark = self.rootNVDAObject.makeTextInfo(textInfos.POSITION_SELECTION).bookmark
		gesture.send()
		info, caretMoved = self.rootNVDAObject._hasCaretMoved(bookmark)
		if not caretMoved:
			return
		info = self.makeTextInfo(textInfos.POSITION_SELECTION)
		inTable = info._rangeObj.tables.count > 0
		isCollapsed = info.isCollapsed
		if inTable and isCollapsed:
			info.expand(textInfos.UNIT_CELL)
			isCollapsed = False
		if not isCollapsed:
			speech.speakTextInfo(info, reason=controlTypes.OutputReason.FOCUS)
		braille.handler.handleCaretMove(self)

	def _iterTextStyle(
		self,
		kind: str,
		direction: documentBase._Movement = documentBase._Movement.NEXT,
		pos: textInfos.TextInfo | None = None,
	) -> Generator[browseMode.TextInfoQuickNavItem, None, None]:
		raise NotImplementedError("Outlook is not supported due to performance - #16408")

	__gestures = {
		"kb:tab": "tab",
		"kb:shift+tab": "tab",
	}


class BaseOutlookWordDocument(BaseWordDocument):
	@script(gestures=["kb:tab", "kb:shift+tab"])
	def script_tab(self, gesture):
		bookmark = self.makeTextInfo(textInfos.POSITION_SELECTION).bookmark
		gesture.send()
		info, caretMoved = self._hasCaretMoved(bookmark)
		if not caretMoved:
			return
		self.reportTab()


class OutlookWordDocument(WordDocument, BaseOutlookWordDocument):
	def _get_isReadonlyViewer(self):
		# #2975: The only way we know an email is read-only is if the underlying email has been sent.
		try:
			return self.appModule.nativeOm.activeInspector().currentItem.sent
		except (COMError, NameError, AttributeError):
			return False

	def _get_treeInterceptorClass(self):
		if self.isReadonlyViewer:
			return MailViewerTreeInterceptor
		return super(OutlookWordDocument, self).treeInterceptorClass

	def _get_shouldCreateTreeInterceptor(self):
		return self.isReadonlyViewer

	def _get_role(self):
		return controlTypes.Role.DOCUMENT if self.isReadonlyViewer else super(OutlookWordDocument, self).role

	ignoreEditorRevisions = True
	ignorePageNumbers = (
		True  # This includes page sections, and page columns. None of which are appropriate for outlook.
	)

	__gestures = {
		"kb:control+shift+a": "changeCase",
	}


class OutlookUIAWordDocument(UIAWordDocument, BaseOutlookWordDocument):
	"""Forces browse mode to be used on the UI Automation Outlook message viewer if the message is being read)."""

	def _get_isReadonlyViewer(self):
		return controlTypes.State.READONLY in self.states

	def _get_shouldCreateTreeInterceptor(self):
		return self.isReadonlyViewer


class DatePickerButton(IAccessible):
	# Value is a duplicate of name so get rid of it
	value = None


class DatePickerCell(IAccessible):
	# Value is a duplicate of name so get rid of it
	value = None

	# Focus events are always on this object with the exact same event parameters
	# Therefore we cannot safely filter out duplicates
	def isDuplicateIAccessibleEvent(self, obj):
		return False
