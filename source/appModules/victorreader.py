# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# VictorReader App Module for NVDA
# Provides enhanced braille and keyboard support for VictorReader application

import appModuleHandler
import appModules.HWUtils
import api
import controlTypes
import humanwareCommands

from scriptHandler import script
from logHandler import log
from keyboardHandler import KeyboardInputGesture

class AppModule(appModuleHandler.AppModule):
	"""
	App module for VictorReader application.
	Provides braille shortcuts for navigation, bookmarks, and reading controls.
	"""

	VALID_AUTOMATION_IDS = {
    	"BookTextContent",
    	"PlayPauseButton",
    	"PreviousButton",
    	"NextButton",
    	"BookmarksButton",
    	"TableOfContentButton"
	}

	# === INFORMATION AND NAVIGATION ===
	@script(
		# Translators: Input Help message for the "Where Am I" command.
		description=_("Where Am I"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot6"), # Space+D156
	)
	def script_braille_whereAmI(self, gesture):
		self._executeCommand("whereAmI")

	@script(
		# Translators: Input Help message for the "Book Info" command.
		description=_("Book info"),
		gesture=("br(hidBrailleStandard):space+dot2+dot4"), # Space+I
	)
	def script_braille_bookInfo(self, gesture):
		self._executeCommand("bookInfo")

	@script(
		# Translators: Input Help message for the "Table of Contents" command.
		description=_("Table of Contents"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot5"), # Space+T
	)
	def script_braille_tableOfContents(self, gesture):
		self._executeCommand("tableOfContents")

	@script(
		# Translators: Input Help message for the "Go To Page" command.
		description=_("Go to Page"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot5+dot8"), # Enter+G
	)
	def script_braille_goToPage(self, gesture):
		self._executeCommand("goToPage")

	# === SEARCH FUNCTIONS ===
	@script(
		# Translators: Input Help message for the "Find" command.
		description=_("Find"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"), # Space+F
	)
	def script_braille_find(self, gesture):
		self._executeCommand("find")

	@script(
		# Translators: Input Help message for the "Find Next" command.
		description=_("Find next"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"), # Space+N
	)
	def script_braille_findNext(self, gesture):
		self._executeCommand("findNext")

	@script(
		# Translators: Input Help message for the "Find Previous" command.
		description=_("Find previous"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"), # Space+P
	)
	def script_braille_findPrevious(self, gesture):
		self._executeCommand("findPrevious")

	# === KEYBOARD NAVIGATION ===
	@script(
		# Translators: Input Help message for the "Next Page" command.
		description=_("Next page from keyboard"),
		gesture=("kb:pageDown"),
	)
	def script_keyboard_nextPage(self, gesture):
		gesture.send()

	@script(
		# Translators: Input Help message for the "Previous Page" command.
		description=_("Previous page from keyboard"),
		gesture=("kb:pageUp"),
	)
	def script_keyboard_previousPage(self, gesture):
		gesture.send()

	@script(
		# Translators: Input Help message for the "Beginning of Book" command.
		description=_("Beginning of book from keyboard"),
		gesture=("kb:control+home"),
	)
	def script_keyboard_beginningOfBook(self, gesture):
		gesture.send()

	@script(
		# Translators: Input Help message for the "End of Book" command.
		description=_("End of book from keyboard"),
		gesture=("kb:control+end"),
	)
	def script_keyboard_endOfBook(self, gesture):
		gesture.send()

	@script(
		# Translators: Input Help message for the "Perform alt key" command.
		description=_("Perform alt"),
		gesture=("kb:alt"),
	)
	def script_keyboard_opensWindowsMenu(self, gesture):
		gesture.send()

	# === READING CONTROLS ===
	@script(
		# Translators: Input Help message for the "Up Arrow" command.
		description=_("Up Arrow"),
		gesture=("kb:upArrow"),
	)
	def script_upArrowQwerty(self, gesture):
		self.moveByLine(gesture)

	@script(
		# Translators: Input Help message for the "Down Arrow" command.
		description=_("Down Arrow"),
		gesture=("kb:downArrow"),
	)
	def script_downArrowQwerty(self, gesture):
		self.moveByLine(gesture)

	@script(
		# Translators: Input Help message for the "Left Arrow" command.
		description=_("Left Arrow"),
		gesture=("kb:leftArrow"),
	)
	def script_leftArrowQwerty(self, gesture):
		self.moveByCharacter(gesture)

	@script(
		# Translators: Input Help message for the "Right Arrow" command.
		description=_("Right Arrow"),
		gesture=("kb:rightArrow"),
	)
	def script_rightArrowQwerty(self, gesture):
		self.moveByCharacter(gesture)

	@script(
		# Translators: Input Help message for the "Next Sentence" command.
		description=_("Next Sentence"),
		gesture=("br(hidBrailleStandard):space+dot5+dot6"),	# Space+D56
	)
	def script_braille_nextSentence(self, gesture):
		self.moveByWordFromCommandName("nextSentence")

	@script(
		# Translators: Input Help message for the "Next Sentence" command.
		description=_("Next Sentence"),
		gesture=("kb:control+downArrow"),
	)
	def script_nextSentenceQwerty(self, gesture):
		self.moveByWord(gesture)

	@script(
		# Translators: Input Help message for the "Previous Sentence" command.
		description=_("Previous Sentence"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3"),	# Space+D23
	)
	def script_braille_previousSentence(self, gesture):
		self.moveByWordFromCommandName("previousSentence")

	@script(
		# Translators: Input Help message for the "Previous Sentence" command.
		description=_("Previous Sentence"),
		gesture=("kb:control+upArrow"),
	)
	def script_previousSentenceQwerty(self, gesture):
		self.moveByWord(gesture)

	@script(
		# Translators: Input Help message for the "Next Word" command.
		description=_("Next Word"),
		gesture=("br(hidBrailleStandard):space+dot5"),
	)
	def script_braille_nextWord(self, gesture):
		self.moveByWordFromCommandName("nextWord")

	@script(
		# Translators: Input Help message for the "Next Word" command.
		description=_("Next Word"),
		gesture=("kb:control+rightArrow"),
	)
	def script_nextWordQwerty(self, gesture):
		self.moveByWord(gesture)

	@script(
		# Translators: Input Help message for the "Previous Word" command.
		description=_("Previous Word"),
		gesture=("br(hidBrailleStandard):space+dot2"),
	)
	def script_braille_previousWord(self, gesture):
		self.moveByWordFromCommandName("previousWord")

	@script(
		# Translators: Input Help message for the "Previous Word" command.
		description=_("Previous Word"),
		gesture=("kb:control+leftArrow"),
	)
	def script_previousWordQwerty(self, gesture):
		self.moveByWord(gesture)

	@script(
		# Translators: Input Help message for the "Increase Speed" command.
		description=_("Increase Speed"),
		gesture=("br(hidBrailleStandard):space+dot5+dot8"),	# Enter+D5
	)
	def script_braille_increaseSpeed(self, gesture):
		self._executeCommand("increaseSpeed")

	@script(
		# Translators: Input Help message for the "Decrease Speed" command.
		description=_("Decrease Speed"),
		gesture=("br(hidBrailleStandard):space+dot2+dot8"),	# Enter+D2
	)
	def script_braille_decreaseSpeed(self, gesture):
		self._executeCommand("decreaseSpeed")

	@script(
		# Translators: Input Help message for the "Toggle Text and Audio Book" command.
		description=_("Toggle between text and audio book"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot6"),	# Space+D2356
	)
	def script_braille_toggleTextAndAudioBook(self, gesture):
		self._executeCommand("toggleTextAndAudioBook")

	# === BOOKMARK MANAGEMENT ===
	@script(
		# Translators: Input Help message for the "Insert Bookmark" command.
		description=_("Insert bookmark"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot8"),	# Enter+B
	)
	def script_braille_bookmarkInsert(self, gesture):
		self._executeCommand("bookmarkInsert")

	@script(
		# Translators: Input Help message for the "Jump to Bookmark" command.
		description=_("Jump to bookmark"),
		gesture=("br(hidBrailleStandard):space+dot2+dot4+dot5+dot8"),	# Enter+J
	)
	def script_braille_jumpToBookmark(self, gesture):
		self._executeCommand("jumpToBookmark")

	@script(
		# Translators: Input Help message for the "Bookmark List" command.
		description=_("Bookmark list"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7"),	# Backspace+L
	)
	def script_braille_bookmarkList(self, gesture):
		self._executeCommand("bookmarkList")

	@script(
		# Translators: Input Help message for the "Rename Bookmark" command.
		description=_("Rename bookmark"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot7"),	# Backspace+R
	)
	def script_braille_renameBookmark(self, gesture):
		self._executeCommand("renameBookmark")

	# Removed for now Backspace+D2356 will be globally used for "Delete", find new shortcut when feature is ready to implement
	# @script(
	# 	description=_("Delete Bookmark"),
	# 	gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot6+dot7"),	# Backspace+D2356
	# )
	# def script_braille_deleteBookmark(self, gesture):
	# 	self._executeCommand("deleteBookmark")

	# === HEADING NAVIGATION ===
	@script(
		description=_("Inputs braille dots via the braille keyboard"),
		category=_("Braille"),
		gesture="bk:dots",
	)
	def script_braille_dots(self, gesture):
		obj = api.getFocusObject()

		if hasattr(obj, 'UIAAutomationId') and obj.UIAAutomationId in self.VALID_AUTOMATION_IDS:
			# Decode which dots are pressed
			dots_pressed = []
			for i in range(8):  # 8 dots (1-8)
				if gesture.dots & (1 << i):
					dots_pressed.append(str(i + 1))

			# Check for specific dot combinations
			if len(dots_pressed) == 1 and '2' in dots_pressed:
				# Dot 2 only -> simulate "1"
				appModules.HWUtils.emulateKeyPress("1")
				log.info("Next heading 1 simulated via braille dot 2")
				return
			elif len(dots_pressed) == 2:
				if '2' in dots_pressed and '3' in dots_pressed:
					# Dots 2 and 3 -> simulate "2"
					appModules.HWUtils.emulateKeyPress("2")
					log.info("Next heading 2 simulated via braille dots 2 and 3")
					return
				elif '2' in dots_pressed and '5' in dots_pressed:
					# Dots 2 and 5 -> simulate "3"
					appModules.HWUtils.emulateKeyPress("3")
					log.info("Next heading 3 simulated via braille dots 2 and 5")
					return
				elif '1' in dots_pressed and '3' in dots_pressed:
					# Dots 1 and 3 -> simulate "k"
					appModules.HWUtils.emulateKeyPress("k")
					log.info("Play/Pause 'k' simulated via braille dots 1 and 3")
					return
			elif len(dots_pressed) == 3:
				if '1' in dots_pressed and '2' in dots_pressed and '3' in dots_pressed:
					# Dots 1, 2 and 3 -> simulate "l"
					appModules.HWUtils.emulateKeyPress("l")
					log.info("Jump forward 'l' simulated via braille dots 1, 2 and 3")
					return
				elif '2' in dots_pressed and '4' in dots_pressed and '5' in dots_pressed:
					# Dots 2, 4 and 5 -> simulate "j"
					appModules.HWUtils.emulateKeyPress("j")
					log.info("Jump backward 'j' simulated via braille dots 2, 4 and 5")
					return
				elif '1' in dots_pressed and '2' in dots_pressed and '5' in dots_pressed:
					# Dots 1, 2 and 5 -> simulate "h"
					appModules.HWUtils.emulateKeyPress("h")
					log.info("Next heading 'h' simulated via braille dots 1, 2 and 5")
					return
			elif len(dots_pressed) == 4:
				if '1' in dots_pressed and '2' in dots_pressed and '3' in dots_pressed and '4' in dots_pressed:
					# Dots 1, 2, 3 and 4 -> simulate "p"
					appModules.HWUtils.emulateKeyPress("p")
					log.info("Previous navigation level 'p' simulated via braille dots 1, 2, 3 and 4")
					return
				elif '1' in dots_pressed and '3' in dots_pressed and '4' in dots_pressed and '5' in dots_pressed:
					# Dots 1, 3, 4 and 5 -> simulate "n"
					appModules.HWUtils.emulateKeyPress("n")
					log.info("Next navigation level 'n' simulated via braille dots 1, 3, 4 and 5")
					return
				elif '2' in dots_pressed and '3' in dots_pressed and '4' in dots_pressed and '5' in dots_pressed:
					# Dots 2, 3, 4 and 5 -> simulate "t"
					appModules.HWUtils.emulateKeyPress("t")
					log.info("Navigation level 't' simulated via braille dots 2, 3, 4 and 5")
					return

		humanwareCommands.HumanwareCommands.script_braille_dots(self, gesture)

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Erases the last entered braille cell or character"),
		category=_("Braille"),
		gesture="bk:dot7",
	)
	def script_braille_eraseLastCell(self, gesture):
		humanwareCommands.HumanwareCommands.script_braille_eraseLastCell(self, gesture)

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Translates any braille input and presses the enter key"),
		category=_("Braille"),
		gesture="bk:dot8",
	)
	def script_braille_enter(self, gesture):
		humanwareCommands.HumanwareCommands.script_braille_enter(self, gesture)

	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Translates any braille input"),
		category=_("Braille"),
		gesture="bk:dot7+dot8",
	)
	def script_braille_translate(self, gesture):
		humanwareCommands.HumanwareCommands.script_braille_translate(self, gesture)

	@script(
		# Translators: Input Help message for the "Previous Heading" command.
		description=_("Previous heading"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot5+dot7"),	# Backspace+h -> Shift+h
	)
	def script_braille_previousHeading(self, gesture):
		appModules.HWUtils.emulateKeyPress("shift+h")

	@script(
		# Translators: Input Help message for the "Previous Heading 1" command.
		description=_("Previous heading 1"),
		gesture=("br(hidBrailleStandard):space+dot2+dot7"),	# Backspace+1 -> Shift+1
	)
	def script_braille_previousHeading1(self, gesture):
		self._navigateToPreviousHeading(1, gesture)

	@script(
		# Translators: Input Help message for the "Previous Heading 2" command.
		description=_("Previous heading 2"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot7"),	# Backspace+2 -> Shift+2
	)
	def script_braille_previousHeading2(self, gesture):
		self._navigateToPreviousHeading(2, gesture)

	@script(
		# Translators: Input Help message for the "Previous Heading 3" command.
		description=_("Previous heading 3"),
		gesture=("br(hidBrailleStandard):space+dot2+dot5+dot7"),	# Backspace+3 -> Shift+3
	)
	def script_braille_previousHeading3(self, gesture):
		self._navigateToPreviousHeading(3, gesture)

	# === HELPER METHODS ===
	def _navigateToPreviousHeading(self, level, gesture):
		"""
		Navigate to previous heading of specified level.

		Args:
			level (int): Heading level (1-3)
			gesture: Input gesture object
		"""
		obj = api.getFocusObject()
		if obj.UIAAutomationId == "BookTextContent":
			log.info(f"Navigating to previous heading level {level} via braille gesture")
			appModules.HWUtils.emulateKeyPress(f"control+{level}")

	def _executeCommand(self, commandName):
		"""
		Execute a VictorReader command by name.

		Args:
			commandName (str): Name of the command to execute
		"""
		appModules.HWUtils.emulateKeyPressFromCommandName(self, commandName)

	def moveByCharacter(self, gesture):
		obj = api.getFocusObject()

		if obj.role == controlTypes.Role.EDITABLETEXT:
			try:
				if hasattr(obj, 'script_caret_moveByCharacter'):
					obj.script_caret_moveByCharacter(gesture)
			except Exception as e:
				log.error(f"Error calling EditableText methods: {e}")
		else:
			gesture.send()

	def moveByWordFromCommandName(self, commandName):
		kbIdentifier = appModules.HWUtils.getShortcutFromCommandName(self, commandName)
		gesture = KeyboardInputGesture.fromName(kbIdentifier)
		self.moveByWord(gesture)

	def moveByWord(self, gesture):
		obj = api.getFocusObject()

		if obj.role == controlTypes.Role.EDITABLETEXT:
			try:
				if hasattr(obj, 'script_caret_moveByWord'):
					obj.script_caret_moveByWord(gesture)
			except Exception as e:
				log.error(f"Error calling EditableText methods: {e}")
		else:
			gesture.send()

	def moveBySentence(self, gesture):
		obj = api.getFocusObject()

		if obj.role == controlTypes.Role.EDITABLETEXT:
			try:
				if hasattr(obj, 'script_caret_nextSentence'):
					obj.script_caret_nextSentence(gesture)
			except Exception as e:
				log.error(f"Error calling EditableText methods: {e}")
		else:
			gesture.send()

	def moveByLine(self, gesture):
		obj = api.getFocusObject()

		if obj.role == controlTypes.Role.EDITABLETEXT:
			try:
				if hasattr(obj, 'script_caret_moveByLine'):
					obj.script_caret_moveByLine(gesture)
			except Exception as e:
				log.error(f"Error calling EditableText methods: {e}")
		else:
			gesture.send()
