/*
 *  Copyright (C) 2026 AutoRemesher fork contributors
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef AUTO_REMESHER_CLI_STDINCONTROL_H
#define AUTO_REMESHER_CLI_STDINCONTROL_H
#include <AutoRemesher/Remesh>

namespace AutoRemesher {
namespace Cli {

    // Lets the process that started this one (the Blender add-on) cancel the
    // run: a detached thread requests the cancel when stdin receives the line
    // "cancel" or is closed, e.g. because the host died.  The token must live
    // until the process exits.
    void startStdinCancelReader(CancelToken* token);

}
}

#endif
