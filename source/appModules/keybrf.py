# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# KeyBrf App Module for NVDA

import appModuleHandler
import appModules.HWUtils
from scriptHandler import script
import textInfos
import controlTypes
from NVDAObjects.behaviors import EditableTextWithAutoSelectDetection

# Constants for line endings and page breaks
CRLF = "\r\n"  # Windows line ending
LF = "\n"      # Unix/Mac line ending
PAGE_BREAK = "\x0c"  # Form feed / page break character


class EditableTextWithCorrectEmptyLineHandling(EditableTextWithAutoSelectDetection):
	"""EditableText with correct empty line handling, similar to Scintilla."""

	def makeTextInfo(self, position):
		"""Override makeTextInfo to create our custom TextInfo."""
		info = super().makeTextInfo(position)
		# Return our custom TextInfo
		return CorrectedTextInfo(info)

	def _caretScriptPostMovedHelper(self, speakUnit, gesture, info=None):
		"""Override to pass the correct object to review.handleCaretMove."""
		from scriptHandler import isScriptWaiting, willSayAllResume
		import speech
		import braille
		import review
		import controlTypes

		if isScriptWaiting():
			return
		if not info:
			try:
				info = self.makeTextInfo(textInfos.POSITION_CARET)
			except:
				return

		# Forget the word currently being typed as the user has moved the caret somewhere else.
		speech.clearTypedWordBuffer()

		# Pass the NVDA object to review.handleCaretMove, not the TextInfo
		review.handleCaretMove(self)

		if speakUnit and not willSayAllResume(gesture):
			expandedInfo = info.copy()
			expandedInfo.expand(speakUnit)
			speech.speakTextInfo(expandedInfo, unit=speakUnit, reason=controlTypes.OutputReason.CARET)

		braille.handler.handleCaretMove(self)


class CorrectedTextInfo:
	"""Wrapper for TextInfo that corrects empty lines."""

	def __init__(self, textInfo):
		self._textInfo = textInfo
		self._isCorrected = False

	def __getattr__(self, name):
		"""Delegate all attributes/methods to the original TextInfo."""
		return getattr(self._textInfo, name)

	def copy(self):
		"""Return a copy of this wrapper."""
		return CorrectedTextInfo(self._textInfo.copy())

	def expand(self, unit):
		"""Override expand to correct empty lines."""
		self._textInfo.expand(unit)

		# Special correction for lines
		if unit == textInfos.UNIT_LINE:
			text = self._textInfo.text

			# Case 1: Empty line that starts with a special character (CRLF, LF, or PAGE_BREAK)
			if text.startswith(CRLF) or text.startswith(LF) or text.startswith(PAGE_BREAK):
				# Determine the minimum length based on what character(s) it starts with
				if text.startswith(CRLF):
					minLen = 2  # More than just \r\n
				else:
					minLen = 1  # More than just \n or \x0c

				if len(text) > minLen:
					# Adjust to include only the empty line part
					self._textInfo.collapse()
					self._textInfo.expand(textInfos.UNIT_CHARACTER)
					# Try to include all line ending characters
					try:
						tempInfo = self._textInfo.copy()
						tempInfo.move(textInfos.UNIT_CHARACTER, 1)
						if tempInfo.text == LF:
							self._textInfo.setEndPoint(tempInfo, "endToEnd")
					except:
						pass
					self._isCorrected = True

			# Case 2: Normal line that ends with \r\n but includes text from next line
			elif CRLF in text:
				# Find the position of \r\n
				lineBreakPos = text.find(CRLF)

				# Check if there's text after \r\n (text from next line)
				if lineBreakPos >= 0 and lineBreakPos + 2 < len(text):
					try:
						# Create a new TextInfo that ends at the line break
						correctedInfo = self._textInfo.copy()
						correctedInfo.collapse()

						# Move character by character until we reach \r\n inclusive
						for i in range(lineBreakPos + 2):
							tempInfo = correctedInfo.copy()
							tempInfo.move(textInfos.UNIT_CHARACTER, 1)
							correctedInfo.setEndPoint(tempInfo, "endToEnd")

						# Replace our TextInfo with the corrected one
						self._textInfo = correctedInfo
						self._isCorrected = True
					except:
						pass

	@property
	def text(self):
		"""Return the text from the original TextInfo."""
		return self._textInfo.text


class AppModule(appModuleHandler.AppModule):

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		"""Apply correct empty line handling to editable controls."""
		if (obj.role == controlTypes.Role.EDITABLETEXT):
			# Insert our custom class at the beginning of the list
			clsList.insert(0, EditableTextWithCorrectEmptyLineHandling)

	@script(
		description=_("New file"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot7"), # Backspace+B
	)
	def script_braille_newFile(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "new")

	@script(
		description=_("Open file"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot7"),	# Backspace+O
	)
	def script_braille_openFile(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "open")

	@script(
		description=_("Close file"),
		gesture=("br(hidBrailleStandard):space+dot2+dot4+dot5+dot6"),	#  Space+W
	)
	def script_braille_closeFile(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "close")

	@script(
		# Translators: Input Help message for the read mode/edit mode command.
		description=_("Read Mode/Edit Mode"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot6"),	# Space+X
	)
	def script_braille_readMode(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "readModeEditMode")

	@script(
		description=_("Where am I"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot6"),	# Space+D156
	)
	def script_braille_whereAmI(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "whereAmI")

	@script(
		description=_("Find"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space+F
	)
	def script_braille_find(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "find")

	@script(
		description=_("Find next"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"),	# Space+N
	)
	def script_braille_findNext(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "findNext")

	@script(
		description=_("Find previous"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"),	# Space+P
	)
	def script_braille_findPrevious(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "findPrevious")

	@script(
		description=_("Replace"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"),	# Backspace+F
	)
	def script_braille_replace(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "replace")

	@script(
		# Translators: Input Help message for the replace and find next command.
		description=_("Replace and find next"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot7"),	# Backspace+N
	)
	def script_braille_replaceAndFindNext(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "replaceNext")

	@script(
		# Translators: Input Help message for the replace and find previous command.
		description=_("Replace and find previous"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4+dot7"),	# Backspace+P
	)
	def script_braille_replaceAndFindPrevious(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "replacePrevious")

	@script(
		# Translators: Input Help message for the bookmark menu command.
		description=_("Bookmark Menu"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot8"),	# Enter+M
	)
	def script_braille_bookmarkMenu(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "bookmarkMenu")

	@script(
		description=_("Insert bookmark"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot8"),	# Enter+B
	)
	def script_braille_bookmarkInsert(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "bookmarkInsert")

	@script(
		description=_("Jump to Bookmark"),
		gesture=("br(hidBrailleStandard):space+dot2+dot4+dot5+dot8"),	# Enter+J
	)
	def script_braille_bookmarkJumpTo(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "bookmarkJump")

	# Removed for now Backspace+D2356 will be globally used for "Delete", find new shortcut when feature is ready to implement
	# @script(
	# 	description=_("Remove Bookmark"),
	# 	gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot6+dot7"),	# Backspace+D2356
	# )
	# def script_braille_bookmarkRemove(self, gesture):
	# 	appModules.HWUtils.emulateKeyPressFromCommandName(self, "bookmarkRemove")
