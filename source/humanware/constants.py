# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# Message types, these message types are synced with the Humanware client
NVDA_ERROR = 0
NVDA_ADDON_ERROR = 1
NVDA_INSTALL_DONE = 2

#Error codes, these error codes are synced with the Humanware client
SUCCESS = 0
FAILURE = 1
NVDA_ADDON_BUNDLE_ERROR = 2
NVDA_ADDON_MIN_VERSION_ERROR = 3
NVDA_ADDON_API_VERSION_ERROR = 4
NVDA_ADDON_INSTALL_ERROR = 5
NVDA_SILENT_INSTALL_ALREADY_RUNNING_ERROR = 6
NVDA_SILENT_INSTALL_FAILED = 7

#Pipe name
HW_BNW_CONTROL_CENTER_PIPE = r'\\.\pipe\BNW-NVDA Control Center'
