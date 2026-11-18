
"""
MCP Guardian - Desktop Control Window
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.approval.manager import ApprovalManager, ApprovalRequest
from app.desktop.bridge import ApprovalBridge
from app.desktop.notification import ApprovalDialog


logger = logging.getLogger(__name__)


class GuardianWindow(QMainWindow):

    def __init__(
        self,
        bridge: ApprovalBridge,
        approval_manager: ApprovalManager,
    ):
        super().__init__()

        self.bridge = bridge
        self.approval_manager = approval_manager

        self.dialogs: dict[str, ApprovalDialog] = {}

        self.setWindowTitle("MCP Guardian")
        self.setMinimumSize(420, 240)

        self._build_ui()

        self.bridge.request_created.connect(
            self.show_approval_dialog
        )

        self.bridge.gateway_error.connect(
            self.show_gateway_error
        )

        self.bridge.gateway_status.connect(
            self.update_status
        )

    def _build_ui(self):

        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("MCP Guardian")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Your MCP security gateway is active."
        )

        self.status_label = QLabel("Status: Starting...")
        self.pending_label = QLabel("Pending requests: 0")

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(15)
        layout.addWidget(self.status_label)
        layout.addWidget(self.pending_label)
        layout.addWidget(self.error_label)
        layout.addStretch()

        self.setCentralWidget(central)

    def show_approval_dialog(
        self,
        request: ApprovalRequest,
    ):

        logger.info(
            "Displaying approval dialog for %s",
            request.tool_name,
        )

        dialog = ApprovalDialog(
            request,
            self,
        )

        dialog.decision.connect(
            self._submit_decision
        )

        self.dialogs[request.request_id] = dialog

        dialog.finished.connect(
            lambda _result, request_id=request.request_id:
            self._remove_dialog(request_id)
        )

        self._update_pending_count()

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _submit_decision(
        self,
        request_id: str,
        allowed: bool,
    ):

        # decide() is thread-safe and schedules the decision
        # on the asyncio event loop.
        self.approval_manager.decide(
            request_id,
            allowed,
        )

    def _remove_dialog(self, request_id: str):

        self.dialogs.pop(request_id, None)

        self._update_pending_count()

    def _update_pending_count(self):

        self.pending_label.setText(
            f"Pending requests: {len(self.dialogs)}"
        )

    def update_status(self, message: str):

        self.status_label.setText(
            f"Status: {message}"
        )

    def show_gateway_error(self, message: str):

        self.status_label.setText("Status: Error")

        self.error_label.setText(
            f"Gateway error: {message}"
        )
