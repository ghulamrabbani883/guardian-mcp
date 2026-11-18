
"""
MCP Guardian - Tool Approval Dialog
"""

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.approval.manager import ApprovalRequest


class ApprovalDialog(QDialog):

    decision = Signal(str, bool)

    def __init__(
        self,
        request: ApprovalRequest,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.request = request

        self.setWindowTitle("MCP Guardian - Approval Required")
        self.setMinimumSize(520, 430)

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._build_ui()

    def _build_ui(self):

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        heading = QLabel("MCP Request Requires Approval")
        heading.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        warning = QLabel(
            "An application is requesting permission to execute an MCP tool."
        )
        warning.setWordWrap(True)

        server_label = QLabel(
            f"<b>Server:</b> {self.request.server_name}"
        )

        tool_label = QLabel(
            f"<b>Tool:</b> {self.request.tool_name}"
        )

        request_label = QLabel(
            f"<b>Request ID:</b> {self.request.request_id}"
        )
        request_label.setWordWrap(True)

        arguments_label = QLabel("<b>Tool arguments:</b>")

        arguments_view = QPlainTextEdit()
        arguments_view.setReadOnly(True)
        arguments_view.setPlainText(
            json.dumps(
                self.request.arguments,
                indent=4,
                ensure_ascii=False,
                default=str,
            )
        )

        allow_button = QPushButton("Allow")
        allow_button.setMinimumHeight(40)
        allow_button.setStyleSheet(
            """
            QPushButton {
                background-color: #15803d;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #166534;
            }
            """
        )

        block_button = QPushButton("Block")
        block_button.setMinimumHeight(40)
        block_button.setStyleSheet(
            """
            QPushButton {
                background-color: #b91c1c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #991b1b;
            }
            """
        )

        buttons = QHBoxLayout()
        buttons.addWidget(block_button)
        buttons.addWidget(allow_button)

        layout.addWidget(heading)
        layout.addWidget(warning)
        layout.addWidget(server_label)
        layout.addWidget(tool_label)
        layout.addWidget(request_label)
        layout.addWidget(arguments_label)
        layout.addWidget(arguments_view, 1)
        layout.addLayout(buttons)

        allow_button.clicked.connect(self._allow)
        block_button.clicked.connect(self._block)

    def _allow(self):
        self.decision.emit(
            self.request.request_id,
            True,
        )
        self.accept()

    def _block(self):
        self.decision.emit(
            self.request.request_id,
            False,
        )
        self.reject()

    def closeEvent(self, event):
        """
        Closing the dialog without making a decision is a denial.
        """

        self.decision.emit(
            self.request.request_id,
            False,
        )

        super().closeEvent(event)
