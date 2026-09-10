from __future__ import annotations

import configparser
import shutil
from dataclasses import dataclass
from pathlib import Path

"""
Binary patches for the shipped Prodeus 1.0.2 GameAssembly.dll.

1. Skip the startup logo sequence (Unity / Humble / Bounding Box).
   CommandLineStartup.StartUp is a compiled C# iterator whose MoveNext
   dispatches through a jump table. Its first entry points at the step that
   yields IntroSequence.PlayIntro; repointing it at the next step drops the
   intro and goes straight into loading. The intro both begins and ends with
   the screen faded to black, so skipping it cannot leave the overlay opaque.

2. Make the command line flags work at all.
   CommandLineStartup.ProcessArguments reads -loadMap, -loadEditor,
   -playFromHere, -camPos, -camRot and -noClip, but nothing in the shipped
   build ever calls it: its only reference is its slot in the IL2CPP method
   pointer table. The boot coroutine instead ends with a hardcoded
   SetReturnGameMenuWindow("intro", "") followed by LoadSceneFirst("MainMenu").
   Replacing that pair with a call to ProcessArguments restores the flags.
   With no flags passed, ProcessArguments takes a default branch that issues
   the identical two calls, so stock behaviour is unchanged.

Patches are located by signature rather than fixed offset, so a game update
that shifts the code is detected instead of silently corrupting the DLL.
"""

_conf = configparser.ConfigParser()
_conf.read(Path(__file__).parent / "conf.ini")
_GAME_DLL = Path(_conf["paths"]["game_dll"])


@dataclass(frozen=True)
class _Patch:
    name: str
    original: bytes
    patched: bytes


_PATCHES = (
    _Patch(
        "skip intro logo sequence",
        bytes.fromhex("998e2c01" "e98e2c01" "a48f2c01" "d28f2c01"),
        bytes.fromhex("e98e2c01" "e98e2c01" "a48f2c01" "d28f2c01"),
    ),
    _Patch(
        "route boot through ProcessArguments",
        bytes.fromhex("488b15ea89c700" "4533c0" "488b0df081c500"),
        bytes.fromhex("488b4f20" "e86036b5ff" "eb36" "8b0df081c500"),
    ),
)


def _backup(dll: Path) -> None:
    target = dll.with_suffix(dll.suffix + ".orig-backup")
    if target.exists():
        print(f"  backup already present: {target.name}")
    else:
        shutil.copy2(dll, target)
        print(f"  backup written: {target.name}")


def patch(dll: Path) -> None:
    if not dll.is_file():
        raise FileNotFoundError(f"{dll} not found; check game_dll in conf.ini")

    data = dll.read_bytes()
    pending = []

    for p in _PATCHES:
        if p.original not in data and data.count(p.patched) == 1:
            print(f"  {p.name}: already applied")
            continue
        hits = data.count(p.original)
        if hits != 1:
            raise RuntimeError(
                f"{p.name}: expected 1 match, found {hits}. "
                "The game was probably updated and the patch needs redoing."
            )
        pending.append(p)

    if not pending:
        print(f"{dll.name}: nothing to do")
        return

    _backup(dll)

    for p in pending:
        offset = data.index(p.original)
        data = data[:offset] + p.patched + data[offset + len(p.patched):]
        print(f"  {p.name}: patched at 0x{offset:X}")

    dll.write_bytes(data)


def main() -> None:
    print(_GAME_DLL)
    patch(_GAME_DLL)
    print("done.")


if __name__ == "__main__":
    main()
