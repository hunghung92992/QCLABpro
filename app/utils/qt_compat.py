# -*- coding: utf-8 -*-
"""
app/shared/qt_compat.py (V6 - Fixed CaseInsensitive)
Module tương thích PySide6 toàn diện.
Đã bổ sung CaseInsensitive và các Model/Item.
"""

import sys
import os

os.environ["QT_API"] = "pyside6"

try:
    from PySide6.QtCore import (
        Qt, QDate, QDateTime, QTime, QTimer, QAbstractItemModel, QSettings,
        QModelIndex, QPointF, Signal as pyqtSignal, Slot as pyqtSlot,
        QSize, QEvent, QObject, QThread, QByteArray, QBuffer, QUrl,
        QSortFilterProxyModel
    )
    from PySide6.QtGui import (
        QColor, QFont, QAction, QKeySequence, QBrush, QPen, QPainter,
        QIcon, QImage, QStandardItemModel, QStandardItem, QPixmap,
        QDesktopServices, QPageSize, QPageLayout, QPdfWriter,
        QPainterPath
    )
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QFormLayout, QGroupBox, QFrame,
        QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
        QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
        QDialog, QDialogButtonBox, QMessageBox, QFileDialog, QInputDialog,
        QTabWidget, QStackedWidget, QScrollArea, QMenu, QCompleter,
        QStyledItemDelegate, QStyleOptionViewItem, QSizePolicy,
        QGraphicsOpacityEffect,
        QListWidget, QListWidgetItem, QListView,
        QSplitter, QToolBar, QStatusBar,
        QFileSystemModel
    )
    from PySide6.QtPrintSupport import QPrinter

except ImportError:
    raise ImportError("LỖI: Chưa cài đặt PySide6. Hãy chạy: pip install PySide6")


# =============================================================================
# 🚑 MONKEY PATCHING (VÁ LỖI TỰ ĐỘNG)
# =============================================================================

# 1. Vá lỗi exec_()
try:
    QDialog.exec_ = QDialog.exec
    QMenu.exec_ = QMenu.exec
    QApplication.exec_ = QApplication.exec
except AttributeError: pass

# 2. Vá lỗi QMessageBox Enum
if not hasattr(QMessageBox, 'Yes'):
    QMessageBox.Yes = QMessageBox.StandardButton.Yes
    QMessageBox.No = QMessageBox.StandardButton.No
    QMessageBox.Ok = QMessageBox.StandardButton.Ok
    QMessageBox.Cancel = QMessageBox.StandardButton.Cancel
    QMessageBox.Save = QMessageBox.StandardButton.Save
    QMessageBox.Close = QMessageBox.StandardButton.Close
    QMessageBox.Discard = QMessageBox.StandardButton.Discard

# 3. Vá lỗi QHeaderView Enum
if not hasattr(QHeaderView, 'Stretch'):
    QHeaderView.Stretch = QHeaderView.ResizeMode.Stretch
    QHeaderView.ResizeToContents = QHeaderView.ResizeMode.ResizeToContents
    QHeaderView.Fixed = QHeaderView.ResizeMode.Fixed
    QHeaderView.Interactive = QHeaderView.ResizeMode.Interactive

# 4. Vá lỗi QAbstractItemView Enum
if not hasattr(QAbstractItemView, 'NoEditTriggers'):
    QAbstractItemView.NoEditTriggers = QAbstractItemView.EditTrigger.NoEditTriggers
    QAbstractItemView.CurrentChanged = QAbstractItemView.EditTrigger.CurrentChanged
    QAbstractItemView.DoubleClicked = QAbstractItemView.EditTrigger.DoubleClicked
    QAbstractItemView.SelectedClicked = QAbstractItemView.EditTrigger.SelectedClicked

if not hasattr(QAbstractItemView, 'SelectRows'):
    QAbstractItemView.SelectRows = QAbstractItemView.SelectionBehavior.SelectRows
    QAbstractItemView.SelectColumns = QAbstractItemView.SelectionBehavior.SelectColumns
    QAbstractItemView.SelectItems = QAbstractItemView.SelectionBehavior.SelectItems

