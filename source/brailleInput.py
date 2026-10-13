# This file was modified for the BrailleNote evolve
# Technologies Humanware 2026

# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2012-2025 NV Access Limited, Rui Batista, Babbage B.V., Julien Cochuyt, Leonard de Ruijter

import time
import unicodedata
from typing import Optional, List, Set

import NVDAHelper
import treeInterceptorHandler
import config
from config.configFlags import TypingEcho
import core
from logHandler import log
from NVDAState import WritePaths
import winUser
import winBindings.user32
import inputCore
import speech
import textInfos
import ui
import keyboardHandler
import api
from baseObject import AutoPropertyObject
import keyLabels
import struct
import brailleTranslation
#import louis
import brailleTables
import braille
import sys
import os

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
	import brailleImeNamedPipe  # type: ignore  # dynamically added to sys.path
except ImportError:
	log.warning("Could not import brailleImeNamedPipe from BrailleNoteEvolve addon")
	brailleImeNamedPipe = None


"""Framework for handling braille input from the user.
All braille input is represented by a {BrailleInputGesture}.
Normally, all that is required is to create and execute a L{BrailleInputGesture},
as there are built-in gesture bindings for braille input.
"""

FALLBACK_TABLE = config.conf.getConfigValidation(("braille", "inputTable")).default
"""Table to use if the input table configuration is invalid."""

DOT7 = 1 << 6
DOT8 = 1 << 7
#: This bit flag must be added to all braille cells when using liblouis with dotsIO.
LOUIS_DOTS_IO_START = 0x8000
#: The start of the Unicode braille range.
#: @type: int
UNICODE_BRAILLE_START = 0x2800
#: The Unicode braille character to use when masking cells in protected fields.
#: @type: str
UNICODE_BRAILLE_PROTECTED = "⣿"  # All dots down

#: Prefix of the description string registered by BrailleIME via GetLanguageProfileDescription.
#: Used to identify BrailleIME from TSF lang-change notifications.
BRAILLE_IME_DESCRIPTION_PREFIX = "Braille IME"


