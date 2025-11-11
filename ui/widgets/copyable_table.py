from PyQt5.QtWidgets import QTableWidget, QMenu, QAction
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QClipboard

class CopyableTable(QTableWidget):
    """支持复制功能的表格"""
    def __init__(self, rows=0, cols=4, headers=None):
        super().__init__(rows, cols)
        if headers:
            self.setHorizontalHeaderLabels(headers)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self._setup_context_menu()
    
    def _setup_context_menu(self):
        """设置右键菜单和快捷键"""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        
        # 添加复制动作
        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self._copy_selected)
        self.addAction(copy_action)
    
    def _show_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu()
        menu.addAction(self.actions()[0])  # 添加复制动作
        menu.exec_(self.mapToGlobal(pos))
    
    def _copy_selected(self):
        """复制选中单元格内容到剪贴板"""
        selected = self.selectedItems()
        if not selected:
            return
        
        # 获取选中区域范围
        min_row = min(item.row() for item in selected)
        max_row = max(item.row() for item in selected)
        min_col = min(item.column() for item in selected)
        max_col = max(item.column() for item in selected)
        
        # 构建表格数据
        data = []
        for row in range(min_row, max_row + 1):
            row_data = []
            for col in range(min_col, max_col + 1):
                item = self.item(row, col)
                row_data.append(item.text() if item else "")
            data.append("\t".join(row_data))
        
        # 复制到剪贴板
        clipboard = QClipboard()
        clipboard.setText("\n".join(data))