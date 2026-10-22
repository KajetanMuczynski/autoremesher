/*
 * Copyright 2013 Computer Graphics Group, RWTH Aachen University
 * Author: Hans-Christian Ebke <ebke@cs.rwth-aachen.de>
 *
 * This file is part of QEx.
 *
 * QEx is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your
 * option) any later version.
 *
 * QEx is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with QEx.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Modified by the Quadami fork, 2026-10-21 (TODO 6.1b): includes Guards.hh.
 * See thirdparty/libQEx/PATCHES.md.
 */

#ifndef GLOBALS_HH_
#define GLOBALS_HH_

#include "Guards.hh"

#include <OpenMesh/Core/Utils/Property.hh>
#include <OpenMesh/Core/Utils/PropertyManager.hh>

/// @file

namespace QEx {

/**
 * @brief This class contains definitions used in multiple classes.
 */
class QExGlobals {
    public:
        static const char *LOCAL_UVS_HANDLE_NAME() {
            return "QEx.LocalUVs";
        }
};

} /* namespace QEx */

#endif /* GLOBALS_HH_ */
