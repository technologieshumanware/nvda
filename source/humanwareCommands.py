# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# Standard library imports
import os
import sys

# Third-party imports
import wx

# NVDA imports
import api
import braille
import brailleInput
import brailleTranslation
import controlTypes
import core
import globalCommands
import inputCore
import scriptHandler
import winUser
from appModules import HWUtils
from baseObject import ScriptableObject
from globalCommands import SCRCAT_BRAILLE
from logHandler import log
from NVDAState import WritePaths
from scriptHandler import script

# Add BrailleNoteEvolve addon path to sys.path for importing modules
# Try both installed addon location and scratchpad (development) location
addon_paths = [
	# Installed addon location (works for release and portable)
	os.path.join(WritePaths.addonsDir, "BrailleNoteEvolve", "globalPlugins", "BrailleNoteEvolve"),
	# Development/scratchpad location
	os.path.join(WritePaths.scratchpadDir, "globalPlugins", "BrailleNoteEvolve")
]
for addon_path in addon_paths:
	if os.path.exists(addon_path) and addon_path not in sys.path:
		sys.path.insert(0, addon_path)
		break

# Import from BrailleNoteEvolve addon
try:
	import _languageProfileDialog  # type: ignore  # dynamically added to sys.path
except ImportError:
	log.warning("Could not import _languageProfileDialog from BrailleNoteEvolve addon")
	_languageProfileDialog = None

# Binary masks for braille dots
DOT_7_MASK = 0b01000000  # 64
DOT_8_MASK = 0b10000000  # 128
DOT_7_OR_8_MASK = DOT_7_MASK | DOT_8_MASK  # 192 (dots 7 or 8)


class EmulatedGesture(inputCore.InputGesture):
	"""Wrapper for emulating braille gestures with custom identifiers."""

	def __init__(self, targetGestureId, originalGesture=None):
		super().__init__()
		self.targetGestureId = targetGestureId
		# Copy important attributes from the original gesture
		if originalGesture and hasattr(originalGesture, 'dots'):
			self.dots = originalGesture.dots

	def _get_identifiers(self):
		return [self.targetGestureId]

	def _get_displayName(self):
		return self.targetGestureId


