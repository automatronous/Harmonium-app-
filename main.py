from __future__ import annotations

import sys
from pathlib import Path


def get_project_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


PROJECT_ROOT = get_project_root()


def _check_runtime() -> tuple[bool, str]:
    missing: list[str] = []
    warnings: list[str] = []

    try:
        import PySide6  # noqa: F401
    except Exception as exc:
        missing.append(f"PySide6 ({exc})")

    try:
        import numpy  # noqa: F401
    except Exception as exc:
        missing.append(f"numpy ({exc})")

    try:
        import sounddevice  # noqa: F401
    except Exception as exc:
        warnings.append(f"sounddevice unavailable: {exc}")

    try:
        import fluidsynth  # noqa: F401
    except Exception as exc:
        warnings.append(f"FluidSynth backend unavailable: {exc}")

    if missing:
        message = [
            "Missing required runtime dependencies:",
            f"  - {', '.join(missing)}",
            "",
            "Install them with:",
            "  pip install -r requirements.txt",
            "",
            "On Windows, pyFluidSynth also needs the native FluidSynth library.",
            "The project README explains the exact setup and SoundFont placement.",
        ]
        return False, "\n".join(message)

    if warnings:
        return True, "\n".join(warnings)

    return True, ""


def main() -> int:
    ok, message = _check_runtime()
    if not ok:
        print(message)
        return 1

    from PySide6.QtWidgets import QApplication

    from ui.app import KeyboardWorkbenchWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Astra Keys")
    app.setOrganizationName("Codex Studio")

    window = KeyboardWorkbenchWindow(project_root=PROJECT_ROOT)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
