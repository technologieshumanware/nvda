# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Humanware utilities for NVDA screen reader.

This package provides utilities for Humanware braille keyboards and devices,
including gesture handling, keyboard emulation, and dialog management.
"""

# Import and re-export all public functions for easy access
from .gestureConfig import (
	init,
	initLocaleGesture,
	loadLocaleGestureFromCommandNameMap,
	getShortcutFromCommandName,
	getShortcutFromCommandNameAndAppModuleName,
	getConfigValueFromGestureIni,
	getNvdaModifierKey,
)

from .keyboardEmulation import (
	emulateKeyPress,
	emulateGesture,
	emulateKeyPressFromCommandName,
	emulateKeyPressFromCommandNameAndAppModuleName,
	emulateGestureFromCommandName,
	emulateKeySequence,
	emulateKeySequenceFromCommandName,
	emulateTabKeyPress,
	emulateAltKeyPress,
)

from .dialogUtils import (
	getUIAClassName,
	isInHumanWareSaveAsDialog,
	hasAutomationId,
	SAVE_AS_DIALOG_CLASS_NAME,
	SAVE_AS_FILE_MANAGER_CLASS_NAME,
)

from .gestureMap import GlobalGestureCommandNameMap

__all__ = [
	# gestureConfig
	'init',
	'initLocaleGesture',
	'loadLocaleGestureFromCommandNameMap',
	'getShortcutFromCommandName',
	'getShortcutFromCommandNameAndAppModuleName',
	'getConfigValueFromGestureIni',
	'getNvdaModifierKey',
	# keyboardEmulation
	'emulateKeyPress',
	'emulateGesture',
	'emulateKeyPressFromCommandName',
	'emulateKeyPressFromCommandNameAndAppModuleName',
	'emulateGestureFromCommandName',
	'emulateKeySequence',
	'emulateKeySequenceFromCommandName',
	'emulateTabKeyPress',
	'emulateAltKeyPress',
	# dialogUtils
	'getUIAClassName',
	'isInHumanWareSaveAsDialog',
	'hasAutomationId',
	'SAVE_AS_DIALOG_CLASS_NAME',
	'SAVE_AS_FILE_MANAGER_CLASS_NAME',
	# gestureMap
	'GlobalGestureCommandNameMap',
]
