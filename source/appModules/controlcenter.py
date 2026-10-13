# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

import appModuleHandler
import humanwareCommands

from scriptHandler import script
from appModules import humanware
from globalCommands import SCRCAT_BRAILLE

class AppModule(appModuleHandler.AppModule):
	"""
	App module for Control Center.
	"""
	@script(
		# Translators: Input help mode message for a braille command.
		description=_("Translates any braille input"),
		category=SCRCAT_BRAILLE,
		gesture="bk:dot7+dot8",
	)
	def script_braille_translate(self, gesture):
		humanware.emulateKeyPress("control")
		humanwareCommands.HumanwareCommands.script_braille_translate(self, gesture)
