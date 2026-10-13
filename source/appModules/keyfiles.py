# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# KeyFiles App Module for NVDA

import appModuleHandler
import appModules.HWUtils
from scriptHandler import script

class AppModule(appModuleHandler.AppModule):

	@script(
		# Translators: Input Help message for the new folder command.
		description=_("New folder"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"), # space + N
	)
	def script_braille_newFolder(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "newFolder")

	@script(
		# Translators: Input Help message for the search command.
		description=_("Search"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space + F
	)
	def script_braille_keyfilesSearch(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "keyfilesSearch")

	@script(
		# Translators: Input Help message for the sort command.
		description=_("Sort"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot6"),	# Space + V
	)
	def script_braille_keyfilesSort(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "keyfilesSort")

	@script(
		# Translators: Input Help message for the rename command.
		description=_("Rename"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot5+dot7"),	# BackSpace + R
	)
	def script_braille_keyfilesRename(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "keyfilesRename")

	@script(
		# Translators: Input Help message for the drive selector command.
		description=_("Drive selection"),
		gesture=("br(hidBrailleStandard):space+dot1+dot4+dot5"),	# Space + D
	)
	def script_braille_keyfilesDriveSelector(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "driveSelection")

	@script(
		description=_("Where am I"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot6"),	# Space + Dots156
	)
	def script_braille_keyfilesWhereAmI(self, gesture):
		kbIdentifier = appModules.HWUtils.getShortcutFromCommandName(self, "keyfilesWhereAmI")
		appModules.HWUtils.emulateGesture(kbIdentifier)

	@script(
		# Translators: Input Help message for the more options command.
		description=_("More Options"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot7+dot8"),	# Backspace + Enter + M
	)
	def script_braille_moreOptions(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "MoreOptions")

	@script(
		description=_("select/unselect element"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7") # Backspace+L
	)
	def script_braille_selectUnselectElement(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "selectUnselectElement")
