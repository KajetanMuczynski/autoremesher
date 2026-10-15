# SPDX-License-Identifier: GPL-3.0-or-later
# Qt-free tests of the remeshing core (src/AutoRemesher and the thirdparty
# sources it uses). The app itself is still built with qmake.
#
#   cmake -S tests -B build-tests && cmake --build build-tests -j2 && ctest --test-dir build-tests
cmake_minimum_required(VERSION 3.16)
project(autoremesher_tests CXX)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(TBB REQUIRED)
find_package(Threads REQUIRED)

set(ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
file(GLOB CORE_SOURCES "${ROOT}/src/AutoRemesher/*.cpp")
add_library(autoremesher_core STATIC
    ${CORE_SOURCES}
    "${ROOT}/thirdparty/isotropicremesher/isotropicremesher.cpp"
    "${ROOT}/thirdparty/isotropicremesher/isotropichalfedgemesh.cpp"
    "${ROOT}/thirdparty/isotropicremesher/axisalignedboundingboxtree.cpp"
    "${ROOT}/thirdparty/meshoptimizer/src/simplifier.cpp"
    "${ROOT}/thirdparty/meshoptimizer/src/indexgenerator.cpp")
target_include_directories(autoremesher_core PUBLIC
    "${ROOT}/include"
    "${ROOT}/src"
    "${ROOT}/thirdparty/eigen"
    "${ROOT}/thirdparty/isotropicremesher"
    "${ROOT}/thirdparty/meshoptimizer/src")
target_compile_definitions(autoremesher_core PUBLIC _USE_MATH_DEFINES NOMINMAX)
target_link_libraries(autoremesher_core PUBLIC TBB::tbb Threads::Threads)

enable_testing()
add_executable(quad_count_test quad_count_test.cpp)
target_link_libraries(quad_count_test PRIVATE autoremesher_core)
add_test(NAME quad_count COMMAND quad_count_test)
