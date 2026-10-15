# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 AutoRemesher fork contributors
"""List the DLLs a Windows executable imports; fail on runtime or TBB DLLs.

    python ci/check_dll_imports.py autoremesher-cli.exe     (needs: pip install pefile)

The Blender add-on bundles autoremesher-cli.exe alone, so the C++ runtime
(MSVCP*, VCRUNTIME*, the UCRT's api-ms-win-crt-*) and TBB must be linked
statically. (The UCRT ships with Windows 10 and 11, but linking it
statically too keeps the program independent of its servicing state.)
"""

import re
import sys

import pefile

NOT_SHIPPED = re.compile(r"^(msvcp|vcruntime|concrt|vcomp|api-ms-win-crt-|ucrtbase|tbb)", re.I)

pe = pefile.PE(sys.argv[1], fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
dlls = sorted({entry.dll.decode() for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])}, key=str.lower)
print("%s imports: %s" % (sys.argv[1], ", ".join(dlls)))
bad = [dll for dll in dlls if NOT_SHIPPED.match(dll)]
if bad:
    sys.exit("FAIL: imports runtime or TBB DLLs that should be linked statically: " + ", ".join(bad))
print("OK: no C++ runtime or TBB DLLs")
