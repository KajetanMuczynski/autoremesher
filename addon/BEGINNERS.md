# Building the add-on yourself on Linux, for someone new to it

Most people do not need this: install a ready-made zip and follow the user
guide, [docs/USER-GUIDE.md](../docs/USER-GUIDE.md), which covers installing,
using and updating the add-on. This page is only for building the zip from
this repository on an Ubuntu laptop. Developer details:
[README.md](README.md).

## 1. Install Blender 4.5 LTS

```
sudo snap install blender --channel=4.5lts/stable --classic
```

`snap info blender` (2026-10-15) lists `4.5lts/stable` as 4.5.14, classic
confinement. Classic means Blender can start the remesher from your home
folder; the add-on also drops the snap's library paths before it starts the
remesher, so the remesher uses the system TBB library it was built with,
not the snap's copy.

Blender 5.x is not for this laptop: it needs Intel Kaby Lake or newer graphics,
the HD 5500 is older (https://www.blender.org/download/requirements/).

## 2. Build the add-on zip and the remesher

```
sh ~/Documents/Autoremesher/autoremesher/addon/package.sh
```

It builds the remesher and prints the path of the add-on zip, which has the
remesher inside (`build/addon/quadami-<version>-linux-x64.zip`).

## 3. Start Blender from a terminal

```
blender
```

Started from a terminal, Blender shows the remesher's messages there if
something goes wrong (copy the text after `Quadami worker output:` into a bug
report).

## 4. Install and use it

Continue with the user guide: install the zip from step 2 as in its §2, then
its §3 "Your first remesh".
