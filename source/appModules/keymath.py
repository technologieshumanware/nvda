# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# KeyMath App Module for NVDA

import appModuleHandler
import appModules.HWUtils
from scriptHandler import script

class AppModule(appModuleHandler.AppModule):
	@script(
		# Translators: Input Help message for the new expression command.
		description=_("New Expression"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot4+dot5"), # Space+N
	)
	def script_braille_newExpression(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "newExpression")

	@script(
		# Translators: Input Help message for the modify expression command.
		description=_("Modify Expression"),
		gesture=("br(hidBrailleStandard):space+dot8"), # Enter
	)
	def script_braille_modifyExpression(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "modifyExpression")

	@script(
		# Translators: Input Help message for the delete all expression command.
		description=_("Delete all expressions"),
		gesture=("br(hidBrailleStandard):space+dot3+dot5+dot6+dot7"), # Backspace+D356
	)
	def script_braille_deleteAllExpressions(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "deleteAllExpressions")

	@script(
		# Translators: Input Help message for the insert braille symbol command.
		description=_("Insert Braille Symbol"),
		gesture=("br(hidBrailleStandard):space+dot3+dot5+dot7"), # Backspace+D35
	)
	def script_braille_insertSymbol(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "insertSymbol")


	@script(
		# Translators: Input Help message for the insert from a BRL file command.
		description=_("Insert from BRL file"),
		gesture=("br(hidBrailleStandard):space+dot1+dot3+dot5+dot7"), # Backspace+O
	)
	def script_braille_insertBRL(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "insertBRL")

	@script(
		# Translators: Input Help message for the export to BRL file command.
		description=_("Export to BRL file"),
		gesture=("br(hidBrailleStandard):space+dot2+dot3+dot4+dot7"), # Backspace+S
	)
	def script_braille_exportBRL(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "exportBRL")

	@script(
		# Translators: Input Help message for the announce expression command.
		description=_("Announce expression"),
		gesture=("br(hidBrailleStandard):space+dot1+dot4"), # Space+C
	)
	def script_braille_announceExpression(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "announceExpression")

	@script(
		# Translators: Input Help message for the display expression error command.
		description=_("Display expression error"),
		gesture=("br(hidBrailleStandard):space+dot2+dot4"), # Space+I
	)
	def script_braille_displayExpressionError(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "displayExpressionError")

	@script(
		# Translators: Input Help message for the enable or disable expression command.
		description=_("Enable or disable expression"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot7"), # Backspace+L
	)
	def script_braille_enableDisableExpression(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "enableDisableExpression")

	@script(
		description=_("Refresh"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot3+dot5"), # Space+R
	)
	def script_braille_refresh(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "refresh")

	@script(
		# Translators: Input Help message for the export content command.
		description=_("Export content"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot7"), # Backspace+E
	)
	def script_braille_exportContent(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "exportContent")

	@script(
		# Translators: Input Help message for the export embossing command.
		description=_("Export embossing"),
		gesture=("br(hidBrailleStandard):space+dot1+dot5+dot8"), # Enter+E
	)
	def script_braille_exportEmbossing(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "exportEmbossing")

	@script(
		# Translators: Input Help message for the graph viewer command.
		description=_("Graph viewer"),
		gesture=("br(hidBrailleStandard):space+dot1+dot2+dot4+dot5+dot8"), # Enter+G
	)
	def script_braille_graphViewer(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "graphViewer")

	@script(
		# Translators: Input Help message for the graph settings command.
		description=_("Graph settings"),
		gesture=("br(hidBrailleStandard):space+dot3+dot5"), # Space+D35
	)
	def script_braille_graphSettings(self, gesture):
		appModules.HWUtils.emulateKeyPressFromCommandName(self, "graphSettings")
