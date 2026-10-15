# SPDX-License-Identifier: GPL-3.0-or-later
# Qt-free tests of the remeshing core. They link the top-level autoremesher_core
# target, so the core is compiled from one source list:
#
#   cmake -S . -B build-tests -DAUTOREMESHER_BUILD_TESTS=ON
#   cmake --build build-tests --target quad_count_test --parallel 2
#   ctest --test-dir build-tests --output-on-failure
add_executable(quad_count_test quad_count_test.cpp)
target_link_libraries(quad_count_test PRIVATE autoremesher_core)
add_test(NAME quad_count COMMAND quad_count_test)

add_executable(diagnostics_test diagnostics_test.cpp)
target_link_libraries(diagnostics_test PRIVATE autoremesher_core)
add_test(NAME diagnostics COMMAND diagnostics_test)

add_executable(open_boundary_test open_boundary_test.cpp)
target_link_libraries(open_boundary_test PRIVATE autoremesher_core)
add_test(NAME open_boundary COMMAND open_boundary_test)