if not hasattr(QAbstractItemView, 'SingleSelection'):
    QAbstractItemView.SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
    QAbstractItemView.MultiSelection = QAbstractItemView.SelectionMode.MultiSelection

# 5. Vá lỗi Màu & Cờ (Qt)
if not hasattr(Qt, 'red'):
    Qt.red = Qt.GlobalColor.red
    Qt.green = Qt.GlobalColor.green
    Qt.blue = Qt.GlobalColor.blue
    Qt.white = Qt.GlobalColor.white
    Qt.black = Qt.GlobalColor.black
    Qt.yellow = Qt.GlobalColor.yellow
    Qt.gray = Qt.GlobalColor.gray
    Qt.lightGray = Qt.GlobalColor.lightGray
    Qt.transparent = Qt.GlobalColor.transparent

if not hasattr(Qt, 'AlignCenter'):
    Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
    Qt.AlignLeft = Qt.AlignmentFlag.AlignLeft
    Qt.AlignRight = Qt.AlignmentFlag.AlignRight
    Qt.AlignTop = Qt.AlignmentFlag.AlignTop
    Qt.AlignBottom = Qt.AlignmentFlag.AlignBottom
    Qt.AlignVCenter = Qt.AlignmentFlag.AlignVCenter
    Qt.AlignHCenter = Qt.AlignmentFlag.AlignHCenter

# --- SỬA LỖI MATCH FLAGS & CASE SENSITIVITY ---
# PySide6 dùng Qt.MatchFlag.MatchFixedString thay vì MatchFixed
if not hasattr(Qt, 'MatchFixed'):
    Qt.MatchFixed = Qt.MatchFlag.MatchFixedString
    Qt.MatchContains = Qt.MatchFlag.MatchContains
    Qt.MatchExactly = Qt.MatchFlag.MatchExactly

# PySide6 dùng Qt.CaseSensitivity.CaseInsensitive
if not hasattr(Qt, 'CaseInsensitive'):
    Qt.CaseInsensitive = Qt.CaseSensitivity.CaseInsensitive
    Qt.CaseSensitive = Qt.CaseSensitivity.CaseSensitive

# Export ra ngoài module để dùng trực tiếp (như code cũ)
MatchFixed = Qt.MatchFixed
MatchContains = Qt.MatchContains
MatchExactly = Qt.MatchExactly
CaseInsensitive = Qt.CaseInsensitive  # <--- ĐÃ BỔ SUNG
CaseSensitive = Qt.CaseSensitive


# --- Helper Functions ---
def fill_combo_from_list(combo, items, id_key="id", text_key="name", add_empty=None):
    current_id = combo.currentData()
    combo.clear()
    if add_empty is not None: combo.addItem(add_empty, None)
    for item in items:
        val = item.get(id_key) if isinstance(item, dict) else getattr(item, id_key, None)
        txt = str(item.get(text_key, "")) if isinstance(item, dict) else str(getattr(item, text_key, ""))
        combo.addItem(txt, val)
    idx = combo.findData(current_id)
    if idx >= 0: combo.setCurrentIndex(idx)

def get_combo_id(combo): return combo.currentData()
def set_combo_by_id(combo, value):
    idx = combo.findData(value)
    if idx >= 0: combo.setCurrentIndex(idx)
def add_combo_item(combo, text, data=None): combo.addItem(text, data)
def clear_combo(combo): combo.clear()
def combo_find_text_ci(combo, text):
    if not text: return -1
    needle = text.strip().lower()
    for i in range(combo.count()):
        if combo.itemText(i).strip().lower() == needle: return i
    return -1
# ... (các đoạn code khác)

# --- ĐẢM BẢO USER ROLE TỒN TẠI ---
if not hasattr(Qt, 'UserRole'):
    # PySide6 thường để trong ItemDataRole, nhưng ta gán alias cho Qt.UserRole cho tiện
    try:
        Qt.UserRole = Qt.ItemDataRole.UserRole
    except AttributeError:
        # Fallback nếu version Qt quá cũ/mới lạ
        pass

# Export biến UserRole ra ngoài module
if hasattr(Qt, 'UserRole'):
    UserRole = Qt.UserRole
else:
    # Giá trị số nguyên mặc định của UserRole trong Qt là 32 (0x0100)
    UserRole = 32