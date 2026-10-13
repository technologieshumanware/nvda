# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# KeyFiles App Module for NVDA

import appModuleHandler
import winUser

from appModules import humanware
from scriptHandler import script

class AppModule(appModuleHandler.AppModule):

	@script(
		# Translators: Input Help message for the new folder command.
		description=_("New folder"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"), # space+N
	)
	def script_braille_newFolder(self, gesture):
		humanware.emulateKeyPressFromCommandName(self, "newFolder") # Ctrl+N

	@script(
		# Translators: Input Help message for the search command.
		description=_("Search"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space+F
	)
	def script_braille_keyfilesSearch(self, gesture):
		humanware.emulateKeyPressFromCommandName(self, "keyfilesSearch") # Ctrl+F

	@script(
		# Translators: Input Help message for the sort command.
		description=_("Sort"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot6"),	# Space+V
	)
	def script_braille_keyfilesSort(self, gesture):
		humanware.emulateKeyPressFromCommandName(self, "keyfilesSort") # Ctrl+S

	@script(
		# Translators: Input Help message for the rename command.
		description=_("Rename"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot7"),	# BackSpace+R
	)
	def script_braille_keyfilesRename(self, gesture):
		humanware.emulateKeyPressFromCommandName(self, "keyfilesRename") # F2

	@script(
		description=_("Where am I"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot6"),	# Space+Dots156
	)
	def script_braille_keyfilesWhereAmI(self, gesture):
		kbIdentifier = humanware.getShortcutFromCommandName(self, "keyfilesWhereAmI")
		humanware.emulateGesture(kbIdentifier) # NVDA+End

	@script(
		# Translators: Input Help message for the more options command.
		description=_("More Options"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot7+dot8"),	# Backspace+Enter+M
	)
	def script_braille_moreOptions(self, gesture):
		humanware.emulateKeyPressFromCommandName(self, "MoreOptions") # Ctrl+M

	@script(
		description=_("select/unselect element"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7") # Backspace+L
	)
	def script_braille_selectUnselectElement(self, gesture):
		humanware.emulateKeyPressFromCommandName(self, "selectUnselectElement") # Ctrl+Space
