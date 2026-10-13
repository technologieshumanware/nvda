# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2014-2025 NV Access Limited
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.


"""Framework for braille translation.
Plugins can register their own implementation for any or all of these
using L{registerProvider}.
"""

import re
import typing
from typing import List, Optional, Union
from logHandler import log



class  BrailleTranslationProvider(object):
	

		def backTranslate(self, brl: str, cursorPos=None, mode=0) -> str:
			"""Get text for specified braille string.
			@param brl: A string of Unicode braille.
			@return: A Unicode string.
			"""
			raise NotImplementedError

		#def translate(self, txt: str, typeform=None, cursorPos=None, mode=0) -> [str, list[int], list[int], int]:
		def translate(self, txt: str, typeform=None, cursorPos=None, mode=0):
			"""Get text for specified string.
			@param txt: Unicode string.
			@param cursorPos: position in the input string.
			@return: A tuple, string of Unicode braille, a brailleToText position array,  
					a textToBraille position array, and matching cursorPos in the translation.
			"""
			raise NotImplementedError

		def translateInGradeForEntry(self, txt: str, typeform=None, cursorPos=None, mode=0):
			"""Forward translate the specified string, using the braille translator defined
			for input. That translator typically deals with backtranslation, but there are odd
			cases where it needs to perform forward translation too.
			@param txt: Unicode string.
			@param cursorPos: position in the input string.
			@return: A tuple, string of Unicode braille, a brailleToText position array,  
					a textToBraille position array, and matching cursorPos in the translation.
			"""
			raise NotImplementedError



		def initialize(self):
			raise NotImplementedError
		
		def getTranslators(self) -> list[str]:
			raise NotImplementedError
		
		#brailleInput requires awareness of literary vs computer braille.
		def useLiteraryBrailleForInput(self) -> bool :
			raise NotImplementedError
		
		#we could have had the computerbraille = !literary braille, but 
		#liblouis implementation of useLiteraryBrailleForInput isn't exactly defined correctly
		def useComputerBrailleForInput(self) -> bool :
			raise NotImplementedError
		

		

# { Typeforms (from libLouis)
plain_text = 0x0000
italic = 0x0001
underline = 0x0002
bold = 0x0004256
# }

# { modes   (keeping values from libLouis)

compbrlAtCursor = 2
partialTranslation = 256

#}


translationProvider: Optional[BrailleTranslationProvider] = None

def registerProvider(
	provider: BrailleTranslationProvider,
):
	"""Register a braille translation provider.
	@param provider: The provider to register.
	"""

	global translationProvider
	
	translationProvider = provider


def initialize() -> None:
	# Register builtin providers if a plugin hasn't registered others.
	if not translationProvider:
		try:
			import louisWrapper #late import 
			provider = louisWrapper.LibLouisWrapper()
		except:  
			log.warning("louisWrapper  not available")
		else:
			registerProvider(
				provider,
			)


def terminate() -> None:
	#perform some cleanup there if needed
	log.warning("brailleTranslation terminate")

	