class BrailleInputHandler(AutoPropertyObject):
	"""Handles braille input."""

	bufferBraille: List[int]
	bufferText: str
	cellsWithText: Set[int]
	untranslatedBraille: str
	untranslatedStart: int
	untranslatedCursorPos: int
	_uncontSentTime: Optional[float]
	currentModifiers: Set[str]
	unicodeBrailleInput: bool
	nativeBrailleRequired: bool
	brlucxEnabled: bool
	_inBrowseMode: bool

	def __init__(self):
		super().__init__()
		self._table: brailleTables.BrailleTable = brailleTables.getTable(FALLBACK_TABLE)
		#: A buffer of entered braille cells so that state set by previous cells can be maintained;
		#: e.g. capital and number signs.
		self.bufferBraille = []
		#: The text translated so far from the cells in L{bufferBraille}.
		self.bufferText = ""
		#: Indexes of cells which produced text.
		#: For example, this includes letters and numbers, but not number signs,
		#: since a number sign by itself doesn't produce text.
		#: This is used when erasing cells to determine when to backspace an actual character.
		self.cellsWithText = set()
		#: The cells in L{bufferBraille} that have not yet been translated
		#: or were translated but did not produce any text.
		#: This is used to show these cells to the user while they're entering braille.
		#: This is a string of Unicode braille.
		self.untranslatedBraille = ""
		#: The position in L{brailleBuffer} where untranslated braille begins.
		self.untranslatedStart = 0
		#: The user's cursor position within the untranslated braille.
		#: This enables the user to move within the untranslated braille.
		self.untranslatedCursorPos = 0
		#: The time at which uncontracted characters were sent to the system.
		self._uncontSentTime = None
		#: The modifiers currently being held virtually to be part of the next braille input gesture.
		self.currentModifiers = set()
		#different modes for braille input
		self.unicodeBrailleInput = False
		self.nativeBrailleRequired = False
		#Braille Under Cursor Translation
		self.brlucxEnabled = False
		self._inBrowseMode = False
		#: Set authoritatively by _onInputLangChanged from the TSF layoutString.
		#: None = no lang-change notification received yet; False = regular keyboard; True = BrailleIME.
		self._brailleImeActive: Optional[bool] = None
		self._brailleImeSpeechCells: List[int] = []
		self.handlePostConfigProfileSwitch()
		config.post_configProfileSwitch.register(self.handlePostConfigProfileSwitch)
		NVDAHelper.inputLangChanged.register(self._onInputLangChanged)

	table: brailleTables.BrailleTable
	"""Type definition for auto prop '_get_table/_set_table'"""

	def _get_table(self) -> brailleTables.BrailleTable:
		"""The translation table to use for braille input."""
		return self._table

	def _set_table(self, table: brailleTables.BrailleTable):
		self._table = table
		config.conf["braille"]["inputTable"] = table.fileName

	# Provided by auto property: L{_get_currentFocusIsTextObj}
	currentFocusIsTextObj: bool

	def _get_currentFocusIsTextObj(self):
		focusObj = api.getFocusObject()
		return focusObj._hasNavigableText and (
			not focusObj.treeInterceptor or focusObj.treeInterceptor.passThrough
		)

	# Provided by auto property: L{_get_useContractedForCurrentFocus}
	useContractedForCurrentFocus: bool

	def _get_useContractedForCurrentFocus(self):
		#need to involve brailleTranslation
		#"contracted" entry or not is up to the brailleTranslationProvider
		# contracted also isn't the right concept.
		# should be computer braille vs literary braille. Because in G1, number signs, capitals don't make for a 1 to 1 and require backtranslation of the whole
		return brailleTranslation.translationProvider.useLiteraryBrailleForInput() and self.currentFocusIsTextObj and not self.currentModifiers
		#return self._table.contracted and self.currentFocusIsTextObj and not self.currentModifiers

	def _setUnicodeBrailleInput(self , active: bool):
		"""Requests to enable or disable the Unicode Braille entry mode
		"""
		self.unicodeBrailleInput = active


	#unicode braille input but with a subtle more...
	#difference is mostly about the final intent of that braille. Is it getting transformed to text or kept as braille
	#and that's to deal with IME setting the mode, without knowledge of context or user prefs, and we need to taylor a response to that request
	#so that the content remains as braille, (disable some parts of its brlucx mechanism)
	#that's a bit clunky. ""
	#
	def _setNativeBrailleInputRequired(self , active: bool, announce: bool):
		"""Requests to enable or disable the native braille (which forces Unicode Braille entry) mode
		announcing a feedback about this action is conditional to that bool param.
		"""
		#keep track of that context
		self.nativeBrailleRequired = active

		#activating native braille also activates the unicode braille input
		#but deactivating it doesn't necessarily need to turn unicode braille input off.
		if active:
			#when in native braille, we want to deactivate brlucx
			self.setBRLUCXEnabled(False)
			#set the braille input mode, which may have been lost by prev call.
			self._setUnicodeBrailleInput(active)


		#if we deactivate native braille, but we're still in blrucx, then don't turn off the unicode braille
		elif self.brlucxEnabled :
			self._setUnicodeBrailleInput(True)
		else: #default
			self._setUnicodeBrailleInput(False)

		if announce:
			if self.nativeBrailleRequired:
				#only announce if we're not in the right entry
				if brailleTranslation.translationProvider.useComputerBrailleForInput():
					# Translators: announcement for interaction with a braille edit box
					ui.message(_("A Braille entry is required"))
			else:
				# Translators: announcement for turning off the native braille
				ui.message(_("Native Braille off"))
		log.info("Native Braille %s" %self.nativeBrailleRequired )


	def _onInputLangChanged(self, threadID: int, hkl: int, layoutString: str):
		"""Called when the active input language or method changes.
		Updates the cached BrailleIME active state from the authoritative layoutString,
		then adjusts BRLUCX if the focused app supports it.
		"""
		log.debug("_onInputLangChanged: threadID=%s hkl=%s layoutString=%s" % (threadID, hkl, layoutString))
		# Determine IME state from layoutString.
		# Plain keyboard layouts produce hex strings like "00000409".
		# BrailleIME produces "Braille IME (English - Canada)".
		try:
			int(layoutString, 16)
			is_hex = True
		except (ValueError, TypeError):
			is_hex = False
		self._brailleImeActive = (not is_hex and layoutString.startswith(BRAILLE_IME_DESCRIPTION_PREFIX))
		# Only adjust BRLUCX if the current app supports it.
		focus = api.getFocusObject()
		if not focus or not focus.appModule:
			return
		if '_supportsBRLUCX' not in type(focus.appModule).__dict__:
			return
		self.setBRLUCXEnabled(self._brailleImeActive)

	def _onBrowseModeStateChange(self, browseMode: bool):
		"""Called when browse mode is toggled. Notifies the IME to claim/release context."""
		self._inBrowseMode = browseMode
		focus = api.getFocusObject()
		if not focus or not focus.appModule:
			return
		if '_supportsBRLUCX' not in type(focus.appModule).__dict__:
			return
		# In browse mode (browseMode=True), NVDA claims context; in focus mode, it releases.
		self._setUnicodeBrailleInput(not browseMode)
		if brailleImeNamedPipe:
			try:
				pipe_client = brailleImeNamedPipe.get_pipe_client()
				if browseMode:
					pipe_client.notify_brlucx_disabled()
				else:
					pipe_client.notify_brlucx_enabled()
			except Exception as e:
				log.debug(f"Failed to notify IME of browse mode state change: {e}")

	def _canEnableBRLUCX(self) -> bool:
		"""Returns True if all conditions allow BRLUCX to be enabled, logging the reason if not."""
		if not self._brailleImeActive:
			log.info("requesting BRLUCX but IME is not activated")
			return False
		if brailleTranslation.translationProvider and brailleTranslation.translationProvider.useComputerBrailleForInput():
			log.info("requesting BRLUCX but we're in computer braille")
			return False
		if self._inBrowseMode:
			log.info("requesting BRLUCX but we're in browse mode")
			return False
		return True

	def setBRLUCXEnabled(self, active: bool):
		if active:
			active = self._canEnableBRLUCX()

		# Notify the IME about the state change (fire and forget)
		if brailleImeNamedPipe:
			try:
				pipe_client = brailleImeNamedPipe.get_pipe_client()
				if active:
					pipe_client.notify_brlucx_enabled()
				else:
					pipe_client.notify_brlucx_disabled()
			except Exception as e:
				log.info(f"Failed to notify IME about brlucx state change: {e}")
				active = False
		else:
			log.info("brailleImeNamedPipe module not available")

		self.brlucxEnabled = active
		#brlucxEnabled implies unicode braille input enabled
		#but if not enabled, that doesn't mean we can't be in unicode braille input
		if active:
			self._setUnicodeBrailleInput(self.brlucxEnabled)

		log.info("==>setBRLUCX %s" % self.brlucxEnabled)




	def _translate(self, endWord: bool) -> bool:
		"""Translate buffered braille up to the cursor.
		Any text produced is sent to the system.
		@param endWord: C{True} if this is the end of a word, C{False} otherwise.
		@return: C{True} if translation produced text, C{False} if not.
		"""
		assert not self.useContractedForCurrentFocus or endWord, (
			"Must only translate contracted at end of word"
		)
		if self.useContractedForCurrentFocus:
			# self.bufferText has been used by _reportContractedCell, so clear it.
			self.bufferText = ""
		oldTextLen = len(self.bufferText)
		pos = self.untranslatedStart + self.untranslatedCursorPos


		if self.unicodeBrailleInput:
			log.debug("retain braille")
			self.bufferText = u"".join([chr(cell | UNICODE_BRAILLE_START ) for cell in self.bufferBraille[:pos]])
			self.bufferText = self.bufferText.replace('\u2800', ' ')
		else:
			#backtranslation
			#Todo: abstract translators
			#according to liblouis doc, backtranslate is capable of detecting Unicode Braille in the input
			#so we can ignore the dotsIO mask...
			data = u"".join([chr(cell | UNICODE_BRAILLE_START) for cell in self.bufferBraille[:pos]])

			# mode = louis.dotsIO | louis.noUndefinedDots
			mode = 0
			#if (not self.currentFocusIsTextObj or self.currentModifiers) and self._table.contracted:
			# 	mode |= louis.partialTrans
			if (not self.currentFocusIsTextObj or self.currentModifiers) and brailleTranslation.translationProvider.useLiteraryBrailleForInput():
				mode |= brailleTranslation.partialTranslation
			# self.bufferText = louis.backTranslate(
			# 	[self._table.fileName, "braille-patterns.cti"],
			# 	data,
			# 	mode=mode,
			# 	)[0]
			self.bufferText = brailleTranslation.translationProvider.backTranslate(data, mode=mode)





		newText = self.bufferText[oldTextLen:]
		if newText:
			# New text was generated by the cells just entered.
			if self.useContractedForCurrentFocus or self.currentModifiers:
				# For contracted braille, an entire word is sent at once.
				# Don't speak characters as this is sent.
				# Also, suppress typed characters when emulating a command gesture.
				if not self.unicodeBrailleInput or self.currentModifiers:
					speech._suppressSpeakTypedCharacters(len(newText))
			else:
				self._uncontSentTime = time.time()
			self.untranslatedStart = pos
			self.untranslatedCursorPos = 0
			if self.currentModifiers or not self.currentFocusIsTextObj:
				if len(newText) > 1:
					# Emulation of multiple characters at once is unsupported
					# Clear newText, so this function returns C{False} if not at end of word
					newText = ""
				else:
					self.emulateKey(newText)
			else:
				self.sendChars(newText)

		if endWord or (newText and (not self.currentFocusIsTextObj or self.currentModifiers)):
			# We only need to buffer one word.
			# Clear the previous word (anything before the cursor) from the buffer.
			del self.bufferBraille[:pos]
			self.bufferText = ""
			self.cellsWithText.clear()
			self.currentModifiers.clear()
			self.untranslatedStart = 0
			self.untranslatedCursorPos = 0

		if newText or endWord:
			self._updateUntranslated()
			return True

		return False

	def _translateForReportContractedCell(self, pos):
		"""Translate text for current input as required by L{_reportContractedCell}.
		@return: The previous translated text.
		@rtype: str
		"""
		cells = self.bufferBraille[: pos + 1]
		oldText = self.bufferText

		if self.unicodeBrailleInput:
			text = u"".join([chr(cell | UNICODE_BRAILLE_START) for cell in cells])
			self.bufferText = self.bufferText.replace('\u2800', ' ')

		else:
			#backtranslation
			# data = "".join([chr(cell | LOUIS_DOTS_IO_START) for cell in cells])
			# text = louis.backTranslate(
			# 	[self._table.fileName, "braille-patterns.cti"],
			# 	data,
			# 	mode=louis.dotsIO | louis.noUndefinedDots | louis.partialTrans,
			# )[0]

			#in that case, the partialTrans is important, that's what prevents "b" to be announced as "b u t" while typing
			#need to abstract that... because it's very liblouis specific
			#
			#

			""" partialTrans
			This flag specifies that back-translation input should be treated as an incomplete word.
			Rules that apply only for complete words or at the end of a word will not take effect.
			This is intended to be used when translating input typed on a braille keyboard to provide
			a rough idea to the user of the characters they are typing before the word is complete. """
			mode = brailleTranslation.partialTranslation

			data = u"".join([chr(cell | UNICODE_BRAILLE_START) for cell in cells])
			text = brailleTranslation.translationProvider.backTranslate(data, mode=mode)

		self.bufferText = text
		return oldText

	def _reportContractedCell(self, pos):
		"""Report a guess about the character(s) produced by a cell of contracted braille.
		It's not possible to report the exact characters because later cells might change text produced by earlier cells.
		However, it's helpful for the user to have a rough idea.
		For example, in English contracted braille, "alw" is the contraction for "always".
		As the user types "alw", the characters a, l, w will be spoken.
		@return: C{True} if a guess was reported, C{False} if not (e.g. a number sign).
		@rtype: bool
		"""
		oldText = self._translateForReportContractedCell(pos)
		oldTextLen = len(oldText)
		if oldText != self.bufferText[:oldTextLen]:
			# This cell caused the text before it to change, so we can't make a useful guess.
			return False
		newText = self.bufferText[oldTextLen:]
		if newText:
			# New text was generated by the cells just entered.
			# Speak them as separate characters.
			speech.speakMessage(" ".join(newText))
			return True
		return False

	def _reportUntranslated(self, pos):
		"""Report a braille cell which hasn't yet been translated into text."""
		speakTyped = config.conf["keyboard"]["speakTypedCharacters"]
		protected = api.isTypingProtected()
		if speakTyped:
			if protected:
				speech.speakSpelling(speech.PROTECTED_CHAR)
			#elif not self._table.contracted or not self._reportContractedCell(pos):
			elif not brailleTranslation.translationProvider.useLiteraryBrailleForInput() or not self._reportContractedCell(pos):
				dots = self.bufferBraille[pos]
				speakDots(dots)
		#if self._table.contracted and (not speakTyped or protected):
		if brailleTranslation.translationProvider.useLiteraryBrailleForInput() and (not speakTyped or protected):
			# Even if we're not speaking contracted cells, we might need to start doing so midword.
			# For example, the user might have speak typed characters disabled, but enable it midword.
			# Update state needed to report contracted cells.
			self._translateForReportContractedCell(pos)
		self._updateUntranslated()
		self.updateDisplay()

	def _shouldSpeakBrailleImeWords(self) -> bool:
		typingEchoMode = config.conf["keyboard"]["speakTypedWords"]
		if typingEchoMode == TypingEcho.OFF.value:
			return False
		if api.isTypingProtected():
			return False
		if typingEchoMode == TypingEcho.EDIT_CONTROLS.value:
			return speech.speech.isFocusEditable()
		return True

	def _shouldSpeakBrailleImeCharacters(self) -> bool:
		typingEchoMode = config.conf["keyboard"]["speakTypedCharacters"]
		if typingEchoMode == TypingEcho.OFF.value:
			return False
		if api.isTypingProtected():
			return False
		if typingEchoMode == TypingEcho.EDIT_CONTROLS.value:
			return speech.speech.isFocusEditable()
		return True

	def _isWordDelimiter(self, ch: str) -> bool:
		return ch.isspace()

	def _stripTrailingWordDelimiters(self, text: str) -> str:
		i = len(text)
		while i > 0 and self._isWordDelimiter(text[i - 1]):
			i -= 1
		return text[:i]

	def _getTypedWordFromTextInfo(self) -> Optional[str]:
		"""Read the just-typed word from the focused object via TextInfo.

		Must be called *after* the delimiter character has been committed to the
		document (e.g. inside a :func:`core.callLater` callback).  At that point
		the caret sits one character past the end of the word (on the delimiter);
		moving back one character places us inside the word (or on the delimiter
		itself if the word is empty), and expanding to :data:`textInfos.UNIT_WORD`
		retrieves the full word — including any prefix that was erased and retyped.
		"""
		focus = api.getFocusObject()
		try:
			caretInfo = focus.makeTextInfo(textInfos.POSITION_CARET)
			wordInfo = caretInfo.copy()
			if wordInfo.move(textInfos.UNIT_CHARACTER, -1) == 0:
				return None
			wordInfo.expand(textInfos.UNIT_WORD)
			return wordInfo.text.strip() or None
		except Exception:
			log.debugWarning("BrailleIME: failed to read word from TextInfo", exc_info=True)
			return None

	def _speakTypedWord(self, fallback: Optional[str]) -> None:
		"""Speak the word that was just completed by typing a delimiter.

		Reads the word directly from the document via TextInfo (which is accurate
		even after erase-and-retype operations) and falls back to the
		pre-computed back-translated *fallback* string if TextInfo is unavailable.
		"""
		word = self._getTypedWordFromTextInfo() or fallback
		if word:
			log.debug(f"_speakTypedWord: word={word}")
			speech.speakText(word, priority=speech.priorities.Spri.NOW)

	def _handleBrailleImeSpeechInput(self, dots: int) -> None:
		log.debug("Handling braille IME speech input: dots=%s" % formatDotNumbers(dots))
		speakWords = self._shouldSpeakBrailleImeWords()
		speakChars = self._shouldSpeakBrailleImeCharacters()
		if not (speakWords or speakChars):
			return
		char = UNICODE_BRAILLE_START + dots
		self._brailleImeSpeechCells.append(char)

		if speakChars:
			# Speak braille-unicode echo.
			speech._suppressSpeakTypedCharacters(1)
			core.callLater(30, speech.speakSpelling, chr(char))


		#really it doesn't make sense to call the backtranslation unless
		#we have a space here (dots = 0)
		#(enter will also arrive here as a 0)
		if speakWords and dots == 0:
			data = u"".join([chr(cell) for cell in self._brailleImeSpeechCells])
			text = brailleTranslation.translationProvider.backTranslate(data, mode=0)
			log.debug(f"_handleBrailleImeSpeechInput: text={text}")

			if not text:
				return

			last = text[-1]
			if self._isWordDelimiter(last):
				fallback = self._stripTrailingWordDelimiters(text)
				speech._suppressSpeakTypedCharacters(1)
				speech.cancelSpeech()
				core.callLater(30, self._speakTypedWord, fallback)
				self._brailleImeSpeechCells.clear()




	def input(self, dots: int):
		"""Handle one cell of braille input."""
		# Insert the newly entered cell into the buffer at the cursor position.
		pos = self.untranslatedStart + self.untranslatedCursorPos
		self.bufferBraille.insert(pos, dots)
		self.untranslatedCursorPos += 1

		#last resort sanity check
		if not self.nativeBrailleRequired and not self.brlucxEnabled:
			self._setUnicodeBrailleInput(False)

		# In browse mode, treat dot7 as shift modifier for keyboard emulation
		if self._inBrowseMode and not self.currentModifiers:
			# Check if dot7 is present (for shift)
			if dots & DOT7 and dots != DOT7 and not (dots & DOT8):
				# Remove dot7 from the cell and add shift modifier
				self.bufferBraille[pos] = dots & ~DOT7
				self.currentModifiers.add("shift")

		#In Unicode Braille mode, no need to wait for any word completion,
		# can enter the unicode braille char immediately
		if self.unicodeBrailleInput:
			if self.brlucxEnabled:
				# Use the potentially modified dots from the buffer (dot8/dot7 may have been removed)
				self._handleBrailleImeSpeechInput(self.bufferBraille[pos])
			endWord = True
		else:
			# Space ends the word.
			endWord = dots == 0




		# For uncontracted braille, translate the buffer for each cell added.
		# Any new characters produced are then sent immediately.
		# For contracted braille, translate the buffer only when a word is ended (i.e. a space is typed).
		# This is because later cells can change characters produced by previous cells.
		# For example, in English grade 2, "tg" produces just "tg",
		# but "tgr" produces "together".
		if not self.useContractedForCurrentFocus or endWord:
			if self._translate(endWord):
				if not endWord:
					self.cellsWithText.add(pos)
			#elif self.bufferText and not self.useContractedForCurrentFocus and self._table.contracted:
			elif self.bufferText and not self.useContractedForCurrentFocus and brailleTranslation.translationProvider.useLiteraryBrailleForInput():
				# Translators: Reported when translation didn't succeed due to unsupported input.
				speech.speakMessage(_("Unsupported input"))
				self.flushBuffer()
			else:
				# This cell didn't produce any text; e.g. number sign.
				self._reportUntranslated(pos)
		else:
			self._reportUntranslated(pos)

	def toggleModifier(self, modifier: str):
		self.toggleModifiers([modifier])

	def toggleModifiers(self, modifiers: List[str]):
		# Check modifier validity
		validModifiers: bool = all(
			keyboardHandler.KeyboardInputGesture.fromName(m).isModifier for m in modifiers
		)
		if not validModifiers:
			raise ValueError("%r contains unknown modifiers" % modifiers)

		# Ensure input buffer is clear for the modified key
		if self.bufferText:
			self._translate(True)

		toToggle: frozenset[str] = frozenset(modifiers)
		added = toToggle - self.currentModifiers
		removed = toToggle & self.currentModifiers
		self.currentModifiers.difference_update(toToggle)
		self.currentModifiers.update(added)
		for modifier in added:
			speech.speakMessage(keyLabels.getKeyCombinationLabel(modifier))
		for modifier in removed:
			speech.speakMessage(
				# Translators: Reported when a braille input modifier is released.
				_("{modifier} released").format(
					modifier=keyLabels.getKeyCombinationLabel(modifier),
				),
			)

	def enter(self):
		"""Translates any braille input and presses the enter key."""
		if self.unicodeBrailleInput:
			if self.brlucxEnabled:
				self._handleBrailleImeSpeechInput(0) #in terms of speech echo, same as passing a space.

		self._translate(True)
		inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName("enter"))

	def translate(self):
		"""Translates any braille input without inserting a space or new line."""
		self._translate(True)

	def _updateUntranslated(self):
		"""Update the untranslated braille to be shown to the user.
		If the display will not otherwise be updated, L{updatedisplay} should be called after this.
		"""
		if api.isTypingProtected():
			self.untranslatedBraille = UNICODE_BRAILLE_PROTECTED * (
				len(self.bufferBraille) - self.untranslatedStart
			)
		else:
			self.untranslatedBraille = "".join(
				[chr(UNICODE_BRAILLE_START + dots) for dots in self.bufferBraille[self.untranslatedStart :]],
			)

	def updateDisplay(self):
		"""Update the braille display to reflect untranslated input."""
		region = braille.handler.mainBuffer.regions[-1] if braille.handler.mainBuffer.regions else None
		if isinstance(region, braille.TextInfoRegion):
			braille.handler._regionsPendingUpdate.add(region)
			braille.handler._handlePendingUpdate()

	def eraseLastCell(self):
		# Get the index of the cell being erased.
		index = self.untranslatedStart + self.untranslatedCursorPos - 1
		if self.unicodeBrailleInput and self._brailleImeSpeechCells:
			self._brailleImeSpeechCells.pop()
		if index < 0:
			# Erasing before the start of the buffer.
			self._uncontSentTime = time.time()
			inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName("backspace"))
			return
		cell = self.bufferBraille.pop(index)
		if index in self.cellsWithText:
			# Erase a real character.
			self._uncontSentTime = time.time()
			inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName("backspace"))
			char = self.bufferText[-1]
			self.bufferText = self.bufferText[:-1]
			region = braille.handler.mainBuffer.regions[-1] if braille.handler.mainBuffer.regions else None
			if (
				not isinstance(region, braille.TextInfoRegion)
				or region.cursorPos is None
				or region.rawText[region.cursorPos - 1] != char
			):
				# The character before the cursor isn't the character we expected to erase.
				# The cursor must have moved between typing and erasing.
				# Thus, the buffer is now invalid.
				self.flushBuffer()
				return
			self.cellsWithText.remove(index)
			self.untranslatedStart -= 1
			self.untranslatedCursorPos = 0
			# This might leave us with some untranslated braille.
			# For example, in English grade 1, erasing the number 1 leaves us with a number sign.
			for prevIndex in range(index - 1, -1, -1):
				if prevIndex in self.cellsWithText:
					# This cell produced text, so stop.
					break
				# This cell didn't produce text (e.g. number sign),
				# so show this untranslated input to the user.
				self.untranslatedStart = prevIndex
				self.untranslatedCursorPos += 1
			if self.untranslatedCursorPos > 0:
				self._updateUntranslated()
				self.updateDisplay()
		else:
			# This cell didn't produce text.
			#if self._table.contracted:
			if brailleTranslation.translationProvider.useLiteraryBrailleForInput():
				# Update state needed to report contracted cells.
				self._translateForReportContractedCell(index)
			speakDots(cell)
			self.untranslatedCursorPos -= 1
			self._updateUntranslated()
			self.updateDisplay()

	def flushBuffer(self):
		self.bufferBraille = []
		self.bufferText = ""
		self.cellsWithText.clear()
		self.currentModifiers.clear()
		self.untranslatedBraille = ""
		self.untranslatedStart = 0
		self.untranslatedCursorPos = 0
		self._brailleImeSpeechCells.clear()

	def emulateKey(self, key: str, withModifiers: bool = True):
		"""Emulates a key using the keyboard emulation system.
		If emulation fails (e.g. because of an unknown key), a debug warning is logged
		and the system falls back to sending unicode characters.
		@param withModifiers: Whether this key emulation should include the modifiers that are held virtually.
			Note that this method does not take care of clearing L{self.currentModifiers}.
		"""
		if withModifiers:
			# The emulated key should be the last item in the identifier string.
			keys = list(self.currentModifiers)
			keys.append(key)
			gesture = "+".join(keys)
		else:
			gesture = key
		try:
			inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(gesture))
		except:  # noqa: E722
			log.debugWarning(
				"Unable to emulate %r, falling back to sending unicode characters" % gesture,
				exc_info=True,
			)
			self.sendChars(key)

	def sendChars(self, chars: str):
		"""Sends the provided unicode characters to the system.
		@param chars: The characters to send to the system.
		"""
		inputs = []
		chars = "".join(
			ch if ord(ch) <= 0xFFFF else "".join(chr(x) for x in struct.unpack(">2H", ch.encode("utf-16be")))
			for ch in chars
		)
		for ch in chars:
			for direction in (0, winBindings.user32.KEYEVENTF.KEYUP):
				input = winBindings.user32.INPUT()
				input.type = winBindings.user32.INPUT_TYPE.KEYBOARD
				input.ii.ki = winBindings.user32.KEYBDINPUT()
				input.ii.ki.wScan = ord(ch)
				input.ii.ki.dwFlags = winBindings.user32.KEYEVENTF.UNICODE | direction
				inputs.append(input)
		winUser.SendInput(inputs)
		focusObj = api.getFocusObject()
		if keyboardHandler.shouldUseToUnicodeEx(focusObj):
			# #10569: When we use ToUnicodeEx to detect typed characters,
			# emulated keypresses aren't detected.
			# Send TypedCharacter events manually.
			for ch in chars:
				focusObj.event_typedCharacter(ch=ch)

	def handleGainFocus(self, obj):

		"""Clear all state when the focus changes.
		:type obj: NVDAObjects.NVDAObject
		"""
		self.flushBuffer()

	def handleCaretMove(self, obj):
		"""
		:type obj: NVDAObjects.NVDAObject
		"""
		if not self.bufferBraille:
			# No pending braille input, so nothing to do.
			return
		if self._uncontSentTime:
			# Uncontracted braille recently sent characters to the system.
			# This might cause a caret move, but we don't want to clear state
			# due to our own text entry.
			# If the caret move occurred within a short time, we assume it was caused by us.
			if time.time() - self._uncontSentTime <= 0.3:
				# This was caused by us. Ignore it.
				return
			self._uncontSentTime = None
		# Braille input is incomplete, but the cursor has been moved.
		# Clear all state.
		self.flushBuffer()

	def handlePostConfigProfileSwitch(self):
		# #6140: Migrate to new table names as smoothly as possible.
		tableName = config.conf["braille"]["inputTable"]
		newTableName = brailleTables.RENAMED_TABLES.get(tableName)
		if newTableName:
			tableName = config.conf["braille"]["inputTable"] = newTableName
		if config.conf["braille"]["inputTable"] == "auto":
			tableName = brailleTables.getDefaultTableForCurLang(
				brailleTables.TableType.INPUT,
			)
		if tableName != self._table.fileName:
			try:
				self._table = brailleTables.getTable(tableName)
			except LookupError:
				log.error(
					f"Invalid input table ({tableName}), falling back to default ({FALLBACK_TABLE}).",
				)
				self._table = brailleTables.getTable(FALLBACK_TABLE)


