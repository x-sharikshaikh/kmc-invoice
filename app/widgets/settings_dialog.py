from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
)

from app.core.settings import Settings, save_settings, load_settings, SETTINGS_PATH


class SettingsDialog(QDialog):
    """Dialog to edit application settings and logo path."""

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._orig = settings

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_business = QLineEdit(settings.business_name)
        self.ed_owner = QLineEdit(settings.owner)
        self.ed_phone = QLineEdit(settings.phone)
        self.ed_permit = QLineEdit(settings.permit)
        self.ed_pan = QLineEdit(settings.pan)
        self.ed_cheque_to = QLineEdit(settings.cheque_to)
        self.ed_thank_you = QLineEdit(settings.thank_you)
        self.ed_prefix = QLineEdit(settings.invoice_prefix)

        self.ed_logo = QLineEdit(settings.logo_path or "")
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_logo)
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.ed_logo)
        logo_row.addWidget(btn_browse)

        form.addRow("Business Name", self.ed_business)
        form.addRow("Owner", self.ed_owner)
        form.addRow("Phone", self.ed_phone)
        form.addRow("Permit", self.ed_permit)
        form.addRow("PAN", self.ed_pan)
        form.addRow("Cheque To", self.ed_cheque_to)
        form.addRow("Thank You", self.ed_thank_you)
        form.addRow("Invoice Prefix", self.ed_prefix)
        form.addRow("Logo Path", logo_row)

        root.addLayout(form)

        # Export / Import row (for settings.json)
        io_row = QHBoxLayout()
        self.btn_export = QPushButton("Export Settings")
        self.btn_import = QPushButton("Import Settings")
        self.btn_export.clicked.connect(self._export_settings)
        self.btn_import.clicked.connect(self._import_settings)
        io_row.addStretch(1)
        io_row.addWidget(self.btn_export)
        io_row.addWidget(self.btn_import)
        root.addLayout(io_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        # Reset to defaults button
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.clicked.connect(self._reset_defaults)
        root.addWidget(self.btn_reset)

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)",
        )
        if path:
            self.ed_logo.setText(path)

    def _export_settings(self) -> None:
        # Choose where to save a JSON dump of the current settings fields
        default_name = str(SETTINGS_PATH)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            default_name,
            "JSON (*.json);;All Files (*.*)",
        )
        if not path:
            return
        try:
            save_settings(self.result_settings(), path)
            QMessageBox.information(self, "Export Settings", "Settings exported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not export settings:\n{e}")

    def _import_settings(self) -> None:
        # Load a JSON file and populate the fields; user can then Save to persist
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            str(Path.home()),
            "JSON (*.json);;All Files (*.*)",
        )
        if not path:
            return
        try:
            s = load_settings(path)
            # Populate fields
            self.ed_business.setText(s.business_name)
            self.ed_owner.setText(s.owner)
            self.ed_phone.setText(s.phone)
            self.ed_permit.setText(s.permit)
            self.ed_pan.setText(s.pan)
            self.ed_cheque_to.setText(s.cheque_to)
            self.ed_thank_you.setText(s.thank_you)
            self.ed_prefix.setText(s.invoice_prefix)
            self.ed_logo.setText(s.logo_path or "")
            QMessageBox.information(self, "Import Settings", "Settings loaded. Click Save to apply.")
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Could not import settings:\n{e}")

    def result_settings(self) -> Settings:
        """Return a Settings object based on current inputs."""
        return Settings(
            business_name=self.ed_business.text().strip(),
            owner=self.ed_owner.text().strip(),
            phone=self.ed_phone.text().strip(),
            permit=self.ed_permit.text().strip(),
            pan=self.ed_pan.text().strip(),
            cheque_to=self.ed_cheque_to.text().strip(),
            thank_you=self.ed_thank_you.text().strip(),
            invoice_prefix=self.ed_prefix.text().strip() or self._orig.invoice_prefix,
            logo_path=(self.ed_logo.text().strip() or None),
        )

    def _reset_defaults(self) -> None:
        """Reset UI fields to default Settings (does not auto-save)."""
        s = Settings()
        self.ed_business.setText(s.business_name)
        self.ed_owner.setText(s.owner)
        self.ed_phone.setText(s.phone)
        self.ed_permit.setText(s.permit)
        self.ed_pan.setText(s.pan)
        self.ed_cheque_to.setText(s.cheque_to)
        self.ed_thank_you.setText(s.thank_you)
        self.ed_prefix.setText(s.invoice_prefix)
        self.ed_logo.setText(s.logo_path or "")
