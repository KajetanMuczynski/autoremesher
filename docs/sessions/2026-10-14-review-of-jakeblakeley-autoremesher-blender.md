# 2026-10-14 · Claude (cloud session) · Review of jakeblakeley/autoremesher-blender
- Repos/commits: fork `jakeblakeley/autoremesher-blender@5368a8c`, forked from upstream `061f740a` (v1.0.0).
- Did: cloned, diffed against its fork point, read the add-on, worker, binding, CMake/packaging and core changes. Added REFERENCE §6.1 and TODO items.
- Found: a one-day fork (2026-07-07), unmaintained since, macOS-only tested, core still on the Geogram pipeline that upstream replaced in 1.1. Strong parts: nanobind module + cibuildwheel + Blender extension packaging, crash-isolated subprocess worker with modal progress. Core additions: LFS thin-feature sizing (Geogram), island detail floor, health check, scale normalisation. No changes to the field/param/rounding/extraction math.
- Decision proposed: borrow the infrastructure and ideas, port them onto current upstream; don't build on its core.
- Measured: nothing.
- Next: same as before, plus port the packaging during Phase 1.
