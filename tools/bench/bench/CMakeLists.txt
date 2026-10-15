# SPDX-License-Identifier: GPL-3.0-or-later
# Qt-free benchmark build of the AutoRemesher core. Not an upstream build file:
# it compiles the same core sources the qmake app links (src/AutoRemesher plus
# thirdparty isotropicremesher and meshoptimizer) with the same release flags
# (autoremesher.pro, unix:!macx block) so timings match the shipped binary.
#
#   cmake -S tools/bench/bench -B build -DAR_SOURCE_DIR=. [-DAR_BENCH_PROBE=ON]   (from the repo root)
cmake_minimum_required(VERSION 3.16)
project(ar_bench CXX)

set(AR_SOURCE_DIR "" CACHE PATH "AutoRemesher source tree (this repo, or an upstream checkout)")
option(AR_BENCH_PROBE "Compile the probes inserted by probes.patch" OFF)
if(NOT EXISTS "${AR_SOURCE_DIR}/src/AutoRemesher/autoremesher.cpp")
    message(FATAL_ERROR "Set AR_SOURCE_DIR to an AutoRemesher checkout")
endif()
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(TBB REQUIRED)
find_package(Threads REQUIRED)

file(GLOB AR_CORE_SOURCES "${AR_SOURCE_DIR}/src/AutoRemesher/*.cpp")
set(AR_THIRDPARTY "${AR_SOURCE_DIR}/thirdparty")
set(AR_SOURCES
    ${AR_CORE_SOURCES}
    "${AR_THIRDPARTY}/isotropicremesher/isotropicremesher.cpp"
    "${AR_THIRDPARTY}/isotropicremesher/isotropichalfedgemesh.cpp"
    "${AR_THIRDPARTY}/isotropicremesher/axisalignedboundingboxtree.cpp"
    "${AR_THIRDPARTY}/meshoptimizer/src/simplifier.cpp"
    "${AR_THIRDPARTY}/meshoptimizer/src/indexgenerator.cpp")

option(AR_USE_CHOLMOD "Experiment: CHOLMOD supernodal LLT instead of SimplicialLDLT (needs cholmod-experiment.patch)" OFF)

set(BENCH_TARGET ar_bench)
if(AR_BENCH_PROBE)
    set(BENCH_TARGET ar_bench_probe)
endif()
if(AR_USE_CHOLMOD)
    set(BENCH_TARGET ${BENCH_TARGET}_cholmod)
endif()
add_executable(${BENCH_TARGET} ar_bench.cpp ${AR_SOURCES})
if(AR_BENCH_PROBE)
    target_sources(${BENCH_TARGET} PRIVATE bench_probe.cpp)
    target_compile_definitions(${BENCH_TARGET} PRIVATE AR_BENCH_PROBE=1)
endif()
if(AR_USE_CHOLMOD)
    find_path(CHOLMOD_INCLUDE_DIR cholmod.h PATH_SUFFIXES suitesparse REQUIRED)
    find_library(CHOLMOD_LIBRARY cholmod REQUIRED)
    target_include_directories(${BENCH_TARGET} PRIVATE "${CHOLMOD_INCLUDE_DIR}")
    target_link_libraries(${BENCH_TARGET} PRIVATE "${CHOLMOD_LIBRARY}")
    target_compile_definitions(${BENCH_TARGET} PRIVATE AR_USE_CHOLMOD=1)
endif()
target_include_directories(${BENCH_TARGET} PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${AR_SOURCE_DIR}/include"
    "${AR_SOURCE_DIR}/src"
    "${AR_THIRDPARTY}/eigen"
    "${AR_THIRDPARTY}/isotropicremesher"
    "${AR_THIRDPARTY}/meshoptimizer/src")
target_compile_definitions(${BENCH_TARGET} PRIVATE NDEBUG _USE_MATH_DEFINES NOMINMAX)
target_compile_options(${BENCH_TARGET} PRIVATE -O3 -funroll-loops -march=x86-64-v2 -w)
set_property(TARGET ${BENCH_TARGET} PROPERTY INTERPROCEDURAL_OPTIMIZATION ON)
target_link_libraries(${BENCH_TARGET} PRIVATE TBB::tbb Threads::Threads)
