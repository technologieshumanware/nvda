# This file was modified for the BrailleNote evolve
# Technologies Humanware 2026

# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2019-2025 NV Access Limited, Cyrille Bougot

"""App module for Microsoft Word.
Word and Outlook share a lot of code and components. This app module gathers the code that is relevant for
Microsoft Word only.
"""

import time
from NVDAObjects.UIA import Dialog
import appModuleHandler
import config
from humanwareCommands import commands as humanwareCommands
from scriptHandler import script
import ui
import api
from logHandler import log
import mathPres
from NVDAObjects.IAccessible.winword import WordDocument as IAccessibleWordDocument
from NVDAObjects.UIA.wordDocument import WordDocument as UIAWordDocument
from appModules import humanware
from NVDAObjects.window.winword import (
	WordDocument,
	WdOutlineLevel,
)
from utils.displayString import DisplayStringIntEnum
from typing import TYPE_CHECKING
import brailleInput
import controlTypes
import winUser
from NVDAObjects import NVDAObject
from typing import Callable

if TYPE_CHECKING:
	import inputCore

class ViewType(DisplayStringIntEnum):
	"""Enumeration containing the possible view types in Word documents:.
	https://learn.microsoft.com/en-us/office/vba/api/word.wdviewtype
	"""

	DRAFT = 1
	OUTLINE = 2
	PRINT = 3
	WEB = 6
	READ = 7

	@property
	def _displayStringLabels(self):
		return {
			# Translators: One of the view types in Word documents.
			ViewType.DRAFT: _("DRAFT"),
			# Translators: One of the view types in Word documents.
			ViewType.OUTLINE: _("Outline"),
			# Translators: One of the view types in Word documents.
			ViewType.PRINT: _("Print layout"),
			# Translators: One of the view types in Word documents.
			ViewType.WEB: _("Web layout"),
			# Translators: One of the view types in Word documents.
			ViewType.READ: _("Read mode"),
		}


