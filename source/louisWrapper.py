# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware


import os
import braille
import brailleInput
import brailleTranslation
from logHandler import log
import config
import globalVars
import louisHelper
from types import NoneType

with os.add_dll_directory(globalVars.appDir):
	import louis

class LibLouisWrapper(brailleTranslation.BrailleTranslationProvider):

		brailleInputHandler:brailleInput.BrailleInputHandler
		brailleDisplayHandler:braille.BrailleHandler
		

		def backTranslate(self, brl: str, cursorPos=None, mode=0) -> str:
			"""Get text for specified braille string.
			@param brl: A string of Unicode braille.
			@return: A Unicode string.
			"""
			mode |= louis.ucBrl | louis.noUndefinedDots 
			if  issubclass(self.brailleInputHandler.__class__, NoneType):
				table = brailleInput.FALLBACK_TABLE
				log.info("backTranslate: Defaulting to brailleInput.FALLBACK_TABLE")
				self.brailleInputHandler = brailleInput.handler

			else:
				table = self.brailleInputHandler._table.fileName

			return louis.backTranslate(
				[table, "braille-patterns.cti"],
				brl,
				cursorPos=cursorPos or 0,
				mode=mode,
				)[0]


		def translate(self, txt: str, typeform=None, cursorPos=None, mode=0):
			"""Get text for specified string.
			@param txt: Unicode string.
			@return: A tuple, string of Unicode braille, a brailleToText position array, a textToBraille position array, and matching cursorPos in the translation.
			"""
			mode |= louis.dotsIO
			if  issubclass(self.brailleDisplayHandler.__class__, NoneType):
				table = braille.FALLBACK_TABLE
				log.info("Defaulting to braille.FALLBACK_TABLE")
				self.brailleDisplayHandler = braille.handler


			else:
				table = self.brailleDisplayHandler._table.fileName  
			
			return louisHelper.translate([table, "braille-patterns.cti"], txt, typeform=typeform, cursorPos=cursorPos, mode=mode)



		def translateInGradeForEntry(self, txt: str, typeform=None, cursorPos=None, mode=0):
			#in this context, having a mode like compbrlAtCursor would not make any sense
			mode = louis.dotsIO

			#forward translation, but using the table from the BrailleINPUT
			if  issubclass(self.brailleInputHandler.__class__, NoneType):
				table = brailleInput.FALLBACK_TABLE
				log.info("translateInGradeForEntry: Defaulting to brailleInput.FALLBACK_TABLE")
				self.brailleInputHandler = brailleInput.handler

			else:
				table = self.brailleInputHandler._table.fileName

			braille, brailleToRawPos, rawToBraillePos, cursorPosition = louisHelper.translate([table, "braille-patterns.cti"], txt, typeform=typeform, cursorPos=cursorPos, mode=mode)
			
   			# Workaround for liblouis: cursor position refers to the position before a character.
			# When cursor is at the end of text (after the last character), liblouis fails to handle it correctly.
			if cursorPos is not None and cursorPos >= len(txt):
				cursorPosition = len(braille)

			return braille, brailleToRawPos, rawToBraillePos, cursorPosition




		#here we use the strict equivalent of what was in place
		#which is based on the contracted attribute of the input table
		#But maybe it's not 100% acurate for the intended usage
		def useLiteraryBrailleForInput(self) -> bool :
			if  issubclass(self.brailleInputHandler.__class__, NoneType):
				return False  #the fallback table isn't contracted
			
			return self.brailleInputHandler._table.contracted
		

		#here we test for the actual computer braille flag. 
		def useComputerBrailleForInput(self) -> bool :
			if  issubclass(self.brailleInputHandler.__class__, NoneType):
				return False  #the fallback table isn't computer braille
			
			return self.brailleInputHandler._table.computerBraille
		


		def __init__(self):
			log.info("Wrapper init")
			louisHelper.initialize()
			self.brailleInputHandler = brailleInput.handler
			self.brailleDisplayHandler = braille.handler
			

		#unused, for compatibility
		#could be connected to brailleTables.listTables() with filtering
		def getTranslators(self):
			return "See brailleTables"
