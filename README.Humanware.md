# NVDA for the BrailleNote evolve— Humanware documentation

This document covers what is specific to the Humanware fork of NVDA. For the upstream
NVDA project, its license, community and contribution guidelines, see the main
[readme.md](./readme.md).

## Contents

* [Project context](#project-context)
* [Building](#building)
* [Add-on localization](#add-on-localization)
* [Debugging an add-on](#debugging-an-add-on)
* [Running the system tests](#running-the-system-tests)
* [Incorporating upstream NV Access releases](#incorporating-upstream-nv-access-releases)
* [Add-on general information](#add-on-general-information)

## Project context

NVDA is an open-source screen reader developed by NV Access. On the BrailleNote evolve, 
Humanware ships a customized build of NVDA with its own modifications
and add-ons to integrate tightly with the device (braille display, braille keyboard/IME,
localized shortcuts, and device-specific behaviors).

* **Upstream project:** <https://www.nvaccess.org/>
* **Target devices:** BrailleNote evolve

> The authoritative list of changes is the `BNW-*` commit history and the Confluence space.

## Building

This fork builds like upstream NVDA. See the upstream guide
[projectDocs/dev/buildingNVDA.md](./projectDocs/dev/buildingNVDA.md) and
[projectDocs/dev/createDevEnvironment.md](./projectDocs/dev/createDevEnvironment.md) for the
full setup.

From the repository root, use the bundled SCons wrapper (not a system-wide `scons`):

```
scons.bat
```

For attaching a debugger to a running build, see the upstream
[remote debugging guide](./projectDocs/dev/remoteDebugging.md).

## Add-on localization

Add-ons use NVDA's standard gettext-based translation system. Translatable strings are
extracted into a `.pot` template, translated into per-language `.po` files with
[Poedit](https://poedit.net/), compiled to `.mo`, and loaded at runtime via
`addonHandler`.

### 1. Create the `.pot` template

The `.pot` file is a standard text file that lists the translatable strings (message ids).
Lines starting with `#` are comments and can be used to give translators context about a
string.

### 2. Translate with Poedit

* Install [Poedit](https://poedit.net/).
* Open the `.pot` file in Poedit. Comments authored in step 1 appear in the bottom-right
  panel (marked with a comment icon in the string list) to guide the translator.
* Click **Create new translation** and select the target language.
* Translate all the strings.

### 3. Save the translation files

Save the resulting `.po` file (Poedit also generates the compiled `.mo`) into a `locale`
folder placed at the same level as `globalPlugins`, following this layout:

```
locale/
  <lang>/               # one folder per language, e.g. es, fr
    LC_MESSAGES/
      <domain>.po
      <domain>.mo
```

### 4. Load the translations in Python

Initialize the translation system once in your module, then wrap translatable strings in
`_()`:

```python
import addonHandler
from typing import Callable

addonHandler.initTranslation()
_: Callable[[str], str]
```

Retrieve a string by its message id (`msgid`):

```python
self.brailleSettingsLabel = _("Braille settings")
self._math_code_title = _("&Math code:")
```

## Debugging an add-on

Add-ons can be loaded from NVDA's Developer Scratchpad so you can test and debug changes
without repackaging and reinstalling the add-on.

### Setup

* Check out this NVDA repo and the add-on repo (for example
  `...\screenreader\nvda\addons\BrailleNoteEvolve`).
* Launch NVDA from Visual Studio Code, then open **Preferences (Settings)**, select the
  **Advanced** tab and enable **Enable loading custom code from Developer Scratchpad
  directory**.
* Click **Open developer scratchpad directory** to open it in File Explorer, e.g.
  `...\nvda\nvaccess\nvda\source\userConfig\scratchpad`.

> This is the **source** scratchpad, used when running NVDA from the repo. An installed NVDA
> uses a different scratchpad under `%AppData%\Roaming\nvda` — see
> [File locations](#file-locations).

### Load the add-on from the scratchpad

* Copy the add-on's `globalPlugins` subfolder into the scratchpad. For example, copy:

  ```
  ...\nvda\addons\BrailleNoteEvolve\addon\globalPlugins\BrailleNoteEvolve
  ```

  into:

  ```
  ...\nvda\nvaccess\nvda\source\userConfig\scratchpad\globalPlugins\BrailleNoteEvolve
  ```

* Restart NVDA. If the add-on is detected correctly, it generates its `.pyc` files under a
  `__pycache__` folder. You can now test and debug the add-on.

> If your changes are not being applied, NVDA may be using the officially installed version
> of the add-on instead of the scratchpad copy. Go to **Tools → Add-on store…** and
> uninstall the add-on. Other add-ons can be installed from Jenkins.

### Debugging an add-on that requires NuGet packages

Some add-ons pull native libraries via NuGet. To debug against a locally built version of
such a library:

* Open the `lib` and build/package a local NuGet package with the desired code (see
  [Testing a NuGet package locally](https://technologieshumanware.atlassian.net/wiki/spaces/BNW/pages/661454855/Testing+a+NuGet+package+locally)).
* Download and install [gettext](https://www.gnu.org/software/gettext/), then add its `bin`
  directory to your `PATH`, e.g. `C:\Program Files\gettext-iconv\bin`.
* Check that `C:\Program Files (x86)\NuGet` contains `nuget.exe`. If not, download NuGet and
  place the executable there, then add `C:\Program Files (x86)\NuGet` to your `PATH`.
* In the add-on's `sconstruct` file, set the library version to the version of the package
  you built above (for example, the tested version of `WebDriverLib` was `5.0.0.2`).
* Open a terminal in the folder containing the source code and run:

  ```
  scons version=[wanted version]
  ```

## Running the system tests

The NVDA system tests exercise the built application end to end. See
[tests/system/readme.md](./tests/system/readme.md) for full details.

* Build NVDA first with the bundled SCons wrapper:

  ```
  scons.bat
  ```

* Run the NVDA system tests:

  ```
  runsystemtests.bat --include NVDA
  ```

* To rerun only the tests that failed, point at the previous run's output:

  ```
  runsystemtests.bat --include NVDA --rerunfailed testOutput/system/output.xml
  ```

## Add-on general information

This section collects general reference notes for developing NVDA add-ons.

### Documented in the upstream Developer Guide

The following topics are covered in the upstream NVDA
[Developer Guide](./projectDocs/dev/developerGuide/developerGuide.md):

* **Plugin types** (Global Plugins vs. App Modules) —
  [Types of Plugins](./projectDocs/dev/developerGuide/developerGuide.md#pluginsTypes)
* **Finding the appName for an App Module** —
  [Basics of an App Module](./projectDocs/dev/developerGuide/developerGuide.md#appModuleBasics)
  and [Associating App Modules with an executable](./projectDocs/dev/developerGuide/developerGuide.md#AssociatingAppModule)
* **Localization** —
  [Localizing Add-ons](./projectDocs/dev/developerGuide/developerGuide.md#localizingAddons)
* **Sleep mode** —
  [the App Module SleepMode variable](./projectDocs/dev/developerGuide/developerGuide.md#appModuleSleepMode)
* **Common NVDA object events** —
  [Events](./projectDocs/dev/developerGuide/developerGuide.md#events)
* **Extension points** —
  [Extension Points](./projectDocs/dev/developerGuide/developerGuide.md#ExtensionPoints)

### File locations

Add-ons and other NVDA files live in:

```
C:\Users\<username>\AppData\Roaming\nvda
```

App Modules for testing go in the scratchpad:

```
C:\Users\<username>\AppData\Roaming\nvda\scratchpad\appModules
```

> **Note — two scratchpad locations.** There are two different scratchpad directories
> depending on how you run NVDA:
>
> * **Installed NVDA:** `%AppData%\Roaming\nvda\scratchpad` (the path above). Use this when
>   testing against an installed build.
> * **Running from source (VS Code / Debug):** `source\userConfig\scratchpad` inside this
>   repo. Use this when debugging from the sources, as described in
>   [Debugging an add-on](#debugging-an-add-on).
>
> Copy your add-on into the scratchpad that matches the NVDA you are actually running.

### Imports from the NVDA source

When you write an import such as:

```python
import api
```

the module (`api.py`) comes from the NVDA source code, e.g. `...\nvda\source`.

### Writing output to the display

* `ui.message("your message")` — writes to the braille display **and** speaks the message.
* `braille.handler.message("your message")` — braille only.
* `speech.speakMessage("your message")` — speech only.

### Adding support for a braille display

Add a driver under the add-on's `brailleDisplayDriver` folder and implement:

```python
class BrailleDisplayDriver(braille.BrailleDisplayDriver):
    ...
```
