from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMenu, QAction, 
                            QFileDialog, QMessageBox)
from .beam_intensity_page import BeamIntensityPage
from .polarization_page import PolarizationPage

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPIS测量系统")
        self.setGeometry(100, 100, 1200, 800)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 创建各功能页面
        self.beam_intensity_page = BeamIntensityPage()
        self.polarization_page = PolarizationPage()
        
        # 添加标签页
        self.tabs.addTab(self.beam_intensity_page, "流强测量")
        self.tabs.addTab(self.polarization_page, "极化率测量")
        
        # 设置中心部件
        self.setCentralWidget(self.tabs)
        
        # 创建菜单栏
        self.create_menu()
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 保存数据动作
        save_action = QAction("保存数据", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(save_action)
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def save_data(self):
        """保存当前标签页的数据"""
        current_index = self.tabs.currentIndex()
        
        if current_index == 0:  # 流强测量页面
            if not self.beam_intensity_page.stat_table.rowCount():
                QMessageBox.warning(self, "警告", "没有数据可保存")
                return
                
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存流强数据", "beam_intensity_data.csv",
                "CSV文件 (*.csv);;所有文件 (*)",
                options=options
            )

            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        # 写入表头
                        headers = [self.beam_intensity_page.stat_table.horizontalHeaderItem(i).text() 
                                  for i in range(self.beam_intensity_page.stat_table.columnCount())]
                        f.write(",".join(headers) + "\n")
                        
                        # 写入数据
                        for row in range(self.beam_intensity_page.stat_table.rowCount()):
                            row_data = []
                            for col in range(self.beam_intensity_page.stat_table.columnCount()):
                                item = self.beam_intensity_page.stat_table.item(row, col)
                                row_data.append(item.text() if item else "")
                            f.write(",".join(row_data) + "\n")
                    
                    QMessageBox.information(self, "成功", f"数据已保存至: {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"保存数据时出错: {str(e)}")
                    
        elif current_index == 1:  # 极化率测量页面
            if not self.polarization_page.stat_table.rowCount():
                QMessageBox.warning(self, "警告", "没有数据可保存")
                return
                
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存极化率数据", "polarization_data.csv",
                "CSV文件 (*.csv);;所有文件 (*)",
                options=options
            )
            
            if file_path:
                try:
                    with open(file_path, 'w') as f:
                        # 写入表头
                        headers = [self.polarization_page.stat_table.horizontalHeaderItem(i).text() 
                                  for i in range(self.polarization_page.stat_table.columnCount())]
                        f.write(",".join(headers) + "\n")
                        
                        # 写入数据
                        for row in range(self.polarization_page.stat_table.rowCount()):
                            row_data = []
                            for col in range(self.polarization_page.stat_table.columnCount()):
                                item = self.polarization_page.stat_table.item(row, col)
                                row_data.append(item.text() if item else "")
                            f.write(",".join(row_data) + "\n")
                    
                    QMessageBox.information(self, "成功", f"数据已保存至: {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"保存数据时出错: {str(e)}")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
            "离子束流强与极化率测量系统\n"
            "版本: 1.0.0\n\n"
            "本系统用于测量和分析离子束流强和极化率数据。\n"
            "支持数据采集、实时绘图、统计分析和数据导出。"
        )
    
    def closeEvent(self, event):
        """关闭窗口时的事件处理"""
        # 停止所有运行中的线程
        if self.beam_intensity_page.thread and self.beam_intensity_page.thread.isRunning():
            self.beam_intensity_page.thread.stop()

        '''if self.polarization_page.thread and self.polarization_page.thread.isRunning():
            self.polarization_page.thread.stop()'''
        
        event.accept()