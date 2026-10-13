# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# Browser Base Module for NVDA
# Contains common braille shortcuts shared across browser app modules

import appModuleHandler
from appModules import humanware
from scriptHandler import script


class BrowserAppModule(appModuleHandler.AppModule):
	"""Base class for browser app modules containing common braille shortcuts."""
	
	# Subclasses should define this attribute with the browser name
	# e.g., browserName = "firefox"
	browserName = None

	@script(
		description=_("Makes the menu bar appear"),
		gesture=("br(hidBrailleStandard):space+dot1+dot7"),	# Backspace+A -> Alt+F
	)
	def script_braille_makesMenuBarAppear(self, gesture):
		if self.browserName:
			humanware.emulateKeyPressFromCommandName(self, f"{self.browserName}_makesMenuBarAppear")

	@script(
		description=_("Back"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot7"),	# Backspace+B -> Alt+leftArrow
	)
	def script_braille_back(self, gesture):
		humanware.emulateKeyPress("alt+leftarrow")

	@script(
		description=_("Forward"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot7"),	# Backspace+F -> Alt+rightArrow
	)
	def script_braille_forward(self, gesture):
		humanware.emulateKeyPress("alt+rightArrow")

	@script(
		description=_("Toggle single letter navigation"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7"),	# Backspace+L -> NVDA+Shift+Space
	)
	def script_braille_toggleSingleLetterNavigation(self, gesture):
		humanware.emulateGesture("nvda+shift+space")

	@script(
		description=_("Open a new window"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5+dot7"),	# Backspace+N -> Ctrl+N
	)
	def script_braille_openNewWindow(self, gesture):
		if self.browserName:
			humanware.emulateKeyPressFromCommandName(self, f"{self.browserName}_openNewWindow")
 
	@script(
		description=_("Perform a text search on the current page"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4"),	# Space+F -> Ctrl+NVDA+F
	)
	def script_braille_searchOnCurrentPage(self, gesture):
		humanware.emulateGesture("control+nvda+f")

	@script(
		description=_("Find next text search result"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"),	# Space+N -> NVDA+F3
	)
	def script_braille_findNextText(self, gesture):
		humanware.emulateGesture("nvda+f3")

	@script(
		description=_("Find previous text search result"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot4"),	# Space+P -> NVDA+Shift+F3
	)
	def script_braille_findPreviousText(self, gesture):
		humanware.emulateGesture("nvda+shift+f3")

	# Browser-specific shortcuts that use the browserName attribute
	@script(
		description=_("Select address bar"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot8"),	# Enter+O -> Alt+D
	)
	def script_braille_selectAddressBar(self, gesture):
		if self.browserName:
			humanware.emulateKeyPressFromCommandName(self, f"{self.browserName}_selectAddressBar")

	@script(
		description=_("Manage bookmarks"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot5+dot8"),	# Enter+D235 -> Ctrl+Shift+O
	)
	def script_braille_manageBookmarks(self, gesture):
		if self.browserName:
			humanware.emulateKeyPressFromCommandName(self, f"{self.browserName}_manageBookmarks")

	@script(
		description=_("Add bookmark"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot8"),	# Enter+M -> Ctrl+D
	)
	def script_braille_addBookmark(self, gesture):
		if self.browserName:
			humanware.emulateKeyPressFromCommandName(self, f"{self.browserName}_addBookmark")

	@script(
		description=_("Open browser history"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot6+dot8"),	# Enter+D236 -> Ctrl+H
	)
	def script_braille_openBrowserHistory(self, gesture):
		if self.browserName:
			humanware.emulateKeyPressFromCommandName(self, f"{self.browserName}_openBrowserHistory")
