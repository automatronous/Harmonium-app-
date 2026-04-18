from __future__ import annotations

import shutil
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from audio import (
    DEFAULT_INSTRUMENT_ID,
    AudioEngine,
    EffectsState,
    LoopAssignment,
    LoopManager,
    PresetData,
    PresetStore,
    build_instrument_catalog,
)
from ui.keyboard_widget import PianoKeyboardWidget
from ui.panels import AssignmentEditor, EffectsPanel, InstrumentBrowser, LoopPadsBar, PerformancePanel


KEYBOARD_NOTE_MAP = {
    Qt.Key_A: (60, "A"),
    Qt.Key_W: (61, "W"),
    Qt.Key_S: (62, "S"),
    Qt.Key_E: (63, "E"),
    Qt.Key_D: (64, "D"),
    Qt.Key_F: (65, "F"),
    Qt.Key_T: (66, "T"),
    Qt.Key_G: (67, "G"),
    Qt.Key_Y: (68, "Y"),
    Qt.Key_H: (69, "H"),
    Qt.Key_U: (70, "U"),
    Qt.Key_J: (71, "J"),
    Qt.Key_K: (72, "K"),
    Qt.Key_O: (73, "O"),
    Qt.Key_L: (74, "L"),
    Qt.Key_P: (75, "P"),
    Qt.Key_Semicolon: (76, ";"),
}

LOOP_HOTKEYS = {
    Qt.Key_1: "1",
    Qt.Key_2: "2",
    Qt.Key_3: "3",
    Qt.Key_4: "4",
    Qt.Key_5: "5",
    Qt.Key_6: "6",
    Qt.Key_7: "7",
    Qt.Key_8: "8",
}


class KeyboardWorkbenchWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.catalog = build_instrument_catalog()
        self.engine = AudioEngine(soundfont_dir=project_root / "soundfonts")
        self.loop_manager = LoopManager(self.engine, self.catalog)
        if getattr(sys, "frozen", False):
            user_data_dir = Path(os.getenv("LOCALAPPDATA")) / "AstraKeys"
            user_data_dir.mkdir(exist_ok=True)

            presets_dir = user_data_dir / "presets"
            presets_dir.mkdir(exist_ok=True)

            default_presets = project_root / "presets"
            for file in default_presets.glob("*.json"):
                target = presets_dir / file.name
                if not target.exists():
                    shutil.copy(file, target)
        else:
         presets_dir = project_root / "presets"
        self.preset_store = PresetStore(presets_dir)
        self.current_instrument_id = DEFAULT_INSTRUMENT_ID
        self.transpose = 0
        self.held_notes: dict[int, int] = {}

        self.setWindowTitle("Astra Keys")
        self.setWindowIcon(QIcon(str(project_root / "assets" / "logo.svg")))
        self.resize(1580, 940)
        self.setMinimumSize(1360, 820)
        self.setFocusPolicy(Qt.StrongFocus)

        self._build_ui()
        self._load_stylesheet()
        self._wire_events()
        self._bootstrap()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(18)
        root.addLayout(body, 1)

        self.instrument_browser = InstrumentBrowser(self.catalog)
        left_frame = self._panel_shell(self.instrument_browser)
        left_frame.setMaximumWidth(320)

        center_frame = self._build_center_panel()
        right_frame = self._build_right_panel()
        right_frame.setMaximumWidth(430)

        body.addWidget(left_frame, 0)
        body.addWidget(center_frame, 1)
        body.addWidget(right_frame, 0)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("heroPanel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        title_box = QVBoxLayout()
        title = QLabel("ASTRA KEYS")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Stage-focused virtual keyboard inspired by arranger workstations, rebuilt around real instrument backends and PySide6.")
        subtitle.setObjectName("heroSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        info_box = QVBoxLayout()
        self.instrument_badge = QLabel("Voice: --")
        self.instrument_badge.setProperty("statusBadge", "ok")
        self.audio_badge = QLabel("Audio: --")
        self.audio_badge.setProperty("statusBadge", "ok")
        self.keymap_badge = QLabel("Keys: A S D F G H J K with W/E/T/Y/U/O/P for sharps")
        self.keymap_badge.setProperty("statusBadge", "ok")
        info_box.addWidget(self.instrument_badge)
        info_box.addWidget(self.audio_badge)
        info_box.addWidget(self.keymap_badge)

        layout.addLayout(title_box, 1)
        layout.addLayout(info_box, 0)
        return frame

    def _build_center_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("stagePanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        overview = QLabel(
            "Play live on the on-screen keyboard, switch between Western and Indian voices, and launch toggle loops on pads 1-8."
        )
        overview.setWordWrap(True)
        overview.setProperty("sectionSubtitle", True)

        self.loop_pads = LoopPadsBar()
        self.keyboard = PianoKeyboardWidget(start_note=48, end_note=84)
        self.keyboard.set_key_labels({midi_note: label for midi_note, label in KEYBOARD_NOTE_MAP.values()})

        footer = QLabel(
            "Loop pads are latched: press once to start, press again to stop. Presets capture effects, selected voice, transpose, and all assignments."
        )
        footer.setWordWrap(True)
        footer.setProperty("sectionSubtitle", True)

        layout.addWidget(overview)
        layout.addWidget(self.loop_pads)
        layout.addWidget(self.keyboard, 1)
        layout.addWidget(footer)
        return frame

    def _build_right_panel(self) -> QFrame:
        container = QFrame()
        container.setObjectName("sidePanel")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        self.performance_panel = PerformancePanel()
        self.effects_panel = EffectsPanel()
        self.assignment_editor = AssignmentEditor(self.catalog)

        layout.addWidget(self._panel_shell(self.performance_panel))
        layout.addWidget(self._panel_shell(self.effects_panel))
        layout.addWidget(self._panel_shell(self.assignment_editor))
        layout.addStretch(1)
        return container

    @staticmethod
    def _panel_shell(widget: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panelShell")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(widget)
        return frame

    def _load_stylesheet(self) -> None:
        stylesheet = (self.project_root / "assets" / "styles.qss").read_text(encoding="utf-8")
        self.setStyleSheet(stylesheet)

    def _wire_events(self) -> None:
        self.instrument_browser.instrumentSelected.connect(self._select_instrument)
        self.keyboard.notePressed.connect(self._mouse_note_on)
        self.keyboard.noteReleased.connect(self._mouse_note_off)
        self.loop_pads.padTriggered.connect(self._toggle_loop)
        self.loop_manager.loopStateChanged.connect(self.loop_pads.set_active)
        self.loop_manager.assignmentsChanged.connect(self._refresh_assignments)
        self.effects_panel.effectsChanged.connect(self._apply_effects)
        self.assignment_editor.assignmentSaved.connect(self._save_assignment)
        self.assignment_editor.assignmentRemoved.connect(self._remove_assignment)
        self.assignment_editor.hotkeySelectionChanged.connect(self._show_assignment_for_hotkey)
        self.performance_panel.soundfontSelected.connect(self._select_soundfont)
        self.performance_panel.soundfontRefreshRequested.connect(self._refresh_soundfonts)
        self.performance_panel.soundfontBrowseRequested.connect(self._browse_soundfont)
        self.performance_panel.presetLoadRequested.connect(self._load_preset)
        self.performance_panel.presetSaveRequested.connect(self._save_preset)
        self.performance_panel.transposeChanged.connect(self._set_transpose)
        self.performance_panel.panicRequested.connect(self.engine.panic)

    def _bootstrap(self) -> None:
        self._refresh_soundfonts()
        if self.engine.backend_name == "FluidSynth" and self.engine.available_soundfonts:
            self.engine.load_first_available_soundfont()
        self._refresh_backend_badges()
        self.instrument_browser.select_instrument(DEFAULT_INSTRUMENT_ID)
        self._load_preset("factory_preset.json")

    def _refresh_backend_badges(self) -> None:
        current_soundfont_name = self.engine.sound_source_label
        ok = self.engine.runtime_error is None
        self.audio_badge.setText(f"Audio: {current_soundfont_name}")
        self.performance_panel.set_backend_status(self.engine.backend_summary, ok)
        self.performance_panel.set_soundfonts(self.engine.soundfont_names(), self.engine.current_soundfont.name if self.engine.current_soundfont else None)
        preset_names = [path.name for path in self.preset_store.list_presets()]
        self.performance_panel.set_presets(preset_names)

    def _refresh_soundfonts(self) -> None:
        self.engine.refresh_soundfonts()
        self._refresh_backend_badges()

    def _select_instrument(self, instrument_id: str) -> None:
        instrument = self.catalog.get(instrument_id)
        self.current_instrument_id = instrument_id
        self.instrument_badge.setText(f"Voice: {instrument.label} [{instrument.family}]")
        self.engine.select_instrument(instrument)
        self._refresh_backend_badges()

    def _apply_effects(self, state: EffectsState) -> None:
        self.engine.apply_effects(state)

    def _set_transpose(self, value: int) -> None:
        self.transpose = value

    def _save_assignment(self, assignment: LoopAssignment) -> None:
        self.loop_manager.upsert_assignment(assignment)
        self.assignment_editor.set_assignment(assignment.hotkey, assignment)

    def _remove_assignment(self, hotkey: str) -> None:
        self.loop_manager.remove_assignment(hotkey)
        self.assignment_editor.set_assignment(hotkey, None)

    def _show_assignment_for_hotkey(self, hotkey: str) -> None:
        self.assignment_editor.set_assignment(hotkey, self.loop_manager.assignments.get(hotkey))

    def _refresh_assignments(self, assignments: dict[str, LoopAssignment]) -> None:
        self.loop_pads.set_assignments(assignments)
        current_hotkey = self.assignment_editor.hotkey_combo.currentText()
        self.assignment_editor.set_assignment(current_hotkey, assignments.get(current_hotkey))

    def _toggle_loop(self, hotkey: str) -> None:
        self.loop_manager.toggle(hotkey)

    def _select_soundfont(self, soundfont_name: str) -> None:
        if soundfont_name == "No SoundFont Loaded":
            return
        path = self.engine.soundfont_by_name(soundfont_name)
        if path and self.engine.load_soundfont(path):
            self._select_instrument(self.current_instrument_id)
        self._refresh_backend_badges()

    def _browse_soundfont(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Load SoundFont", str(self.project_root), "SoundFont (*.sf2)")
        if not source:
            return
        source_path = Path(source)
        target = self.project_root / "soundfonts" / source_path.name
        if source_path.resolve() != target.resolve():
            shutil.copy2(source_path, target)
        if self.engine.load_soundfont(target):
            self._select_instrument(self.current_instrument_id)
        else:
            QMessageBox.warning(self, "SoundFont Error", self.engine.backend_summary)
        self._refresh_backend_badges()

    def _load_preset(self, preset_name: str) -> None:
        try:
            preset = self.preset_store.load(preset_name)
        except Exception as exc:
            QMessageBox.warning(self, "Preset Error", f"Could not load preset:\n{exc}")
            return
        self._apply_preset(preset)

    def _apply_preset(self, preset: PresetData) -> None:
        if preset.soundfont_name:
            soundfont_path = self.engine.soundfont_by_name(preset.soundfont_name)
            if soundfont_path:
                self.engine.load_soundfont(soundfont_path)
        self.performance_panel.set_transpose(preset.transpose)
        self.transpose = preset.transpose
        self.effects_panel.set_state(preset.effects)
        self.engine.apply_effects(preset.effects)
        self.loop_manager.set_assignments(preset.assignments)
        self.instrument_browser.select_instrument(preset.selected_instrument_id)
        self._show_assignment_for_hotkey("1")
        self._refresh_backend_badges()

    def _save_preset(self, preset_name: str) -> None:
        assignments = [self.loop_manager.assignments[key] for key in sorted(self.loop_manager.assignments)]
        preset = PresetData(
            name=preset_name,
            selected_instrument_id=self.current_instrument_id,
            transpose=self.transpose,
            soundfont_name=self.engine.current_soundfont.name if self.engine.current_soundfont else None,
            effects=EffectsState.from_dict(self.effects_panel.state.to_dict()),
            assignments=assignments,
        )
        path = self.preset_store.save(preset)
        self._refresh_backend_badges()
        QMessageBox.information(self, "Preset Saved", f"Saved preset to:\n{path.name}")

    def _mouse_note_on(self, midi_note: int) -> None:
        self.engine.note_on(midi_note + self.transpose)

    def _mouse_note_off(self, midi_note: int) -> None:
        self.engine.note_off(midi_note + self.transpose)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if event.isAutoRepeat():
            return
        if self._input_widget_has_focus():
            super().keyPressEvent(event)
            return

        if event.key() in LOOP_HOTKEYS:
            self._toggle_loop(LOOP_HOTKEYS[event.key()])
            return

        mapping = KEYBOARD_NOTE_MAP.get(event.key())
        if mapping is None:
            super().keyPressEvent(event)
            return

        base_note, _label = mapping
        transposed_note = base_note + self.transpose
        self.held_notes[event.key()] = transposed_note
        self.keyboard.set_note_state(base_note, True)
        self.engine.note_on(transposed_note)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if event.isAutoRepeat():
            return
        mapping = KEYBOARD_NOTE_MAP.get(event.key())
        if mapping is None:
            super().keyReleaseEvent(event)
            return

        base_note, _label = mapping
        transposed_note = self.held_notes.pop(event.key(), base_note + self.transpose)
        self.keyboard.set_note_state(base_note, False)
        self.engine.note_off(transposed_note)

    def _input_widget_has_focus(self) -> bool:
        widget = self.focusWidget()
        if widget is None:
            return False
        class_name = widget.metaObject().className()
        return class_name in {"QLineEdit", "QSpinBox", "QComboBox", "QAbstractSpinBox"}

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        self.loop_manager.stop_all()
        self.engine.close()
        event.accept()
