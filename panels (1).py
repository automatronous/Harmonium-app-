from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from audio.instruments import InstrumentCatalog
from audio.models import EffectsState, LoopAssignment, note_name_choices


class SliderControl(QWidget):
    valueChanged = Signal(float)

    def __init__(self, title: str, minimum: float, maximum: float, step: float, value: float, suffix: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.suffix = suffix
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, int(round((maximum - minimum) / step)))
        self.slider.valueChanged.connect(self._emit_value)
        self.title_label = QLabel(title)
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.title_label)
        row.addStretch(1)
        row.addWidget(self.value_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(row)
        layout.addWidget(self.slider)

        self.set_value(value)

    def set_value(self, value: float) -> None:
        clamped = max(self.minimum, min(self.maximum, value))
        slider_value = int(round((clamped - self.minimum) / self.step))
        block = self.slider.blockSignals(True)
        self.slider.setValue(slider_value)
        self.slider.blockSignals(block)
        self._update_label(clamped)

    def value(self) -> float:
        return self.minimum + self.slider.value() * self.step

    def _update_label(self, value: float) -> None:
        if value == int(value):
            text = f"{int(value)}{self.suffix}"
        else:
            text = f"{value:.2f}{self.suffix}"
        self.value_label.setText(text)

    def _emit_value(self, slider_value: int) -> None:
        value = self.minimum + slider_value * self.step
        self._update_label(value)
        self.valueChanged.emit(value)


class InstrumentBrowser(QWidget):
    instrumentSelected = Signal(str)

    def __init__(self, catalog: InstrumentCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search instruments")
        self.tabs = QTabWidget()
        self.lists: dict[str, QListWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        heading = QLabel("Instrument Browser")
        heading.setProperty("sectionTitle", True)
        helper = QLabel("Separate Western and Indian voice banks with quick browsing.")
        helper.setProperty("sectionSubtitle", True)

        layout.addWidget(heading)
        layout.addWidget(helper)
        layout.addWidget(self.search)
        layout.addWidget(self.tabs, 1)

        for tab_name, label in (("western", "Western"), ("indian", "Indian")):
            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.SingleSelection)
            list_widget.currentItemChanged.connect(self._emit_selection)
            self.lists[tab_name] = list_widget
            self.tabs.addTab(list_widget, label)
            self._populate_tab(tab_name, list_widget)

        self.search.textChanged.connect(self._filter_items)

    def _populate_tab(self, tab_name: str, list_widget: QListWidget) -> None:
        list_widget.clear()
        for instrument in self.catalog.by_tab(tab_name):
            item = QListWidgetItem(f"{instrument.label}\n{instrument.family}")
            item.setData(Qt.UserRole, instrument.id)
            item.setData(Qt.UserRole + 1, f"{instrument.label} {instrument.family}".lower())
            item.setToolTip(instrument.description)
            hint = item.sizeHint()
            item.setSizeHint(QSize(hint.width(), hint.height() + 18))
            list_widget.addItem(item)

    def _filter_items(self, text: str) -> None:
        text = text.strip().lower()
        for list_widget in self.lists.values():
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                label = item.data(Qt.UserRole + 1)
                item.setHidden(bool(text) and text not in label)

    def _emit_selection(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        if current is None:
            return
        instrument_id = current.data(Qt.UserRole)
        self.instrumentSelected.emit(instrument_id)

    def select_instrument(self, instrument_id: str) -> None:
        for tab_name, list_widget in self.lists.items():
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                if item.data(Qt.UserRole) == instrument_id:
                    self.tabs.setCurrentIndex(0 if tab_name == "western" else 1)
                    list_widget.setCurrentItem(item)
                    return


class EffectsPanel(QWidget):
    effectsChanged = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updating = False
        self.controls: dict[str, SliderControl] = {}
        self.state = EffectsState()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Effects")
        title.setProperty("sectionTitle", True)
        subtitle = QLabel("Reverb, chorus, stereo image and a three-band finishing EQ.")
        subtitle.setProperty("sectionSubtitle", True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        groups = {
            "Space": [
                ("reverb_room_size", "Room Size", 0.0, 1.0, 0.01, self.state.reverb_room_size),
                ("reverb_level", "Reverb Send", 0.0, 1.0, 0.01, self.state.reverb_level),
                ("reverb_width", "Reverb Width", 0.0, 1.0, 0.01, self.state.reverb_width),
                ("chorus_level", "Chorus Level", 0.0, 3.0, 0.05, self.state.chorus_level),
                ("chorus_speed", "Chorus Speed", 0.1, 1.5, 0.01, self.state.chorus_speed),
                ("chorus_depth", "Chorus Depth", 0.0, 16.0, 0.1, self.state.chorus_depth),
            ],
            "Mix": [
                ("master_gain", "Master Gain", 0.1, 1.2, 0.01, self.state.master_gain),
                ("pan", "Stereo Pan", -1.0, 1.0, 0.01, self.state.pan),
                ("stereo_width", "Stereo Width", 0.4, 1.8, 0.01, self.state.stereo_width),
            ],
            "EQ": [
                ("low_gain_db", "Low", -12.0, 12.0, 0.1, self.state.low_gain_db),
                ("mid_gain_db", "Mid", -12.0, 12.0, 0.1, self.state.mid_gain_db),
                ("high_gain_db", "High", -12.0, 12.0, 0.1, self.state.high_gain_db),
            ],
        }

        for group_name, configs in groups.items():
            box = QGroupBox(group_name)
            box_layout = QVBoxLayout(box)
            box_layout.setSpacing(10)
            for key, label, minimum, maximum, step, value in configs:
                control = SliderControl(label, minimum, maximum, step, value)
                control.valueChanged.connect(lambda _value, changed_key=key: self._control_changed(changed_key))
                self.controls[key] = control
                box_layout.addWidget(control)
            layout.addWidget(box)
        layout.addStretch(1)

    def set_state(self, state: EffectsState) -> None:
        self._updating = True
        self.state = state
        for key, control in self.controls.items():
            control.set_value(float(getattr(state, key)))
        self._updating = False

    def _control_changed(self, key: str) -> None:
        if self._updating:
            return
        setattr(self.state, key, self.controls[key].value())
        self.effectsChanged.emit(EffectsState.from_dict(self.state.to_dict()))


class LoopPadButton(QPushButton):
    triggered = Signal(str)

    def __init__(self, hotkey: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.hotkey = hotkey
        self.assignment: LoopAssignment | None = None
        self.active = False
        self.pulse = 0.25
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(160, 92)
        self.clicked.connect(lambda: self.triggered.emit(self.hotkey))

        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.28)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(900)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.InOutSine)
        self.animation.valueChanged.connect(self._animation_value_changed)

    def _animation_value_changed(self, value) -> None:
        self.pulse = float(value)
        self.update()

    def set_assignment(self, assignment: LoopAssignment | None) -> None:
        self.assignment = assignment
        self.update()

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.animation.start()
        else:
            self.animation.stop()
            self.pulse = 0.25
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)

        if self.active:
            glow = QColor(103, 215, 255, int(85 + 85 * self.pulse))
            painter.setPen(QPen(glow, 2.4))
            painter.setBrush(QColor("#133549"))
        elif self.assignment:
            painter.setPen(QPen(QColor("#2f4458"), 1.6))
            painter.setBrush(QColor("#121b25"))
        else:
            painter.setPen(QPen(QColor("#253240"), 1.3, Qt.DashLine))
            painter.setBrush(QColor("#0e141c"))

        painter.drawRoundedRect(rect, 14, 14)

        hotkey_font = QFont("Bahnschrift SemiBold", 9)
        title_font = QFont("Bahnschrift SemiBold", 11)
        meta_font = QFont("Bahnschrift", 8)

        painter.setFont(hotkey_font)
        painter.setPen(QColor("#90a4b5"))
        painter.drawText(rect.adjusted(12, 8, -12, -8), Qt.AlignLeft | Qt.AlignTop, f"PAD {self.hotkey}")

        painter.setFont(title_font)
        painter.setPen(QColor("#f8fbff"))
        title = self.assignment.label if self.assignment else "Unassigned"
        painter.drawText(rect.adjusted(12, 28, -12, -38), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, title)

        painter.setFont(meta_font)
        painter.setPen(QColor("#8aa2b4"))
        if self.assignment:
            meta = f"{self.assignment.instrument_id.replace('_', ' ').title()}  |  {self.assignment.pattern_name.replace('_', ' ').title()}"
        else:
            meta = "Click to toggle a saved loop assignment."
        painter.drawText(rect.adjusted(12, 56, -12, -10), Qt.AlignLeft | Qt.AlignBottom | Qt.TextWordWrap, meta)


class LoopPadsBar(QWidget):
    padTriggered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.buttons: dict[str, LoopPadButton] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        for index, hotkey in enumerate(["1", "2", "3", "4", "5", "6", "7", "8"]):
            button = LoopPadButton(hotkey)
            button.triggered.connect(self.padTriggered.emit)
            self.buttons[hotkey] = button
            layout.addWidget(button, index // 4, index % 4)

    def set_assignments(self, assignments: dict[str, LoopAssignment]) -> None:
        for hotkey, button in self.buttons.items():
            button.set_assignment(assignments.get(hotkey))

    def set_active(self, hotkey: str, active: bool) -> None:
        button = self.buttons.get(hotkey)
        if button:
            button.set_active(active)


class AssignmentEditor(QWidget):
    assignmentSaved = Signal(object)
    assignmentRemoved = Signal(str)
    hotkeySelectionChanged = Signal(str)

    def __init__(self, catalog: InstrumentCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._updating = False
        self.instrument_ids: list[str] = []

        title = QLabel("Loop Assignment")
        title.setProperty("sectionTitle", True)
        subtitle = QLabel("Bind layered loops and chord engines to the arranger pads on keys 1-8.")
        subtitle.setProperty("sectionSubtitle", True)

        self.hotkey_combo = QComboBox()
        self.hotkey_combo.addItems([str(index) for index in range(1, 9)])
        self.hotkey_combo.currentTextChanged.connect(self.hotkeySelectionChanged.emit)

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Warm drone / Teen taal / Brass stab loop")

        self.instrument_combo = QComboBox()
        self.root_combo = QComboBox()
        for label, midi_note in note_name_choices(48, 79):
            self.root_combo.addItem(label, midi_note)

        self.chord_combo = QComboBox()
        self.chord_combo.addItems(["major", "minor", "sus2", "sus4", "power", "drone"])

        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["sustain", "pulse", "arp_up", "arp_down", "shimmer", "keherwa", "teen_taal", "bhangra_drive", "four_on_floor"])

        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(50, 190)
        self.tempo_spin.setValue(108)

        self.bars_spin = QSpinBox()
        self.bars_spin.setRange(1, 4)
        self.bars_spin.setValue(1)

        self.velocity_spin = QSpinBox()
        self.velocity_spin.setRange(40, 127)
        self.velocity_spin.setValue(108)

        save_button = QPushButton("Save Assignment")
        remove_button = QPushButton("Clear Pad")
        save_button.clicked.connect(self._save_assignment)
        remove_button.clicked.connect(lambda: self.assignmentRemoved.emit(self.hotkey_combo.currentText()))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.addRow("Pad", self.hotkey_combo)
        form.addRow("Label", self.label_edit)
        form.addRow("Instrument", self.instrument_combo)
        form.addRow("Root", self.root_combo)
        form.addRow("Chord", self.chord_combo)
        form.addRow("Pattern", self.pattern_combo)
        form.addRow("Tempo", self.tempo_spin)
        form.addRow("Bars", self.bars_spin)
        form.addRow("Velocity", self.velocity_spin)

        button_row = QHBoxLayout()
        button_row.addWidget(save_button)
        button_row.addWidget(remove_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self._populate_instruments()

    def _populate_instruments(self) -> None:
        self.instrument_combo.clear()
        self.instrument_ids = []
        for instrument in self.catalog.all():
            self.instrument_combo.addItem(f"{instrument.label} ({instrument.family})", instrument.id)
            self.instrument_ids.append(instrument.id)

    def set_assignment(self, hotkey: str, assignment: LoopAssignment | None) -> None:
        self._updating = True
        self.hotkey_combo.setCurrentText(hotkey)
        if assignment is None:
            self.label_edit.clear()
            self.instrument_combo.setCurrentIndex(0)
            self.root_combo.setCurrentIndex(self.root_combo.findData(60))
            self.chord_combo.setCurrentText("major")
            self.pattern_combo.setCurrentText("sustain")
            self.tempo_spin.setValue(108)
            self.bars_spin.setValue(1)
            self.velocity_spin.setValue(108)
            self._updating = False
            return

        self.label_edit.setText(assignment.label)
        self.instrument_combo.setCurrentIndex(max(0, self.instrument_combo.findData(assignment.instrument_id)))
        self.root_combo.setCurrentIndex(max(0, self.root_combo.findData(assignment.root_midi)))
        self.chord_combo.setCurrentText(assignment.chord_name)
        self.pattern_combo.setCurrentText(assignment.pattern_name)
        self.tempo_spin.setValue(assignment.tempo_bpm)
        self.bars_spin.setValue(assignment.bars)
        self.velocity_spin.setValue(assignment.velocity)
        self._updating = False

    def _save_assignment(self) -> None:
        assignment = LoopAssignment(
            hotkey=self.hotkey_combo.currentText(),
            label=self.label_edit.text().strip() or f"Pad {self.hotkey_combo.currentText()}",
            instrument_id=str(self.instrument_combo.currentData()),
            root_midi=int(self.root_combo.currentData()),
            chord_name=self.chord_combo.currentText(),
            pattern_name=self.pattern_combo.currentText(),
            tempo_bpm=self.tempo_spin.value(),
            bars=self.bars_spin.value(),
            velocity=self.velocity_spin.value(),
        )
        self.assignmentSaved.emit(assignment)


class PerformancePanel(QWidget):
    soundfontSelected = Signal(str)
    soundfontRefreshRequested = Signal()
    soundfontBrowseRequested = Signal()
    presetLoadRequested = Signal(str)
    presetSaveRequested = Signal(str)
    transposeChanged = Signal(int)
    panicRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend_label = QLabel()
        self.backend_label.setWordWrap(True)
        self.backend_label.setProperty("statusBadge", "ok")

        title = QLabel("Performance")
        title.setProperty("sectionTitle", True)
        subtitle = QLabel("Audio backend status, SoundFont loading, preset recall, transpose and emergency all-notes-off.")
        subtitle.setProperty("sectionSubtitle", True)

        self.soundfont_combo = QComboBox()
        self.soundfont_combo.currentTextChanged.connect(self.soundfontSelected.emit)
        refresh_button = QPushButton("Refresh Fonts")
        browse_button = QPushButton("Load .sf2")
        refresh_button.clicked.connect(self.soundfontRefreshRequested.emit)
        browse_button.clicked.connect(self.soundfontBrowseRequested.emit)

        soundfont_row = QHBoxLayout()
        soundfont_row.addWidget(self.soundfont_combo, 1)
        soundfont_row.addWidget(refresh_button)
        soundfont_row.addWidget(browse_button)

        self.transpose_spin = QSpinBox()
        self.transpose_spin.setRange(-24, 24)
        self.transpose_spin.setValue(0)
        self.transpose_spin.valueChanged.connect(self.transposeChanged.emit)

        self.preset_list = QListWidget()
        load_button = QPushButton("Load Selected")
        save_button = QPushButton("Save Snapshot")
        panic_button = QPushButton("Panic")

        load_button.clicked.connect(self._emit_preset_load)
        save_button.clicked.connect(self._request_preset_save)
        panic_button.clicked.connect(self.panicRequested.emit)

        preset_buttons = QHBoxLayout()
        preset_buttons.addWidget(load_button)
        preset_buttons.addWidget(save_button)
        preset_buttons.addWidget(panic_button)

        form = QFormLayout()
        form.addRow("Transpose", self.transpose_spin)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.backend_label)
        layout.addLayout(soundfont_row)
        layout.addLayout(form)
        layout.addWidget(QLabel("Presets"))
        layout.addWidget(self.preset_list, 1)
        layout.addLayout(preset_buttons)

    def set_backend_status(self, text: str, ok: bool) -> None:
        self.backend_label.setText(text)
        self.backend_label.setProperty("statusBadge", "ok" if ok else "warn")
        self.style().unpolish(self.backend_label)
        self.style().polish(self.backend_label)

    def set_soundfonts(self, names: list[str], current_name: str | None) -> None:
        block = self.soundfont_combo.blockSignals(True)
        self.soundfont_combo.clear()
        self.soundfont_combo.addItem("No SoundFont Loaded")
        for name in names:
            self.soundfont_combo.addItem(name)
        if current_name:
            index = self.soundfont_combo.findText(current_name)
            if index >= 0:
                self.soundfont_combo.setCurrentIndex(index)
        self.soundfont_combo.blockSignals(block)

    def set_presets(self, preset_names: list[str]) -> None:
        self.preset_list.clear()
        for name in preset_names:
            self.preset_list.addItem(name)
        if self.preset_list.count():
            self.preset_list.setCurrentRow(0)

    def set_transpose(self, value: int) -> None:
        block = self.transpose_spin.blockSignals(True)
        self.transpose_spin.setValue(value)
        self.transpose_spin.blockSignals(block)

    def _emit_preset_load(self) -> None:
        item = self.preset_list.currentItem()
        if item is not None:
            self.presetLoadRequested.emit(item.text())

    def _request_preset_save(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name.strip():
            self.presetSaveRequested.emit(name.strip())
