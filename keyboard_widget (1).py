from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


WHITE_NOTES = {0, 2, 4, 5, 7, 9, 11}
BLACK_OFFSETS = {1: 0.66, 3: 1.66, 6: 3.66, 8: 4.66, 10: 5.66}


@dataclass(slots=True)
class PianoKey:
    midi_note: int
    is_black: bool
    rect: QRectF


class PianoKeyboardWidget(QWidget):
    notePressed = Signal(int)
    noteReleased = Signal(int)

    def __init__(self, start_note: int = 48, end_note: int = 84, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.start_note = start_note
        self.end_note = end_note
        self.minimumHeight = 250
        self.setMinimumHeight(250)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.key_labels: dict[int, str] = {}
        self.pressed_notes: set[int] = set()
        self.white_keys: list[PianoKey] = []
        self.black_keys: list[PianoKey] = []
        self.anim_levels: dict[int, float] = {}
        self._mouse_note: int | None = None
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)
        self.animation_timer.timeout.connect(self._advance_animation)
        self.animation_timer.start()
        self._rebuild_keys()

    def set_key_labels(self, labels: dict[int, str]) -> None:
        self.key_labels = labels
        self.update()

    def set_note_state(self, midi_note: int, pressed: bool) -> None:
        if pressed:
            self.pressed_notes.add(midi_note)
            self.anim_levels[midi_note] = max(0.65, self.anim_levels.get(midi_note, 0.0))
        else:
            self.pressed_notes.discard(midi_note)
            self.anim_levels.setdefault(midi_note, 0.25)
        self.update()

    def _advance_animation(self) -> None:
        changed = False
        for midi_note in list(self.anim_levels):
            current = self.anim_levels[midi_note]
            target = 1.0 if midi_note in self.pressed_notes else 0.0
            current += (target - current) * 0.22
            if current < 0.02 and target == 0.0:
                self.anim_levels.pop(midi_note, None)
            else:
                self.anim_levels[midi_note] = current
            changed = True
        if changed:
            self.update()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._rebuild_keys()

    def _rebuild_keys(self) -> None:
        white_notes = [note for note in range(self.start_note, self.end_note + 1) if note % 12 in WHITE_NOTES]
        if not white_notes:
            return
        key_height = float(self.height()) - 20.0
        white_width = float(self.width()) / len(white_notes)
        white_y = 10.0

        self.white_keys = []
        self.black_keys = []
        white_positions: dict[int, float] = {}
        white_index = 0

        for midi_note in range(self.start_note, self.end_note + 1):
            pitch_class = midi_note % 12
            if pitch_class in WHITE_NOTES:
                x = white_index * white_width
                rect = QRectF(x, white_y, white_width, key_height)
                self.white_keys.append(PianoKey(midi_note, False, rect))
                white_positions[midi_note] = x
                white_index += 1

        black_width = white_width * 0.62
        black_height = key_height * 0.62
        for midi_note in range(self.start_note, self.end_note + 1):
            pitch_class = midi_note % 12
            if pitch_class not in BLACK_OFFSETS:
                continue
            octave = (midi_note // 12) - (self.start_note // 12)
            x = (octave * 7 + BLACK_OFFSETS[pitch_class]) * white_width - black_width / 2
            rect = QRectF(x, white_y, black_width, black_height)
            self.black_keys.append(PianoKey(midi_note, True, rect))

        self.update()

    def _key_at(self, pos: QPointF) -> int | None:
        for key in self.black_keys:
            if key.rect.contains(pos):
                return key.midi_note
        for key in self.white_keys:
            if key.rect.contains(pos):
                return key.midi_note
        return None

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        super().mousePressEvent(event)
        note = self._key_at(event.position())
        if note is None:
            return
        self._mouse_note = note
        self.set_note_state(note, True)
        self.notePressed.emit(note)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        super().mouseReleaseEvent(event)
        if self._mouse_note is not None:
            note = self._mouse_note
            self._mouse_note = None
            self.set_note_state(note, False)
            self.noteReleased.emit(note)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#090d13"))

        white_pen = QPen(QColor("#222b35"), 1.0)
        black_pen = QPen(QColor("#0d1117"), 1.0)
        label_font = QFont("Bahnschrift SemiBold", 9)
        note_font = QFont("Bahnschrift SemiBold", 8)

        for key in self.white_keys:
            glow = self.anim_levels.get(key.midi_note, 0.0)
            base = QColor("#f3f5f7")
            top = QColor("#ffffff")
            if glow > 0.0:
                accent = QColor("#f4b860")
                base = QColor(
                    int(base.red() * (1.0 - glow) + accent.red() * glow),
                    int(base.green() * (1.0 - glow) + accent.green() * glow),
                    int(base.blue() * (1.0 - glow) + accent.blue() * glow),
                )
                top = QColor("#ffe7bf")

            gradient = QLinearGradient(key.rect.topLeft(), key.rect.bottomLeft())
            gradient.setColorAt(0.0, top)
            gradient.setColorAt(1.0, base)
            painter.setBrush(gradient)
            painter.setPen(white_pen)
            path = QPainterPath()
            path.addRoundedRect(key.rect.adjusted(1, 1, -1, -1), 7, 7)
            painter.drawPath(path)

            painter.setPen(QColor("#1c2530"))
            painter.setFont(label_font)
            label = self.key_labels.get(key.midi_note, "")
            if label:
                painter.drawText(key.rect.adjusted(0, 0, 0, -18), Qt.AlignHCenter | Qt.AlignBottom, label)
            painter.setFont(note_font)
            painter.setPen(QColor("#51606f"))
            painter.drawText(key.rect.adjusted(0, 18, 0, -6), Qt.AlignHCenter | Qt.AlignBottom, self._note_name(key.midi_note))

        for key in self.black_keys:
            glow = self.anim_levels.get(key.midi_note, 0.0)
            gradient = QLinearGradient(key.rect.topLeft(), key.rect.bottomLeft())
            gradient.setColorAt(0.0, QColor("#2d3642") if glow == 0 else QColor("#1c5f7f"))
            gradient.setColorAt(1.0, QColor("#0b0f14") if glow == 0 else QColor("#0f2f42"))
            painter.setBrush(gradient)
            painter.setPen(black_pen)
            path = QPainterPath()
            path.addRoundedRect(key.rect, 6, 6)
            painter.drawPath(path)
            if glow > 0.02:
                painter.setPen(QPen(QColor(103, 215, 255, int(170 * glow)), 2.0))
                painter.drawRoundedRect(key.rect.adjusted(1.5, 1.5, -1.5, -1.5), 6, 6)

            painter.setPen(QColor("#d9edf7"))
            painter.setFont(label_font)
            label = self.key_labels.get(key.midi_note, "")
            if label:
                painter.drawText(key.rect.adjusted(0, 0, 0, -10), Qt.AlignHCenter | Qt.AlignBottom, label)

    @staticmethod
    def _note_name(midi_note: int) -> str:
        names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        octave = (midi_note // 12) - 1
        return f"{names[midi_note % 12]}{octave}"
