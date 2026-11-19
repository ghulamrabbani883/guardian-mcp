"""
MCP Guardian - System Tray
"""

import logging

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QStyle
logger = logging.getLogger(__name__)


class GuardianTray:

    def __init__(self, app, window):

        self.app = app
        self.window = window

        self.tray = QSystemTrayIcon(
            app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )

        self.tray.setToolTip("MCP Guardian")

        menu = QMenu()

        show_action = QAction("Show Guardian", menu)
        show_action.triggered.connect(self.show_window)

        exit_action = QAction("Exit Guardian", menu)
        exit_action.triggered.connect(self.exit_app)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)

        self.tray.activated.connect(self._on_activated)

        self.tray.show()

        logger.info("Guardian system tray initialized")

    def show_window(self):

        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def exit_app(self):

        logger.info("Exit requested from system tray")
        self.tray.hide()
        self.app.quit()

    def _on_activated(self, reason):

        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()