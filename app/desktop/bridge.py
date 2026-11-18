
"""
MCP Guardian - Qt / Asyncio Communication Bridge
"""

from PySide6.QtCore import QObject, Signal


class ApprovalBridge(QObject):
    """
    Transfers approval notifications from the asyncio thread
    to the Qt main thread.
    """

    request_created = Signal(object)
    gateway_error = Signal(str)
    gateway_status = Signal(str)
