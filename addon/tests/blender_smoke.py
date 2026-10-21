# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 AutoRemesher fork contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Headless check of the add-on inside Blender.

From the source tree, with a remesher given by path:

    AUTOREMESHER_EXECUTABLE=build/cli/autoremesher-cli \
        blender -b --factory-startup --python-exit-code 1 --python addon/tests/blender_smoke.py

Or the installed extension zip with its bundled remesher (what CI runs):

    blender --command extension install-file -r user_default -e build/addon/quadami-...zip
    blender -b --factory-startup --python-exit-code 1 --python addon/tests/blender_smoke.py -- --installed

Background mode has no window, so the modal operator cannot run; this drives
the same steps it does: read the mesh, run the worker, build the object.
"""

import importlib
import os
import sys

import addon_utils
import bpy

installed = "--installed" in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
if installed:
    # The id is the extension's folder name; read it from the source tree.
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "autoremesher_blender"))
    from names import ID  # noqa: E402
    module_name = "bl_ext.user_default." + ID
    addon_utils.enable(module_name, default_set=True, handle_error=None)
    addon = sys.modules[module_name]
    names = importlib.import_module(module_name + ".names")
    report = importlib.import_module(module_name + ".report")
    worker = importlib.import_module(module_name + ".worker")
else:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import autoremesher_blender as addon  # noqa: E402
    from autoremesher_blender import names, report, worker  # noqa: E402

    addon.register()
try:
    shown = addon.MAIN_PARAMETERS + addon.ADVANCED_PARAMETERS
    assert sorted(shown) == sorted(worker.PARAMETER_FLAGS), (shown, worker.PARAMETER_FLAGS)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64)
    source = bpy.context.active_object
    source.location = (1.0, 2.0, 3.0)
    bpy.context.view_layer.update()

    positions, triangles = addon._mesh_arrays(bpy.context, source)
    assert positions.shape[1] == 3 and triangles.shape[1] == 3, (positions.shape, triangles.shape)
    assert len(triangles) == 128 * 2 + 128 * 62 * 2, len(triangles)

    settings = getattr(bpy.context.scene, names.ID)
    settings.target_quads = 2000
    preferences = addon._preferences(bpy.context)
    executable = worker.find_executable(bpy.path.abspath(preferences.executable) if preferences else "")
    if installed:
        assert executable == worker.bundled_executable(), (executable, worker.bundled_executable())
    assert executable, "set AUTOREMESHER_EXECUTABLE"
    print("blender_smoke: remesher %s" % executable)
    build = worker.addon_build_id()
    print("blender_smoke: add-on build %s, remesher build %s" % (build, worker.worker_build_id(executable)))
    if installed:
        # package.py copies the bundled program's id, so the panel shows no mismatch.
        assert build != "dev" and worker.worker_build_id(executable) == build, build
    outcome = worker.remesh(executable, positions, triangles, settings.parameters())
    assert outcome.ok, (outcome.status, outcome.message, outcome.log)

    obj, final_report = addon._build_object(
        bpy.context, source.name, source.matrix_world.copy(),
        [c.name for c in source.users_collection], outcome)
    output = outcome.report["output"]
    quads = sum(1 for polygon in obj.data.polygons if polygon.loop_total == 4)
    assert len(obj.data.polygons) == output["faces"], (len(obj.data.polygons), output)
    assert quads == output["quads"], (quads, output)
    assert len(obj.data.vertices) == output["vertices"]
    assert tuple(obj.matrix_world.translation) == (1.0, 2.0, 3.0)
    assert addon.REPORT_PROPERTY in obj
    for label, value, problem in report.summary_rows(final_report):
        print("  %-20s %s%s" % (label, value, "  <-" if problem else ""))
    print("blender_smoke: OK, Blender %s" % bpy.app.version_string)
finally:
    if installed:
        addon_utils.disable(module_name, default_set=True)
    else:
        addon.unregister()
