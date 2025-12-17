from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

class DropZone(QFrame):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("DropZone")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.label = QLabel("Drop a PDF here\n(or click Browse)")
        self.label.setAlignment(Qt.AlignCenter)

        lay = QVBoxLayout()
        lay.addWidget(self.label)
        self.setLayout(lay)

    def set_path(self, path: str) -> None:
        self.label.setText(f"Selected PDF:\n{path}")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.isLocalFile() and u.toLocalFile().lower().endswith(".pdf") for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        for u in urls:
            if u.isLocalFile():
                p = u.toLocalFile()
                if p.lower().endswith(".pdf"):
                    self.file_dropped.emit(p)
                    event.acceptProposedAction()
                    return
        event.ignore()
