from __future__ import annotations

from pathlib import Path
from typing import Optional
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from app.pdf.pdf_draw import build_invoice_pdf


class PdfPreviewDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Invoice Preview")
        self.resize(900, 700)

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title = QLabel("Preview")
        top.addWidget(self.title)
        top.addStretch(1)
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_in = QPushButton("+")
        self.btn_fit_width = QPushButton("Fit Width")
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_fit_width):
            top.addWidget(b)
        v.addLayout(top)

        self._pdf_view = None
        self._pdf_doc = None
        try:
            from PySide6.QtPdfWidgets import QPdfView  # type: ignore
            from PySide6.QtPdf import QPdfDocument  # type: ignore
            self._pdf_view = QPdfView(self)
            self._pdf_doc = QPdfDocument(self)
            v.addWidget(self._pdf_view, 1)
            # Wire zoom controls if available
            self.btn_zoom_in.clicked.connect(lambda: self._pdf_view.setZoomFactor(self._pdf_view.zoomFactor() * 1.1))
            self.btn_zoom_out.clicked.connect(lambda: self._pdf_view.setZoomFactor(self._pdf_view.zoomFactor() / 1.1))
            self.btn_fit_width.clicked.connect(lambda: self._pdf_view.setZoomMode(getattr(QPdfView, 'ZoomMode', None).FitToWidth if hasattr(QPdfView, 'ZoomMode') else 1))
        except Exception:
            fallback = QLabel("Preview not available on this system. The PDF will open in your default viewer.")
            fallback.setWordWrap(True)
            v.addWidget(fallback)

        self._temp_pdf: Optional[Path] = None

    def load_from_data(self, data: dict) -> bool:
        """Build a temporary PDF from data and load it into the viewer.
        Returns True if loaded in-app; False if a fallback should be used.
        """
        # Build temp PDF
        tmpdir = Path(tempfile.gettempdir()) / "kmc_invoice_preview"
        tmpdir.mkdir(parents=True, exist_ok=True)
        out = tmpdir / "preview.pdf"
        try:
            build_invoice_pdf(out, data)
        except Exception:
            return False
        self._temp_pdf = out
        if self._pdf_view is not None:
            try:
                self._pdf_doc.load(str(out))
                self._pdf_view.setDocument(self._pdf_doc)
                return True
            except Exception:
                return False
        return False

    def temp_path(self) -> Optional[Path]:
        return self._temp_pdf