#: The singleton BrailleInputHandler instance.
handler: Optional[BrailleInputHandler] = None


def initialize():
	global handler
	handler = BrailleInputHandler()
	treeInterceptorHandler.post_browseModeStateChange.register(handler._onBrowseModeStateChange)
	log.info("Braille input initialized")


def terminate():
	global handler
	if handler is not None:
		NVDAHelper.inputLangChanged.unregister(handler._onInputLangChanged)
		treeInterceptorHandler.post_browseModeStateChange.unregister(handler._onBrowseModeStateChange)
	handler = None


def formatDotNumbers(dots: int):
	out = []
	for dot in range(8):
		if dots & (1 << dot):
			out.append(str(dot + 1))
	return " ".join(out)


def speakDots(dots: int):
	# Translators: Used when reporting braille dots to the user.
	speech.speakMessage(_("dot") + " " + formatDotNumbers(dots))


class BrailleInputGesture(inputCore.InputGesture):
	"""Input (dots and/or space bar) from a braille keyboard.
	This could either be as part of a braille display or a stand-alone unit.
	L{dots} and L{space} should be set appropriately.
	"""

	#: Bitmask of pressed dots.
	#: @type: int
	dots = 0

	#: Whether the space bar is pressed.
	#: @type: bool
	space = False

	shouldPreventSystemIdle = True

	def _makeDotsId(self):
		items = ["dot%d" % (i + 1) for i in range(8) if self.dots & (1 << i)]
		if self.space:
			items.append("space")
		return "bk:" + "+".join(items)

	#: The generic gesture identifier for space plus any dots.
	#: This could be used to bind many braille commands to a single script.
	GENERIC_ID_SPACE_DOTS = inputCore.normalizeGestureIdentifier("bk:space+dots")
	#: The generic gesture identifier for any dots.
	#: This is used to bind entry of braille text to a single script.
	GENERIC_ID_DOTS = inputCore.normalizeGestureIdentifier("bk:dots")

	def _get_identifiers(self):
		if self.space and self.dots:
			return (self._makeDotsId(), self.GENERIC_ID_SPACE_DOTS)
		elif self.dots in (DOT7, DOT8, DOT7 | DOT8):
			# Allow bindings to dots 7 and/or 8 by themselves.
			return (self._makeDotsId(), self.GENERIC_ID_DOTS)
		elif self.dots or self.space:
			return (self.GENERIC_ID_DOTS,)
		else:
			return ()

	@classmethod
	def _makeDisplayText(cls, dots: int, space: bool):
		out = ""
		if space and dots:
			# Translators: Reported when braille space is pressed with dots in input help mode.
			out = _("space with dot")
		elif dots:
			# Translators: Reported when braille dots are pressed in input help mode.
			out = _("dot")
		elif space:
			# Translators: Reported when braille space is pressed in input help mode.
			out = _("space")
		if dots:
			out += " " + formatDotNumbers(dots)
		return out

	def _get_displayName(self):
		if not self.dots and not self.space:
			return None
		return self._makeDisplayText(self.dots, self.space)

	@classmethod
	def getDisplayTextForIdentifier(cls, identifier: str):
		assert isinstance(identifier, str)
		# Translators: Used when describing keys on a braille keyboard.
		source = _("braille keyboard")
		if identifier == cls.GENERIC_ID_SPACE_DOTS:
			# Translators: Used to describe the press of space
			# along with any dots on a braille keyboard.
			return (source, _("space with any dots"))
		if identifier == cls.GENERIC_ID_DOTS:
			# Translators: Used to describe the press of any dots
			# on a braille keyboard.
			return (source, _("any dots"))
		# Example identifier: bk:space+dot1+dot2
		# Strip the bk: prefix.
		partsStr = identifier.split(":", 1)[1]
		parts = partsStr.split("+")
		dots = 0
		space = False
		for part in parts:
			if part == "space":
				space = True
			else:
				# Example part: "dot1"
				# Get the dot number and make it 0 based instead of 1 based.
				dot = int(part[3]) - 1
				# Update the dots bitmask.
				dots += 1 << dot
		return (source, cls._makeDisplayText(dots, space))


inputCore.registerGestureSource("bk", BrailleInputGesture)
