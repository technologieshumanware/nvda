# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# Microsoft Edge App Module for NVDA

import appModuleHandler
import appModules.HWUtils

from scriptHandler import script

class AppModule(appModuleHandler.AppModule):
	@script(
		description=_("Back"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot7"),	# Backspace+B -> Alt+leftArrow
	)
	def script_braille_back(self, gesture):
		appModules.HWUtils.emulateKeyPress("alt+leftarrow")

	@script(
		description=_("Forward"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"),	# Backspace+F -> Alt+rightArrow
	)
	def script_braille_forward(self, gesture):
		appModules.HWUtils.emulateKeyPress("alt+rightArrow")

	@script(
		description=_("Select address bar"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot8"),	# Enter+O -> Alt+D
	)
	def script_braille_selectAddressBar(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "msedge_selectAddressBar")

	@script(
		description=_("Manage bookmarks"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot8"),	# Enter+D235 -> Ctrl+Shift+O
	)
	def script_braille_manageBookmarks(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "msedge_manageBookmarks")

	@script(
		description=_("Add bookmark"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot8"),	# Enter+M -> Ctrl+D
	)
	def script_braille_addBookmark(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "msedge_addBookmark")

	@script(
		description=_("Perform a text search on the current page"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space+F -> Ctrl+NVDA+F
	)
	def script_braille_searchOnCurrentPage(self, gesture):
		appModules.HWUtils.emulateGesture("control+nvda+f")

	@script(
		description=_("Find next text search result"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"),	# Space+N -> NVDA+F3
	)
	def script_braille_findNextText(self, gesture):
		appModules.HWUtils.emulateGesture("nvda+f3")

	@script(
		description=_("Find previous text search result"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"),	# Space+P -> NVDA+Shift+F3
	)
	def script_braille_findPreviousText(self, gesture):
		appModules.HWUtils.emulateGesture("nvda+shift+f3")

	@script(
		description=_("Open browser history"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot6+dot8"),	# Enter+D236 -> Ctrl+H
	)
	def script_braille_openBrowserHistory(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "msedge_openBrowserHistory")

	@script(
		description=_("Makes the menu bar appear"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A -> Alt+F
	)
	def script_braille_makesMenuBarAppear(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "msedge_makesMenuBarAppear")

	@script(
		description=_("Open a new window"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot7"),	# Backspace+N -> Ctrl+N
	)
	def script_braille_openNewWindow(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "msedge_openNewWindow")

	@script(
		description=_("Toggle single letter navigation"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7"),	# Backspace+L -> NVDA+Shift+Space
	)
	def script_braille_toggleSingleLetterNavigation(self, gesture):
		appModules.HWUtils.emulateGesture("nvda+shift+space")
