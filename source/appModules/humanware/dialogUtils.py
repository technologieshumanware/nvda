# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Dialog and UIA utility functions for Humanware devices.

Provides utilities for detecting and working with UI Automation elements,
particularly for Humanware custom dialogs and controls.
"""

from typing import Optional

import api
from logHandler import log


# UIA classNames identifying the HumanWare custom "Save As" dialog.
# The dialog is a UIA pane ("OpenSaveAsDialog") that hosts a file browser pane
# ("FileManagerView"). The wrapping window's automationId differs between hosts
# (Word vs Excel) and is sometimes empty, so these classNames are used instead.
SAVE_AS_DIALOG_CLASS_NAME = "OpenSaveAsDialog"
SAVE_AS_FILE_MANAGER_CLASS_NAME = "FileManagerView"


def getUIAClassName(obj) -> Optional[str]:
	"""Safely return the UIA className of obj, or None for non-UIA objects."""
	uiaElement = getattr(obj, "UIAElement", None)
	if uiaElement is None:
		return None
	try:
		return uiaElement.cachedClassName
	except Exception:
		return None


def isInHumanWareSaveAsDialog() -> bool:
	"""Return True if the focus is inside the HumanWare custom "Save As" dialog.

	Walks up the focus ancestor chain looking for both the "OpenSaveAsDialog" pane
	and the "FileManagerView" pane, which together identify the dialog.
	"""
	obj = api.getFocusObject()
	seen = set()
	foundSaveAsPane = False
	foundFileManager = False
	while obj and obj not in seen:
		className = getUIAClassName(obj)
		if className == SAVE_AS_DIALOG_CLASS_NAME:
			foundSaveAsPane = True
		elif className == SAVE_AS_FILE_MANAGER_CLASS_NAME:
			foundFileManager = True
		if foundSaveAsPane and foundFileManager:
			return True
		seen.add(obj)
		obj = obj.parent
	return False


def hasAutomationId(automationId: str) -> bool:
	"""
	Check if the current app module has a specific automation ID.

	Args:
		automationId (str): The automation ID to check for
	Returns:
		bool: True if the automation ID is present, False otherwise
	"""
	if not automationId:
		log.error("hasAutomationId: Invalid automation ID: %r" % automationId)
		return False

	try:
		focus = api.getFocusObject()
		obj = focus
		seen = set()

		while obj:
			if obj.automationId == automationId:
				log.debug("Found matching automation ID: %s" % automationId)
				return True
			if obj in seen:
				log.debug("hasAutomationId: cycle detected in ancestor chain")
				break
			seen.add(obj)
			obj = obj.parent
	except Exception as e:
		log.warning("Error checking automation ID %s: %s" % (automationId, e), exc_info=True)
	return False