class AppModule(appModuleHandler.AppModule):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		log.info("Word: Initialized with passive IME approach")

	def event_gainFocus(self, obj: NVDAObject, nextHandler: Callable[[], None]):
		"""Control IME based on focus context.

		For Word: Enable IME in main document, disable in dialogs/UI elements.
		"""
		# Check if we should enable IME
		shouldEnable = self._shouldEnableIME(obj)
		log.debug(f"Word gainFocus: shouldEnable={shouldEnable}, role={obj.role}")

		# Send message to IME
		if shouldEnable:
			log.debug("Word: Sending BRLUCX_enabled to IME")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(True)
		else:
			reason = self._getDisableReason(obj)
			log.debug(f"Word: Sending BRLUCX_disabled to IME (reason: {reason})")
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(False)

		nextHandler()

	def _shouldEnableIME(self, obj: NVDAObject) -> bool:
		"""Determine if IME should be enabled for this object.

		In Word: Enable for document content, disable for dialogs/UI.
		"""
		try:
			# Check if in main Word document
			if isinstance(obj, (UIAWordDocument, IAccessibleWordDocument, WordDocument)):
				log.debug("Word: Enabling main document")
				return True

			# Check for various UI elements that should be disabled
			if obj.role in (
				controlTypes.Role.BUTTON,
				controlTypes.Role.MENUITEM,
				controlTypes.Role.MENUBAR,
				controlTypes.Role.TOOLBAR,
				controlTypes.Role.TAB,
				controlTypes.Role.TABCONTROL,
				controlTypes.Role.LISTITEM,
			):
				log.debug(f"Word: Disabling UI element (role={obj.role})")
				return False


			# Check if parent is Word document (e.g., text within document)
			parent = obj.parent
			while parent:
				if isinstance(parent, (UIAWordDocument, IAccessibleWordDocument, WordDocument)):
					# Check if we're in a dialog or not. If in a dialog, disable. If in document content, enable.
					if parent.role == controlTypes.Role.DIALOG:
						log.debug("Word: Disabling content within dialog")
						return False

					log.debug(f"Word: Enabling content within document (parent role={parent.role})")
					return True
				if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
					break
				parent = parent.parent

			# Check for dialogs - should be disabled
			if obj.role == controlTypes.Role.DIALOG:
				log.debug("Word: Disabling dialog")
				return False

			# Walk the real Win32 HWND chain to detect common file dialogs (#32770),
			# e.g. Save As via File > Save As > This PC.
			# The NVDA parent chain breaks early on intermediate WINDOW-role panes,
			# so we use GA_ROOT to reach the topmost window reliably.
			try:
				hwnd = getattr(obj, 'windowHandle', None)
				if hwnd:
					root_hwnd = winUser.getAncestor(hwnd, winUser.GA_ROOT)
					if root_hwnd and winUser.getClassName(root_hwnd) == '#32770':
						log.debug("Word: Disabling, inside common file dialog (#32770 root HWND)")
						return False
			except Exception as e:
				log.debug(f"Word: hwnd ancestor check failed: {e}")

			# Check if in a dialog by walking up the NVDA parent chain
			parent = obj.parent
			while parent:
				if parent.role == controlTypes.Role.DIALOG:
					log.debug("Word: Disabling inside dialog")
					return False
				if parent.role in (controlTypes.Role.WINDOW, controlTypes.Role.APPLICATION):
					break
				parent = parent.parent


			# Check for "Tell me" search box or ribbon search
			if obj.role == controlTypes.Role.EDITABLETEXT:
				if obj.name and any(keyword in obj.name.lower()
				                    for keyword in ['tell me', 'search', 'find', 'replace']):
					log.debug(f"Word: Disabling search/find field (name={obj.name})")
					return False

			# Window (role=3) focus when switching to Word
			# Don't disable IME for window focus, keep current state and wait for document focus
			if obj.role == controlTypes.Role.WINDOW:
				# Check if there's a document child. If so, assume we're switching to document
				try:
					for child in obj.children:
						if isinstance(child, (UIAWordDocument, IAccessibleWordDocument, WordDocument)):
							log.debug("Word: Window with document child, keeping IME enabled")
							return True
				except:
					pass
				log.debug(f"Word: Disabling window focus (role={obj.role})")
				return False

			# Default: Enable for most editable content in Word
			if obj.role in (controlTypes.Role.EDITABLETEXT, controlTypes.Role.DOCUMENT):
				log.debug("Word: Enabling editable content")
				return True

			# For anything else, disable to be safe
			log.debug(f"Word: Disabling by default (role={obj.role})")
			return False

		except Exception as e:
			log.debug(f"Word: Error checking IME enable: {e}")
			# If unsure, enable (Word is generally safe)
			return True

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
		if obj.name and 'search' in obj.name.lower():
			return "search field"
		return "not document content"

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if (
			UIAWordDocument in clsList
			or IAccessibleWordDocument in clsList
			# Apply the Word document overlay (and its braille shortcuts) to the
			# HumanWare "HWWordDialog" expression editor (BNW-2013). The Dialog guard
			# keeps this separate from the Save As dialog, whose HWWordDialog wrapper
			# is a WINDOW rather than a DIALOG.
			or (Dialog in clsList and getattr(obj, "UIAAutomationId", None) == "HWWordDialog")
		):
			clsList.insert(0, WinwordWordDocument)
		elif self._isHWWordSaveAsDialog(obj):
			clsList.insert(0, HWWordSaveAsDialog)

	def _isHWWordSaveAsDialog(self, obj: NVDAObject) -> bool:
		"""Return True if obj is the "OpenSaveAsDialog" pane of the HumanWare Save As dialog.

		The dialog is a UIA pane whose className is "OpenSaveAsDialog" (it has no
		automationId). We corroborate it via its "FileManagerView" child pane, since
		the wrapping window's automationId is not reliable across hosts.
		"""
		if humanware.getUIAClassName(obj) != humanware.SAVE_AS_DIALOG_CLASS_NAME:
			return False
		try:
			for child in obj.children:
				if humanware.getUIAClassName(child) == humanware.SAVE_AS_FILE_MANAGER_CLASS_NAME:
					return True
		except Exception:
			pass
		return False

	def _supportsBRLUCX(self) -> bool:
		"""Check if current context supports BRLUCX."""
		return self._shouldEnableIME(api.getFocusObject())

	#Humanware section: key gestures for Word Expression Editor

	def _isWordExpressionEditor(self):
		return getattr(api.getFocusObject(), "UIAAutomationId", None) == "BrailleEditText"

	def getShortcutFromCommandName(self, commandName):
		return humanware.getShortcutFromCommandNameAndAppModuleName(self, commandName, "winword")

	@script(
		# Translators: Input Help message for the key math command.
		description=_("KeyMath"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot7"	# Backspace+M
	)
	def script_braille_keyMath(self, gesture):
		if self._isWordExpressionEditor():
			kbIdentifier = self.getShortcutFromCommandName("keyMath")
			humanware.emulateKeyPress(kbIdentifier)

	@script(
		# Translators: Input Help message for the insert template command.
		description=_("Insert template"),
		gesture="br(hidBrailleStandard):space+dot3+dot5+dot8"  # Enter+dots35
	)
	def script_braille_insertTemplate(self, gesture):
		if self._isWordExpressionEditor():
			kbIdentifier = self.getShortcutFromCommandName("insertTemplate")
			humanware.emulateKeyPress(kbIdentifier)

	@script(
		# Translators: Input Help message for the announce expression command.
		description=_("Announce expression"),
		gesture="br(hidBrailleStandard):space+dot1+dot4", # Space+C
	)
	def script_braille_announceExpression(self, gesture):
		if self._isWordExpressionEditor():
			kbIdentifier = self.getShortcutFromCommandName("announceExpression")
			humanware.emulateKeyPress(kbIdentifier)
		else:
			humanwareCommands.script_reportCurrentLine(gesture)

	@script(
		# Translators: Input Help message for the copy MathML to clipboard command.
		description=_("Copy MathML to clipboard"),
		gesture="br(hidBrailleStandard):space+dot1+dot5+dot7"  # Backspace+E
	)
	def script_braille_copyMathML(self, gesture):
		if self._isWordExpressionEditor():
			kbIdentifier = self.getShortcutFromCommandName("copyMathMLToClipboard")
			humanware.emulateKeyPress(kbIdentifier)

	@script(
		# Translators: Input Help message for the insert equation to document / insert or edit equation command.
		description=_("Insert equation to document / Insert or edit equation"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot8" # Enter+M
	)
	def script_braille_insert_equation_to_document_or_insert_edit_equation(self, gesture):
		#Select the appropriate action depending if we are in expression editor or in document
		if self._isWordExpressionEditor():
			humanware.emulateKeyPress("enter")
		else:
			kbIdentifier = self.getShortcutFromCommandName("insertOrEditEquation")
			humanware.emulateKeyPress(kbIdentifier)

	@script(
		# Translators: Input Help message for the complete MathML entry command.
		description=_("Complete MathML entry"),
		gesture="br(hidBrailleStandard):dot8" #Enter
	)
	def script_braille_complete_mathml_entry(self, gesture):
		if self._isWordExpressionEditor():
			kbIdentifier = self.getShortcutFromCommandName("completeMathMLEntry")
			humanware.emulateKeyPress(kbIdentifier)
		else:
			brailleInput.handler.enter()


	@script(
		# Translators: Input Help message for the insert braille symbol command.
		description=_("Insert braille symbol"),
		gesture="br(hidBrailleStandard):space+dot3+dot5+dot7" #Backspace+dots35
	)
	def script_braille_insert_braille_symbol(self, gesture):
		if self._isWordExpressionEditor():
			kbIdentifier = self.getShortcutFromCommandName("insertBrailleSymbol")
			humanware.emulateKeyPress(kbIdentifier)

	#End Humanware section: key gestures for Word Expression Editor

	def event_appModule_gainFocus(self):
		if config.conf["math"]["other"]["useWordNativeMath"]:
			mathPres.terminate()

	def event_appModule_loseFocus(self):
		mathPres.initialize()

	def terminate(self):
		mathPres.initialize()
		super().terminate()


class WinwordWordDocument(WordDocument):
	def _get_description(self) -> str:
		try:
			curView = self.WinwordWindowObject.view.Type
			description = super().description
			if isinstance(description, str) and not description.isspace():
				return f"{ViewType(curView).displayString} {description}"
			return ViewType(curView).displayString
		except AttributeError:
			return super()._get_description()

	@script(gestures=["kb:control+alt+o", "kb:control+alt+p"])
	def script_changeViewType(self, gesture: "inputCore.InputGesture") -> None:
		if not self.WinwordWindowObject:
			# We cannot fetch the Word object model, so we therefore cannot report the status change.
			# The object model may be unavailable because it's within Windows Defender Application Guard.
			# In this case, just let the gesture through and don't report anything.
			return gesture.send()
		val = self._WaitForValueChangeForAction(
			lambda: gesture.send(),
			lambda: self.WinwordWindowObject.view.Type,
		)
		ui.message(ViewType(val).displayString)

	@script(gesture="kb:control+shift+e")
	def script_toggleChangeTracking(self, gesture):
		if not self.WinwordDocumentObject:
			# We cannot fetch the Word object model, so we therefore cannot report the status change.
			# The object model may be unavailable because it's within Windows Defender Application Guard.
			# In this case, just let the gesture through and don't report anything.
			return gesture.send()
		val = self._WaitForValueChangeForAction(
			lambda: gesture.send(),
			lambda: self.WinwordDocumentObject.TrackRevisions,
		)
		if val:
			# Translators: a message when toggling change tracking in Microsoft word
			ui.message(_("Change tracking on"))
		else:
			# Translators: a message when toggling change tracking in Microsoft word
			ui.message(_("Change tracking off"))

	@script(
		gestures=[
			"kb:alt+shift+-",
			"kb:alt+shift+=",
			"kb:alt+shift+numpadPlus",
			"kb:alt+shift+numpadMinus",
			"kb:numLock+shift+alt+numpadPlus",
			"kb:numLock+shift+alt+numpadMinus",
		],
	)
	def script_collapseOrExpandHeading(self, gesture: "inputCore.InputGesture") -> None:
		if not self.WinwordSelectionObject:
			# We cannot fetch the Word object model, so we therefore cannot report the collapsed state change.
			# The object model may be unavailable because this is a pure UIA implementation such as Windows 10 Mail,
			# or it's within Windows Defender Application Guard.
			# In this case, just let the gesture through and don't report anything.
			gesture.send()
			return
		if self.WinwordWindowObject.view.Type in [ViewType.OUTLINE, ViewType.DRAFT]:
			# In draft mode, collapsing headings is not available.
			# In Outline view, paragraph.CollapsedState does not report the correct value.
			# So do not report anything in these modes
			gesture.send()
			return
		maxParagraphs = 50
		for nParagraph, paragraph in enumerate(self.WinwordSelectionObject.paragraphs):
			if paragraph.outlineLevel != WdOutlineLevel.BODY_TEXT:
				break
			if nParagraph >= maxParagraphs:
				log.debugWarning("Too many paragraphs selected")
				gesture.send()
				return
		else:
			gesture.send()
			# Translators: a message when collapsing or expanding headings in MS Word
			ui.message(_("No heading selected"))
			return
		val = self._WaitForValueChangeForAction(
			lambda: gesture.send(),
			lambda: paragraph.CollapsedState,
		)
		if val:
			# Translators: a message when collapsing a heading in MS Word
			msg = _("Collapsed")
		else:
			# Translators: a message when expanding a heading in MS Word
			msg = _("Expanded")
		ui.message(msg)

	__gestures = {
		"kb:control+shift+b": "toggleBold",
		"kb:control+shift+w": "toggleUnderline",
		"kb:control+shift+a": "toggleCaps",
	}

	# HumanWare Section => add shortcut
	# see source\keyLabels.py for shortcut like "control, shift, insert, space, pageup, end, ..."

	@script(
		# Translators: Input Help message for the open file command.
		description=_("Open file"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot5+dot7"	# Backspace+O
	)
	def script_braille_openFile(self, gesture):
		self.emulateKeyPressFromCommandName("open")

	@script(
		# Translators: Input Help message for the new file command.
		description=_("New file"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot7"	# Backspace+N
	)
	def script_braille_newFile(self, gesture):
		self.emulateKeyPressFromCommandName("new")

	@script(
		# Translators: Input Help message for the exit command.
		description=_("Exit"),
		gesture="br(hidBrailleStandard):space+dot1+dot5"	# Space+E
	)
	def script_braille_exit(self, gesture):
		# Disable IME to trigger backtranslation before the save dialog appears,
		# preventing braille characters in saved documents.
		if brailleInput.handler:
			brailleInput.handler.setBRLUCXEnabled(False)
		self.emulateKeyPressFromCommandName("exit")

	@script(
		# Translators: Input Help message for the word count command.
		description=_("Word count"),
		gesture="br(hidBrailleStandard):space+dot2+dot4"	# Space+I
	)
	def script_braille_wordCount(self, gesture):
		self.emulateKeyPressFromCommandName("wordCount")

	@script(
		# Translators: Input Help message for the read mode command.
		description=_("Read mode"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot6"	# Space+X
	)
	def script_braille_readMode(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("readMode")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the "Where am I" command.
		description=_("Where am I"),
		gesture="br(hidBrailleStandard):space+dot1+dot5+dot6"	# Space+dots156
	)
	def script_braille_whereAmI(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("whereAmI")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the find command.
		description=_("Find"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4"	# Space+F
	)
	def script_braille_find(self, gesture):
		self.emulateKeyPressFromCommandName("find")

	@script(
		# Translators: Input Help message for the find previous command.
		description=_("Find previous"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"	# Space+P
	)
	def script_braille_findPrevious(self, gesture):
		self.emulateKeyPressFromCommandName("findPrevious")

	@script(
		# Translators: Input Help message for the find next command.
		description=_("Find next"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot5",	# Space+N
	)
	def script_braille_findNext(self, gesture):
		self.emulateKeyPressFromCommandName("findNext")

	@script(
		# Translators: Input Help message for the replace command.
		description=_("Replace"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"	# Backspace+F
	)
	def script_braille_replace(self, gesture):
		self.emulateKeyPressFromCommandName("replace")

	@script(
		# Translators: Input Help message for the center alignment command.
		description=_("Center alignment"),
		gesture="br(hidBrailleStandard):space+dot1+dot4+dot8"	# Enter+C
	)
	def script_braille_centerAlignment(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("centerAlignment")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the left alignment command.
		description=_("Left alignment"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot7"	# Backspace+L
	)
	def script_braille_leftAlignment(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("leftAlignment")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the right alignment command.
		description=_("Right alignment"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot8"	# Enter+R
	)
	def script_braille_rightAlignment(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("rightAlignment")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the justify alignment command.
		description=_("Justify alignment"),
		gesture="br(hidBrailleStandard):space+dot2+dot4+dot5+dot8"	# Enter+J
	)
	def script_braille_justifyAlignment(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("justifyAlignment")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the bold command.
		description=_("Bold"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot8"	# Enter+B
	)
	def script_braille_bold(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("bold")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the italics command.
		description=_("Italics"),
		gesture="br(hidBrailleStandard):space+dot2+dot4+dot8"	# Enter+I
	)
	def script_braille_italics(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("italics")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the underline command.
		description=_("Underline"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot6+dot8"	# Enter+U
	)
	def script_braille_underline(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("underline")
		humanware.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the open font dialog command.
		description=_("Open font dialog"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot4+dot8"	# Enter+F
	)
	def script_braille_openFontDialog(self, gesture):
		self.emulateKeyPressFromCommandName("openFontDialog")

	@script(
		# Translators: Input Help message for the increase font size command.
		description=_("Increase font size"),
		gesture="br(hidBrailleStandard):space+dot3+dot4+dot5"	# Space+dots345
	)
	def script_braille_increaseFontSize(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("increaseFontSize")
		if not self.WinwordSelectionObject:
			return humanware.emulateGesture(kbIdentifier)
		val = self._WaitForValueChangeForAction(
			lambda: humanware.emulateGesture(kbIdentifier),
			lambda: self.WinwordSelectionObject.font.size,
		)
		# Translators: a message when increasing or decreasing font size in Microsoft Word
		ui.message(_("{size:g} point font").format(size=val))

	@script(
		# Translators: Input Help message for the decrease font size command in Microsoft Word.
		description=_("Decrease font size"),
		gesture="br(hidBrailleStandard):space+dot1+dot2+dot6"	# Space+dots126
	)
	def script_braille_decreaseFontSize(self, gesture):
		kbIdentifier = self.getShortcutFromCommandName("decreaseFontSize")
		if not self.WinwordSelectionObject:
			return humanware.emulateGesture(kbIdentifier)
		val = self._WaitForValueChangeForAction(
			lambda: humanware.emulateGesture(kbIdentifier),
			lambda: self.WinwordSelectionObject.font.size,
		)
		# Translators: a message when increasing or decreasing font size in Microsoft Word
		ui.message(_("{size:g} point font").format(size=val))

	@script(
		# Translators: Input Help message for the insert hyperlink command.
		description=_("Insert hyperlink"),
		gesture="br(hidBrailleStandard):space+dot1+dot3"	# Space+K
	)
	def script_braille_insertHyperlink(self, gesture):
		self.emulateKeyPressFromCommandName("insertHyperlink")

	@script(
		# Translators: Input Help message for the styles command.
		description=_("Styles"),
		gesture=("br(hidBrailleStandard):space+dot3+dot4+dot8"), # Enter + Dots 3 4
	)
	def script_braille_styles(self, gesture):
		self.emulateKeyPressFromCommandName("styles")

	@script(
		# Translators: Input Help message for the open menu list command.
		description=_("Open menu list"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A
	)
	def script_braille_openMenuList(self, gesture):
		focus = api.getFocusObject()
		supportsBRLUCX = (
			focus and focus.appModule
			and '_supportsBRLUCX' in type(focus.appModule).__dict__
		)

		if supportsBRLUCX:
			if brailleInput.handler:
				# Trigger a back translation before opening the menu list
				brailleInput.handler.setBRLUCXEnabled(False)

		# Add extra delay after Alt if in document (needed for menu to appear)
		delayAfterAlt = 0.5 if focus and focus.role == controlTypes.Role.DOCUMENT else 0.0
		
		# Use the locale-specific key sequence from gesturesFromCommandName.ini
		# English: "alt,m,l" / German: "alt,y,2,l"
		humanware.emulateKeySequenceFromCommandName(self, "openMenuListKeys", delayAfterAlt=delayAfterAlt)

	def emulateKeyPressFromCommandName(self, commandName):
		humanware.emulateKeyPressFromCommandNameAndAppModuleName(self, commandName, "winword")

	def getShortcutFromCommandName(self, commandName):
		return humanware.getShortcutFromCommandNameAndAppModuleName(self, commandName, "winword")

	# HumanWare End Section


class HWWordSaveAsDialog(NVDAObject):
	"""Overlay for the HumanWare custom "Save As" dialog (UIA className "OpenSaveAsDialog").

	The dialog is hosted inside winword.exe (a WPF/VSTA window), so the focus lands on
	a WPF child control rather than on a Word document. Because of this, the document
	overlay (WinwordWordDocument) and its braille scripts are not in scope here.
	This dedicated overlay is attached to the dialog object in
	AppModule.chooseNVDAObjectOverlayClasses, and canPropagate=True lets the gesture
	bubble up from the focused child control to this object.
	"""

	@script(
		# Translators: Input Help message for creating a new folder in the Save As dialog.
		description=_("New folder"),
		gesture="br(hidBrailleStandard):space+dot1+dot3+dot4+dot5",  # Space+N
		canPropagate=True,
	)
	def script_braille_newFolder(self, gesture):
		humanware.emulateKeyPressFromCommandNameAndAppModuleName(self, "new", "winword")