class HumanwareCommands(ScriptableObject):

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Routes the cursor to or activates the object under this braille cell"),
		category=SCRCAT_BRAILLE,
		gesture=("br(hidBrailleStandard):routerSet1_routerKey"),
	)
	def script_braille_routeTo(self, gesture):
		focusObj = api.getFocusObject()

		if focusObj.role == controlTypes.Role.LISTITEM:
			buffer = braille.handler.buffer
			messageBuffer = braille.handler.messageBuffer
			if buffer is not messageBuffer:
				HWUtils.emulateKeyPress("enter")
				# Our ListView Items are not compatible with UIAInvokePattern types. Our ListViewItems should support UIAutomation.
				# focusObj.doAction()
				return
		elif focusObj.role == controlTypes.Role.MENUITEM:
			# Only send enter if it's a submenu (has COLLAPSED state)
			if controlTypes.State.COLLAPSED in focusObj.states:
				buffer = braille.handler.buffer
				messageBuffer = braille.handler.messageBuffer
				if buffer is not messageBuffer:
					HWUtils.emulateKeyPress("enter")
					return

		globalCommands.commands.script_braille_routeTo(gesture)

	@script(
		description=_("Inputs braille dots via the braille keyboard"),
		category=SCRCAT_BRAILLE,
		gesture="bk:dots",
	)
	def script_braille_dots(self, gesture):
		if brailleTranslation.translationProvider and brailleTranslation.translationProvider.useComputerBrailleForInput():
			globalCommands.GlobalCommands.script_braille_dots(self, gesture)
			return

		# Use helper methods from commands instance if not available on self
		_isInBrowseMode = getattr(self, '_isInBrowseMode', None) or commands._isInBrowseMode
		_handleSpaceChordGesture = getattr(self, '_handleSpaceChordGesture', None) or commands._handleSpaceChordGesture

		if not _isInBrowseMode():
			# Try to handle as a space chord gesture
			if _handleSpaceChordGesture(gesture):
				return

		globalCommands.GlobalCommands.script_braille_dots(self, gesture)

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Erases the last entered braille cell or character"),
		category=SCRCAT_BRAILLE,
		gesture="bk:dot7",
	)
	def script_braille_eraseLastCell(self, gesture):
		globalCommands.GlobalCommands.script_braille_eraseLastCell(self, gesture)

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Translates any braille input and presses the enter key"),
		category=SCRCAT_BRAILLE,
		gesture="bk:dot8",
	)
	def script_braille_enter(self, gesture):
		globalCommands.GlobalCommands.script_braille_enter(self, gesture)

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Translates any braille input"),
		category=SCRCAT_BRAILLE,
		gesture="bk:dot7+dot8",
	)
	def script_braille_translate(self, gesture):
		globalCommands.GlobalCommands.script_braille_translate(self, gesture)

	@script(
		description=_("Moves to the previous available setting in the synth settings ring"),
		gesture=("br(hidBrailleStandard):space+dot1+dot8"),	# Enter+D1
	)
	def script_movePreviousVoiceSetting(self, gesture):
		globalCommands.GlobalCommands.script_previousSynthSetting(self, gesture)	# "kb(desktop):NVDA+control+leftArrow"

	@script(
		description=_("Moves to the next available setting in the synth settings ring"),
		gesture=("br(hidBrailleStandard):space+dot4+dot8"),	# Enter+D4
	)
	def script_moveNextVoiceSetting(self, gesture):
		globalCommands.GlobalCommands.script_nextSynthSetting(self, gesture)	# "kb(desktop):NVDA+control+rightArrow"

	@script(
		description=_("Decreases the currently active setting in the synth settings ring"),
		gesture=("br(hidBrailleStandard):space+dot3+dot8"),	# Enter+D3
	)
	def script_decreaseCurrentVoiceSetting(self, gesture):
		globalCommands.GlobalCommands.script_decreaseSynthSetting(self, gesture)	# "kb(desktop):NVDA+control+downArrow"

	@script(
		description=_("Increases the currently active setting in the synth settings ring"),
		gesture=("br(hidBrailleStandard):space+dot6+dot8"),	# Enter+D6
	)
	def script_increaseCurrentVoiceSetting(self, gesture):
		globalCommands.GlobalCommands.script_increaseSynthSetting(self, gesture)	# "kb(desktop):NVDA+control+upArrow"

	@script(
		# Translators: Input help message for toggle Braille grade command.
		description=_("Toggle Braille grade"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot5+dot7"),	# Backspace+G
	)
	def script_toggleBrailleGrade(self, gesture):
		focus = api.getFocusObject()
		supportsBRLUCX = (
			focus and focus.appModule
			and '_supportsBRLUCX' in type(focus.appModule).__dict__
		)
		# If the app supports BRLUCX, signal the IME to commit its word under cursor first.
		if supportsBRLUCX:
			if brailleInput.handler:
				brailleInput.handler.setBRLUCXEnabled(False)
			# Re-evaluate BRLUCX after the config has been updated by the gesture.
			core.callLater(100, focus.appModule.event_gainFocus, focus, lambda: None)
		HWUtils.emulateGestureWithVK('G', [(winUser.VK_CONTROL, False), (winUser.VK_MENU, False)])

	@script(
		# Translators: Input help message for Cut command.
		description=_("Cut"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot6+dot7"),	# Backspace+X
	)
	def script_cut(self, gesture):
		self.emulateKeyPressFromCommandName("cut")	# Ctrl+X

	@script(
		# Translators: Input help message for Copy command.
		description=_("Copy"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot6+dot7"),	# Backspace+Y
	)
	def script_copy(self, gesture):
		self.emulateKeyPressFromCommandName("copy")	# Ctrl+C

	@script(
		# Translators: Input help message for Paste command.
		description=_("Paste"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot6+dot7"),	# Backspace+V
	)
	def script_paste(self, gesture):
		self.emulateKeyPressFromCommandName("paste")	# Ctrl+V

	@script(
		# Translators: Input help message for Undo command.
		description=_("Undo"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot6+dot7"),	# Backspace+Z
	)
	def script_undo(self, gesture):
		self.emulateKeyPressFromCommandName("undo")	# Ctrl+Z

	@script(
		# Translators: Input help message for Redo command.
		description=_("Redo"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot6+dot8"),	# Enter+Z
	)
	def script_redo(self, gesture):
		self.emulateKeyPressFromCommandName("redo")	# Ctrl+Y

	@script(
		# Translators: Input help message for Save command.
		description=_("Save"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4"),	# Space+S
	)
	def script_save(self, gesture):
		self.emulateKeyPressFromCommandName("save")	# Ctrl+S

	@script(
		# Translators: Input help message for Save As command.
		description=_("Save as"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot7"),	# Backspace+S
	)
	def script_saveAs(self, gesture):
		self.emulateKeyPressFromCommandName("saveAs")	# F12

	@script(
		# Translators: Input help message for Delete command.
		description=_("Delete"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot6+dot7"),	# Backspace+D2356
	)
	def script_delete(self, gesture):
		HWUtils.emulateGesture("delete")

	@script(
		# Translators: Input help message for Select All command.
		description=_("Select all"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot5+dot6+dot8"),	# Enter+D123456
	)
	def script_selectAll(self, gesture):
		self.emulateKeyPressFromCommandName("selectAll")	# Ctrl+A

	@script(
		# Translators: Input help message for Print command.
		description=_("Print"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot6+dot8"),	# Enter+V
	)
	def script_print(self, gesture):
		self.emulateKeyPressFromCommandName("print")	# Ctrl+P

	@script(
		# Translators: Input help message for drive selection command.
		description=_("Drive selection"),
		gesture=("br(hidBrailleStandard):space+dot1+dot4+dot5"), # Space+D
	)
	def script_driveSelection(self, gesture):
		self.emulateKeyPressFromCommandName("driveSelection")	# Ctrl+D

	@script(
		# Translators: Input help message for Open context menu command.
		description=_("Open context menu"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4"),	# Space+M
	)
	def script_openContextMenu(self, gesture):
		HWUtils.emulateGesture("shift+f10")

	@script(
		# Translators: Input help message for Open context menu command.
		description=_("Open context menu"),
		gesture=("kb:shift+f10"),
	)
	def script_openContextMenuQwerty(self, gesture):
		gesture.send()

	@script(
		# Translators: Input help message for Alt key command.
		description=_("Alt"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A
	)
	def script_altKey(self, gesture):
		HWUtils.emulateGesture("alt")

	@script(
		gesture=("kb:tab"),
	)
	def script_tabKey(self, gesture):
		if brailleInput.handler.bufferBraille:
			def delayed_translate_and_tab():
				log.debug(f"Executing delayed translate")
				brailleInput.handler.translate()
				log.debug(f"Translate done, sending Tab")
				HWUtils.emulateTabKeyPress(withShift=False)

			# Delay 50ms to let Tab key be released before SendInput() is called
			wx.CallLater(50, delayed_translate_and_tab)
			return

		# No braille in buffer, use keybd_event for better wx dialog compatibility
		# This works even when shift is no longer physically pressed (Perkins firmware)
		HWUtils.emulateTabKeyPress(withShift=False)

	@script(
		gesture=("kb:shift+tab"),
	)
	def script_shiftTabKey(self, gesture):
		if brailleInput.handler.bufferBraille:
			def delayed_translate_and_shift_tab():
				log.debug(f"Executing delayed translate")
				brailleInput.handler.translate()
				log.debug(f"Translate done, sending Shift+Tab")
				HWUtils.emulateTabKeyPress(withShift=True)

			# Delay 50ms to let Tab key be released before SendInput() is called
			wx.CallLater(50, delayed_translate_and_shift_tab)
			return

		# No braille in buffer, use keybd_event for better wx dialog compatibility
		# This works even when shift is no longer physically pressed (Perkins firmware)
		HWUtils.emulateTabKeyPress(withShift=True)

	@script(
		# Translators: Input help message for Open Options menu command.
		description=_("Open Options menu"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5"),	# Space+O
	)
	def script_openOptionsMenu(self, gesture):
		# Use VK code (VK_O = 'O') for keyboard layout independence
		HWUtils.emulateGestureWithVK('O', [(winUser.VK_CONTROL, False), (winUser.VK_MENU, False)])

	@script(
		# Translators: Input help message for Open Options menu command.
		description=_("Open Options menu"),
		gesture=("kb:control+alt+o"),
	)
	def script_openOptionsMenuQwerty(self, gesture):
		gesture.send()

	@script(
		# Translators: Input help message for Spell Check command.
		description=_("Spell check"),
		gesture=("br(hidBrailleStandard):space+dot1+dot6"),	# Space+D16
	)
	def script_spellCheck(self, gesture):
		HWUtils.emulateGesture("f7")

	@script(
		# Translators: Input help message for Pass Next Key Through command.
		description=_(
			"The next key that is pressed will not be handled at all by NVDA, "
			"it will be passed directly through to Windows.",
		),
		gesture=("br(hidBrailleStandard):space+dot4+dot5+dot6+dot8"),	# Enter+D456
	)
	def script_passNextKeyThrough(self, gesture):
		globalCommands.GlobalCommands.script_passNextKeyThrough(self, gesture)	# "kb:NVDA+f2"

	@script(
		# Translators: Input help message for Start Selection command.
		description=_("Start selection"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot8"),	# Enter+S
	)
	def script_startSelection(self, gesture):
		emulatedGesture = EmulatedGesture("kb:NVDA+f9", gesture)
		globalCommands.GlobalCommands.script_review_markStartForCopy(self, emulatedGesture)  # "kb:NVDA+f9"

	@script(
		# Translators: Input help message for End Selection command.
		description=_("End selection"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot8"),	# Enter+E
	)
	def script_endSelection(self, gesture):
		# Need to call from this function to support the copy to clipboard.  (Timing)
		emulatedGesture = EmulatedGesture("kb:NVDA+f10", gesture)
		globalCommands.GlobalCommands.script_review_copy(self, emulatedGesture)  # "kb:NVDA+f10"

	@script(
		# Translators: Input help message for Play / Pause command.
		description=_("Play / pause"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot6+dot7+dot8"),	# Backspace+Enter+X
	)
	def script_playPause(self, gesture):
		HWUtils.emulateGesture("mediaplaypause")

	@script(
		# Translators: Input help message for Next Track command.
		description=_("Next track"),
		gesture=("br(hidBrailleStandard):space+dot4+dot6+dot7+dot8"),	# Backspace+Enter+D46
	)
	def script_nextTrack(self, gesture):
		HWUtils.emulateGesture("medianexttrack")

	@script(
		# Translators: Input help message for Previous Track command.
		description=_("Previous track"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot7+dot8"),	# Backspace+Enter+D13
	)
	def script_previousTrack(self, gesture):
		HWUtils.emulateGesture("mediaprevtrack")

	@script(
		# Translators: Input help message for Refresh command.
		description=_("Refresh"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot8"),	# Enter+R
	)
	def script_refresh(self, gesture):
		HWUtils.emulateGesture("f5")

	@script(
		# Translators: Input help message for Home key command.
		description=_("Home"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot8"),	# Enter+D13
	)
	def script_homeKey(self, gesture):
		HWUtils.emulateGesture("home")

	@script(
		# Translators: Input help message for End key command.
		description=_("End"),
		gesture=("br(hidBrailleStandard):space+dot4+dot6+dot8"),	# Enter+D46
	)
	def script_endKey(self, gesture):
		HWUtils.emulateGesture("end")

	@script(
		# Translators: Input help message for Control + Home key command.
		description=_("Control Home"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3"),	# Space+D123
	)
	def script_controlHomeKey(self, gesture):
		HWUtils.emulateGesture("control+home")

	@script(
		# Translators: Input help message for Control + End key command.
		description=_("Control End"),
		gesture=("br(hidBrailleStandard):space+dot4+dot5+dot6"),	# Space+D456
	)
	def script_controlEndKey(self, gesture):
		HWUtils.emulateGesture("control+end")

	@script(
		# Translators: Input help message for Page Down key command.
		description=_("Page Down"),
		gesture=("br(hidBrailleStandard):space+dot3+dot4+dot5+dot8"),	# Enter+D345
	)
	def script_pageDownKey(self, gesture):
		HWUtils.emulateGesture("pagedown")

	@script(
		# Translators: Input help message for Page Up key command.
		description=_("Page Up"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot6+dot8"),	# Enter+D126
	)
	def script_pageUpKey(self, gesture):
		HWUtils.emulateGesture("pageup")

	@script(
		# Translators: Input help message for Next Word command.
		description=_("Next Word"),
		gesture=("br(hidBrailleStandard):space+dot5"),
	)
	def script_braille_nextWord(self, gesture):
		HWUtils.emulateGesture("control+rightArrow")

	@script(
		# Translators: Input help message for Previous Word command.
		description=_("Previous Word"),
		gesture=("br(hidBrailleStandard):space+dot2"),
	)
	def script_braille_previousWord(self, gesture):
		HWUtils.emulateGesture("control+leftArrow")

	@script(
		# Translators: Input help message for Help key command.
		description=_("Help"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot5"),	# Space+H
	)
	def script_helpKey(self, gesture):
		HWUtils.emulateGesture("f1")

	@script(
		# Translators: Input help message for Cycle through screen elements command.
		description=_("Cycle through screen elements"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot7+dot8"),	# Backspace + Enter + lower F
	)
	def script_cycleScreenElements(self, gesture):
		HWUtils.emulateGesture("f6")

	@script(
		# Translators: Input help message for Next document command.
		description=_("Next document"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot5+dot6"),	# Space+D1256
	)
	def script_NextDocument(self, gesture):
		HWUtils.emulateGesture("control+f6")

	@script(
		# Translators: Input help message for Previous document command.
		description=_("Previous document"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot5+dot6+dot7"),	#  Backspace+D1256
	)
	def script_previousDocument(self, gesture):
		HWUtils.emulateGesture("control+shift+f6")

	@script(
		# Translators: Input help message for Close document command.
		description=_("Close document"),
		gesture=("br(hidBrailleStandard):space+dot2+dot4+dot5+dot6"),	#  Space+W
	)
	def script_closeDocument(self, gesture):
		HWUtils.emulateGestureWithVK('W', [(winUser.VK_CONTROL, False)])

	@script(
		# Translators: Input help message for Apps switcher command.
		description=_("App switcher shortcut"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5"),	# Space+D235
	)
	def script_appsSwitcherShortcut(self, gesture):
		HWUtils.emulateGesture("control+f12")

	@script(
		# Translators: Input help message for Apps switcher command.
		description=_("App switcher shortcut"),
		gesture=("kb:control+f12"),
	)
	def script_appsSwitcherShortcutQwerty(self, gesture):
		gesture.send()

	@script(
		# Translators: Input help message for Notifications Center command.
		description=_("Notification Center shortcut"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot8"),	# Enter+N
	)
	def script_notificationsCenterShortcut(self, gesture):
		HWUtils.emulateGestureWithVK('N', [(winUser.VK_LWIN, False)])

	@script(
		# Translators: Input help message for Windows Settings command.
		description=_("Windows Settings shortcut"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot5+dot8"),	# Enter+Q
	)
	def script_windowsSettingsShortcut(self, gesture):
		HWUtils.emulateGestureWithVK('I', [(winUser.VK_LWIN, False)])

	@script(
		gesture=("br(hidBrailleStandard):space+dot2+dot4+dot7+dot8"),	# Backspace+Enter+I
	)
	def script_toggleKeyboardLayoutShortcut(self, gesture):
		HWUtils.emulateGesture("leftwindows+space")

	@script(
		# Translators: Input help message for Quick Settings shortcut command.
		description=_("Quick Settings shortcut"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot5+dot7"),	# Backspace+Q
	)
	def script_quickSettingsShortcut(self, gesture):
		HWUtils.emulateGestureWithVK('A', [(winUser.VK_LWIN, False)])

	@script(
		# Translators: Input Help message for the browse mode elements list command.
		description=_("Elements list"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot5"),	# Space+T -> NVDA+F7
	)
	def script_elementsList(self, gesture):
		if self._isInBrowseMode():
			HWUtils.emulateGesture("nvda+f7")

	@script(
		# Translators: Input help message for Time and Date command.
		description=_("If pressed once, reports the current time. If pressed twice, reports the current date"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot5+dot8"),	# Enter+T
	)
	def script_sayTime(self, gesture):
		emulatedGesture = EmulatedGesture("kb:NVDA+f12", gesture)
		globalCommands.GlobalCommands.script_dateTime(self, emulatedGesture)  # "kb:NVDA+f12"

	@script(
		# Translators: Input help mode message for report current line command.
		description=_(
			"Reports the current line under the application cursor. "
			"Pressing this key twice will spell the current line. "
			"Pressing three times will spell the line using character descriptions.",
		),
		gesture=("br(hidBrailleStandard):space+dot1+dot4"),	# Space+C
	)
	def script_reportCurrentLine(self, gesture):
		emulatedGesture = EmulatedGesture("kb:NVDA+upArrow", gesture)
		globalCommands.GlobalCommands.script_reportCurrentLine(self, emulatedGesture)  # "NVDA+upArrow"

	@script(
		# Translators: Input help message for Cycle between speech modes command.
		description=_("Cycles between speech modes."),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot7+dot8"),	# Backspace+Enter+S
	)
	def script_toggleSpeechMode(self, gesture):
		emulatedGesture = EmulatedGesture("kb:NVDA+s", gesture)
		globalCommands.GlobalCommands.script_speechMode(self, emulatedGesture)	# NVDA+S

	@script(
		# Translators: Input help message for Battery status command.
		description=_("Reports battery status and time remaining if AC is not plugged in"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot8"),	# Enter+P
	)
	def script_batteryStatus(self, gesture):
		emulatedGesture = EmulatedGesture("kb:NVDA+shift+b", gesture)
		globalCommands.GlobalCommands.script_say_battery_status(self, emulatedGesture)  # "NVDA+shift+b"

	@script(
		# Translators: Input help message for Open Main Menu command.
		description=_("Open Main Menu"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot5+dot6") # Enter+D123456
	)
	def script_openMainMenu(self, gesture):
		HWUtils.emulateGestureWithVK('H', [(winUser.VK_CONTROL, False), (winUser.VK_MENU, False)])

	@script(
		# Translators: Input help message for Open Main Menu command.
		description=_("Open Main Menu"),
		gesture=("kb:control+alt+h")
	)
	def script_openMainMenuQwerty(self, gesture):
		gesture.send()

	@script(
		description=_(
			# Translators: Input help mode message for toggle Braille viewer command.
			"Toggles the NVDA Braille viewer, a floating window that allows you to view braille output, "
			"and the text equivalent for each braille character",
		),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot6+dot7+dot8"), # Backspace+Enter+D1236
	)
	def script_toggleBrailleViewer(self, gesture):
		globalCommands.GlobalCommands.script_toggleBrailleViewer(self, gesture)

	@script(
		description=_(
			# Translators: Input help mode message for toggle focus and browse mode command
			# in web browsing and other situations.
			"Toggles between browse mode and focus mode. "
			"When in focus mode, keys will pass straight through to the application, "
			"allowing you to interact directly with a control. "
			"When in browse mode, you can navigate the document with the cursor, quick navigation keys, etc.",
		),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot6+dot8"),	# Enter+D2356 -> execute the global command
	)
	def script_braille_toggleBrowseFocusModes(self, gesture):
		emulatedGesture = EmulatedGesture("kb:NVDA+space", gesture)
		globalCommands.GlobalCommands.script_toggleVirtualBufferPassThrough(self, emulatedGesture)

	@script(
		# Translators: Input help message for Select Language Profile command.
		description=_("Select Language Profile"),
		gestures=("kb:control+alt+l","br(hidBrailleStandard):space+dot1+dot2+dot3+dot8"), # Enter+L
	)
	def script_selectLanguageProfile(self, gesture):
		if _languageProfileDialog:
			_languageProfileDialog.handleSelectLanguageProfileShortcut()
		else:
			log.warning("Language profile dialog not available")

	@script(
		# Translators: Input help message for generate control + up arrow command.
		description=_("Generates control+upArrow"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3"),	# Space+D23
	)
	def script_generateControlUpArrow(self, gesture):
		HWUtils.emulateGesture("control+upArrow")

	@script(
		# Translators: Input help message for generate control + down arrow command.
		description=_("Generates control+downArrow"),
		gesture=("br(hidBrailleStandard):space+dot5+dot6"),	# Space+D56
	)
	def script_generateControlDownArrow(self, gesture):
		HWUtils.emulateGesture("control+downArrow")

	def _handleSpaceChordGesture(self, gesture) -> bool:
		"""Handle space chord gestures (dot 7 or 8 pressed with other dots).

		Args:
			gesture: The braille gesture to process.

		Returns:
			True if the gesture was handled, False otherwise.
		"""
		# Quick check for dots 7 or 8 using binary operations
		isDot7or8Pressed = gesture.dots & DOT_7_OR_8_MASK
		isMultipleDotsPressed = gesture.dots & (gesture.dots - 1)  # True if more than one bit is active

		# Validate the range of dot values
		if isDot7or8Pressed and isMultipleDotsPressed:
			# Build the list of pressed dots (1 to 8)
			dots_pressed = [str(i + 1) for i in range(8) if gesture.dots & (1 << i)]
			if not dots_pressed or any(int(d) < 1 or int(d) > 8 for d in dots_pressed):
				log.warning(f"Out-of-range dot value: {dots_pressed}")
				return True  # Gesture was handled (even if invalid)

			log.debug(f"Dot 7 or 8 detected, dots pressed: {dots_pressed}")

			# Build the gesture identifier with space
			dotsStr = "+".join([f"dot{d}" for d in dots_pressed])
			targetGestureId = f"br(hidBrailleStandard):space+{dotsStr}"

			# Special handling for sayTime gesture: detect script repetition manually
			if targetGestureId == "br(hidBrailleStandard):space+dot2+dot3+dot4+dot5+dot8":
				repeatCount = scriptHandler.getLastScriptRepeatCount()
				log.info(f"Time/Date gesture detected, repeat count: {repeatCount}")
				# Call script_sayTime directly to bypass gesture emulation issues
				self.script_sayTime(gesture)
				return True

			# Create the emulated gesture with the target identifier
			emulatedGesture = EmulatedGesture(targetGestureId, gesture)

			# Try to execute the gesture via the input manager
			try:
				log.info(f"Executing gesture {targetGestureId}")
				inputCore.manager.executeGesture(emulatedGesture)
				return True
			except inputCore.NoInputGestureAction:
				log.debug(f"No script found for {targetGestureId}, sending dots normally")

		return False  # Gesture was not handled

	def _isInBrowseMode(self) -> bool:
		"""Check if the current focus object is in browse mode.

		Returns:
			True if currently in browse mode, False otherwise.
		"""
		focusObj = api.getFocusObject()
		if not focusObj:
			return False

		# Check if the focus object has a tree interceptor (virtual buffer)
		treeInterceptor = focusObj.treeInterceptor
		if not treeInterceptor:
			return False

		# Check if browse mode is active
		# passThrough is False when in browse mode, True when in focus mode
		return hasattr(treeInterceptor, 'passThrough') and not treeInterceptor.passThrough

	def emulateKeyPressFromCommandName(self, commandName: str) -> None:
		"""Emulate a keyboard shortcut for a global command by its name.

		This function looks up the keyboard shortcut associated with a specific
		NVDA global command and emulates the corresponding key press.

		Args:
			commandName: The name of the global command to execute.
						 Examples: "cut", "copy", "paste", "undo", "redo",
						 "save", "selectAll", "print", etc.

		Examples:
			self.emulateKeyPressFromCommandName("copy")      # Executes Ctrl+C
			self.emulateKeyPressFromCommandName("paste")     # Executes Ctrl+V
			self.emulateKeyPressFromCommandName("selectAll") # Executes Ctrl+A

		Note:
			This method specifically targets GlobalCommands module, which contains
			the standard NVDA global commands and their keyboard shortcuts.
		"""
		HWUtils.emulateKeyPressFromCommandNameAndAppModuleName(self, commandName, "HumanwareCommands")



# Humanware Global instance to make the class accessible for gesture mapping
commands = HumanwareCommands()
