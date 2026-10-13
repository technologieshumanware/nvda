# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

# Chrome App Module for NVDA

from appModules.browserBase import BrowserAppModule


class AppModule(BrowserAppModule):
	browserName = "chrome"
