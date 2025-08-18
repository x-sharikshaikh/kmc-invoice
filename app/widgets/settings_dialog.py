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
        form.addRow("Logo Path (left)", logo_row)

        # Optional right-side name/logo path
        self.ed_right_logo = QLineEdit(getattr(settings, 'name_logo_path', None) or "")
        btn_browse_right = QPushButton("Browse…")
        btn_browse_right.clicked.connect(self._browse_right_logo)
        right_logo_row = QHBoxLayout()
        right_logo_row.addWidget(self.ed_right_logo)
        right_logo_row.addWidget(btn_browse_right)
        form.addRow("Name Logo Path (right)", right_logo_row)

        # Optional digital signature image
        self.ed_signature = QLineEdit(getattr(settings, 'signature_path', None) or "")
        btn_browse_sig = QPushButton("Browse…")
        btn_browse_sig.clicked.connect(self._browse_signature)
        sig_row = QHBoxLayout()
        sig_row.addWidget(self.ed_signature)
        sig_row.addWidget(btn_browse_sig)
        form.addRow("Signature Image (PNG/JPG)", sig_row)

        # Phase 3: File naming template and archive options
        self.ed_file_tpl = QLineEdit(settings.file_name_template)
        self.ed_file_tpl.setPlaceholderText("e.g. {number} - {customer}")
        form.addRow("File Name Template", self.ed_file_tpl)

        self.ed_archive_root = QLineEdit(settings.archive_root or "")
        btn_browse_root = QPushButton("Browse…")
        btn_browse_root.clicked.connect(self._browse_archive_root)
        root_row = QHBoxLayout()
        root_row.addWidget(self.ed_archive_root)
        root_row.addWidget(btn_browse_root)
        form.addRow("Archive Root", root_row)

        try:
            from PySide6.QtWidgets import QCheckBox
            self.chk_archive_by_year = QCheckBox("Group PDFs by year in subfolders")
            self.chk_archive_by_year.setChecked(bool(getattr(settings, 'archive_by_year', True)))
            form.addRow("Archive Options", self.chk_archive_by_year)
        except Exception:
            self.chk_archive_by_year = None

        # Phase 4: Compact mode
        try:
            from PySide6.QtWidgets import QCheckBox
            self.chk_compact = QCheckBox("Compact mode (denser spacing)")
            self.chk_compact.setChecked(bool(getattr(settings, 'compact_mode', False)))
            form.addRow("Display", self.chk_compact)
        except Exception:
            self.chk_compact = None

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

    def _browse_archive_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Archive Folder",
            str(Path.home()),
        )
        if path:
            self.ed_archive_root.setText(path)

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)",
        )
        if path:
            self.ed_logo.setText(path)

    def _browse_right_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Right-side Name Logo Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)",
        )
        if path:
            self.ed_right_logo.setText(path)

    def _browse_signature(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Digital Signature Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)",
        )
        if path:
            self.ed_signature.setText(path)

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
            try:
                self.ed_right_logo.setText(getattr(s, 'name_logo_path', None) or "")
            except Exception:
                pass
            try:
                self.ed_signature.setText(getattr(s, 'signature_path', None) or "")
            except Exception:
                pass
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
            name_logo_path=(self.ed_right_logo.text().strip() or None),
            signature_path=(self.ed_signature.text().strip() or None),
            file_name_template=(self.ed_file_tpl.text().strip() or self._orig.file_name_template),
            archive_root=(self.ed_archive_root.text().strip() or None),
            archive_by_year=bool(self.chk_archive_by_year.isChecked()) if self.chk_archive_by_year else True,
            compact_mode=bool(self.chk_compact.isChecked()) if self.chk_compact else False,
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
        try:
            self.ed_right_logo.setText(getattr(s, 'name_logo_path', None) or "")
        except Exception:
            pass
        try:
            self.ed_signature.setText(getattr(s, 'signature_path', None) or "")
        except Exception:
            pass
        try:
            self.ed_file_tpl.setText(s.file_name_template)
            self.ed_archive_root.setText(s.archive_root or "")
            if self.chk_archive_by_year:
                self.chk_archive_by_year.setChecked(bool(getattr(s, 'archive_by_year', True)))
            if self.chk_compact:
                self.chk_compact.setChecked(bool(getattr(s, 'compact_mode', False)))
        except Exception:
            pass
