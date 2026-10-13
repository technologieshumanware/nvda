# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

"""
Custom gesture map for Humanware command name mappings.

Provides a specialized GlobalGestureMap subclass that handles
regional locale fallback for gesture-to-command bindings.
"""

from typing import Optional

import inputCore


ScriptNameT = str


class GlobalGestureCommandNameMap(inputCore.GlobalGestureMap):
	"""
	Custom gesture map that handles regional locale fallback.
	
	When a new binding is added, it removes any existing bindings for the same command
	from the base language, allowing regional variants (e.g., fr_CA) to override
	base language bindings (e.g., fr).
	"""
	
	def add(
		self,
		gesture: str,
		module: str,
		className: str,
		script: Optional[ScriptNameT],
		replace: bool = False,
	):
		"""
		Add a gesture-to-script binding to the map.
		
		Args:
			gesture (str): Gesture identifier (e.g., "kb:control+c")
			module (str): Module name (e.g., "NVDAObjects.window.winword")
			className (str): Class name (e.g., "WordDocument")
			script (Optional[str]): Script name (e.g., "insertOrEditEquation")
			replace (bool): If True, replace all existing bindings for this gesture
		"""
		# For regional locale fallback: remove any existing bindings for this command
		# before adding the new one (e.g., fr_CA overriding fr)
		if not replace:
			# Search all gestures for this command and remove them
			for existingGesture, existingScripts in list(self._map.items()):
				self._map[existingGesture] = [
					(m, c, s) for (m, c, s) in existingScripts
					if not (m == module and c == className and s == script)
				]
				# Clean up empty gesture entries
				if not self._map[existingGesture]:
					del self._map[existingGesture]
		
		try:
			scripts = self._map[gesture]
		except KeyError:
			scripts = self._map[gesture] = []
		if replace:
			del scripts[:]
		scripts.append((module, className, script))
