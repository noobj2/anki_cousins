from typing import List, Iterable
from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QVBoxLayout,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QLineEdit,
    QLabel,
    QWidget,
)
from anki.hooks import addHook
from anki.collection import _Collection
from aqt import mw  # type: ignore

from .settings import SettingsManager, MatchRule, Comparisons


def show_settings_dialog() -> None:
    col: _Collection = mw.col

    dialog = QDialog(mw)
    dialog.setWindowTitle("Bury Cousins Options")

    dialog_layout = QVBoxLayout()
    dialog.setLayout(dialog_layout)

    note_types = {
        model["name"]: int(model["id"]) for model in col.models.models.values()
    }

    append = QPushButton("Add rule")

    buttons = QDialogButtonBox(QDialogButtonBox.Close | QDialogButtonBox.Save)  # type: ignore
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    buttons.setOrientation(Qt.Horizontal)

    form_grid = FormGrid()
    form_grid.appendRow(
        (
            QLabel("on note"),
            QLabel("match field"),
            QLabel("to note"),
            QLabel("match field"),
            QLabel("matcher"),
            QLabel("similarity"),
        )
    )

    match_forms: List[MatchRuleForm] = []
    for rule in SettingsManager(col).load():
        form = MatchRuleForm(note_types)

        try:
            form.set_values(rule)
        except TypeError:
            col.log("invalid cousin matching rule")
            continue

        form_grid.appendRow(form.fields)
        match_forms.append(form)

    def add_new_rule():
        form = MatchRuleForm(note_types)
        form_grid.appendRow(form.fields)
        match_forms.append(form)

    append.clicked.connect(add_new_rule)

    dialog_layout.addLayout(form_grid)
    dialog_layout.addWidget(append)
    dialog_layout.addWidget(buttons)

    if dialog.exec_():
        SettingsManager(col).save(
            [
                match_form.make_rule()
                for match_form in match_forms
                if match_form.is_valid()
            ]
        )


class FormGrid(QGridLayout):
    def appendRow(self, widgets: Iterable[QWidget]):
        row = self.rowCount()
        for col, element in enumerate(widgets):
            self.addWidget(element, row, col)


class MatchRuleForm:
    def __init__(self, note_types) -> None:
        self._my_note_type = QComboBox()
        for note_type, note_id in note_types.items():
            self._my_note_type.addItem(note_type, note_id)

        # TODO: turn LineEdits into QComboBox whose options are reset on
        # currentTextChanged.connect
        self._my_note_field = QLineEdit()

        self._other_note_type = QComboBox()
        for note_type, note_id in note_types.items():
            self._other_note_type.addItem(note_type, note_id)

        self._other_note_field = QLineEdit()

        self._matcher = QComboBox()
        self._matcher.addItem("by prefix", Comparisons.prefix)
        self._matcher.addItem("by similarity", Comparisons.similarity)
        self._matcher.addItem("contains", Comparisons.contains)
        self._matcher.addItem("contained by", Comparisons.contained_by)
        self._matcher.addItem(
            "cloze answers contained by", Comparisons.cloze_contained_by
        )

        self._threshold = QDoubleSpinBox()
        self._threshold.setMinimum(0)
        self._threshold.setMaximum(1)
        self._threshold.setSingleStep(0.05)
        self._threshold.setValue(0.95)

        self._delete = QCheckBox("delete?")

    @property
    def fields(self) -> List[QWidget]:
        return [
            self._my_note_type,
            self._my_note_field,
            self._other_note_type,
            self._other_note_field,
            self._matcher,
            self._threshold,
            self._delete,
        ]

    def set_values(self, rule: MatchRule) -> None:
        if rule.my_note_model_id:
            self._my_note_type.setCurrentIndex(
                self._my_note_type.findData(rule.my_note_model_id)
            )

        if rule.my_field:
            self._my_note_field.setText(rule.my_field)

        if rule.cousin_note_model_id:
            self._other_note_type.setCurrentIndex(
                self._other_note_type.findData(rule.cousin_note_model_id)
            )

        if rule.cousin_field:
            self._other_note_field.setText(rule.cousin_field)

        if rule.comparison:
            self._matcher.setCurrentIndex(self._matcher.findData(rule.comparison))

        if rule.threshold:
            self._threshold.setValue(rule.threshold)

    def make_rule(self) -> MatchRule:
        return MatchRule(
            int(self._my_note_type.currentData()),
            self._my_note_field.text(),
            int(self._other_note_type.currentData()),
            self._other_note_field.text(),
            self._matcher.currentData(),
            self._threshold.value(),
        )

    def is_valid(self) -> bool:
        if self._delete.isChecked():
            return False

        rule = self.make_rule()

        return (
            isinstance(rule.my_note_model_id, int)
            and isinstance(rule.cousin_note_model_id, int)
            and rule.my_field != ""
            and rule.cousin_field != ""
            and rule.threshold > 0
        )


@partial(addHook, "profileLoaded")
def profileLoaded():
    mw.addonManager.setConfigAction(__name__, show_settings_dialog)
