from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFileDialog, QMessageBox,
                            QComboBox, QTableWidgetItem)
from PyQt5.QtCore import Qt
from .widgets.plot_canvas import BeamHistoryPlot, BeamResultPlot
from .widgets.copyable_table import CopyableTable
from core.acquisition_threads import AcquisitionThread
from core.data_processor import DataProcessor
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import csv


class BeamIntensityPage(QWidget):
    """流强测量页面"""
    def __init__(self):
        super().__init__()
        self.time_scal = 1e-4
        self.gain = 100
        # 新增：默认IP和通道
        self.selected_ip = "192.168.1.100"
        self.selected_channel = 1
        self.thread = None
        self.run_count = 0
        self.results = []
        self.current_result_idx = -1
        self.init_ui()
    
    def init_ui(self):
        """初始化UI组件"""
        # 创建左侧面板（图表和统计）
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # 历史趋势图
        self.history_plot = BeamHistoryPlot()
        self.avg_label = QLabel("流强平均值: 0")
        self.sigma_label = QLabel("标准差: 0")
        
        # 统计表格
        headers = ["运行次数", "束流流强 (mA)", "半高全宽 (μs)", "粒子数 (ppp)",]
        self.stat_table = CopyableTable(headers=headers)
        
        left_layout.addWidget(self.history_plot)
        left_layout.addWidget(self.avg_label)
        left_layout.addWidget(self.stat_table)
        left_panel.setLayout(left_layout)
        
        # 创建右侧面板（控制和结果查看）
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 控制面板
        ctrl_widget = QWidget()
        ctrl_layout = QVBoxLayout()
        
        self.run_input = QLineEdit("1")
        self.time_scal_input = QLineEdit(str(self.time_scal))
        self.gain_input = QLineEdit(str(self.gain))
        
        # 新增：IP选择下拉框
        self.ip_combo = QComboBox()
        self.ip_combo.addItems(["192.168.1.99", "192.168.1.100"])
        self.ip_combo.setCurrentText(self.selected_ip)
        
        # 新增：通道选择下拉框
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["1", "2", "3", "4"])
        self.channel_combo.setCurrentText(str(self.selected_channel))
        
        btn_start = QPushButton("开始")
        btn_stop = QPushButton("停止")
        btn_clear = QPushButton("清空")
        
        btn_start.clicked.connect(self.start_acquisition)
        btn_stop.clicked.connect(self.stop_acquisition)
        btn_clear.clicked.connect(self.clear_data)
        
        # 更新控制面板布局，添加IP和通道选择
        ctrl_layout.addWidget(QLabel("示波器IP地址:"))
        ctrl_layout.addWidget(self.ip_combo)
        ctrl_layout.addWidget(QLabel("示波器通道:"))
        ctrl_layout.addWidget(self.channel_combo)
        ctrl_layout.addWidget(QLabel("运行次数 (0=无限):"))
        ctrl_layout.addWidget(self.run_input)
        ctrl_layout.addWidget(QLabel("Time Scale:"))
        ctrl_layout.addWidget(self.time_scal_input)
        ctrl_layout.addWidget(QLabel("Gain:"))
        ctrl_layout.addWidget(self.gain_input)
        ctrl_layout.addWidget(btn_start)
        ctrl_layout.addWidget(btn_stop)
        ctrl_layout.addWidget(btn_clear)
        
        ctrl_widget.setLayout(ctrl_layout)
        
        # 结果查看器
        result_widget = QWidget()
        result_layout = QVBoxLayout()
        
        self.result_label = QLabel("运行: -")
        self.result_plot = BeamResultPlot()
        
        btn_prev = QPushButton("上一个")
        btn_next = QPushButton("下一个")
        btn_save = QPushButton("保存图片")
        btn_savedata = QPushButton("保存数据")
        
        btn_prev.clicked.connect(self.show_prev_result)
        btn_next.clicked.connect(self.show_next_result)
        btn_save.clicked.connect(self.save_result_image)
        btn_savedata.clicked.connect(self.save_result_data)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_prev)
        btn_layout.addWidget(btn_next)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_savedata)

        result_layout.addWidget(self.result_label)
        result_layout.addWidget(self.result_plot)
        result_layout.addLayout(btn_layout)
        
        result_widget.setLayout(result_layout)
        
        right_layout.addWidget(ctrl_widget)
        right_layout.addWidget(result_widget)
        right_panel.setLayout(right_layout)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_panel, 1)  # 左侧占1份
        main_layout.addWidget(right_panel, 1)  # 右侧占1份
        self.setLayout(main_layout)
    
    def start_acquisition(self):
        """开始数据采集（获取选中的IP和通道）"""
        # 停止当前线程（如果运行中）
        if self.thread and self.thread.isRunning():
            self.thread.stop()
        
        # 获取参数（新增IP和通道参数）
        try:
            count = int(self.run_input.text())
        except ValueError:
            count = 1
        
        try:
            self.time_scal = float(self.time_scal_input.text())
        except ValueError:
            self.time_scal = 1e-4
            self.time_scal_input.setText(str(self.time_scal))
        
        try:
            self.gain = float(self.gain_input.text())
        except ValueError:
            self.gain = 100
            self.gain_input.setText(str(self.gain))
        
        # 新增：获取选中的IP和通道
        self.selected_ip = self.ip_combo.currentText()
        self.selected_channel = int(self.channel_combo.currentText())
        
        # 创建并启动线程（需要确保线程能接收IP和通道参数）
        self.thread = AcquisitionThread(
            self.time_scal, 
            self.gain, 
            count,
            ip_address=self.selected_ip,  # 传递IP
            channel=self.selected_channel  # 传递通道
        )
        self.thread.data_acquired.connect(self.update_ui)
        self.thread.finished.connect(self.acquisition_finished)
        self.thread.start()
    
    # 以下方法保持不变，但需要确保AcquisitionThread类也做相应修改
    def stop_acquisition(self):
        """停止数据采集"""
        if self.thread and self.thread.isRunning():
            self.thread.stop()
    
    def acquisition_finished(self):
        """采集完成回调"""
        pass
    
    def update_ui(self, run_number, time_data, off_data, on_data, beam_data):
        """更新UI显示"""
        self.run_count += 1

        # 更新历史趋势图
        self.history_plot.add_data(self.run_count, beam_data)

        # 更新统计表格
        peak_value, fwhm = DataProcessor.calculate_peak_and_fwhm(time_data, beam_data)
        particle_number = DataProcessor.calculate_particle_count(beam_data,time_data)


        row = self.stat_table.rowCount()
        self.stat_table.insertRow(row)
        self.stat_table.setItem(row, 0, QTableWidgetItem(str(self.run_count)))
        self.stat_table.setItem(row, 1, QTableWidgetItem(f"{peak_value:.2f}"))
        self.stat_table.setItem(row, 2, QTableWidgetItem(f"{fwhm:.2f}"))
        self.stat_table.setItem(row, 3, QTableWidgetItem(f"{particle_number:.2e}"))


        # 更新流强平均值
        all_1 = [float(self.stat_table.item(i, 1).text()) for i in range(self.stat_table.rowCount())]
        all_2 = [float(self.stat_table.item(i, 2).text()) for i in range(self.stat_table.rowCount())]
        all_3 = [float(self.stat_table.item(i, 3).text()) for i in range(self.stat_table.rowCount())]
        overall_avg1 = np.mean(all_1)
        sigma2 = DataProcessor.calculate_sigma(all_1)
        overall_avg2 = np.mean(all_2)
        overall_avg3 = np.mean(all_3)
        self.avg_label.setText(f"流强平均值：{overall_avg1:.2f} mA, 流强标准差 {sigma2:.4f} mA, 半高全宽平均值：{overall_avg2:.2f} μs, 单脉冲粒子数平均值：{overall_avg3:.2e} ppp")




        # 保存结果并显示
        self.results.append((self.run_count, time_data, off_data, on_data, beam_data))
        self.current_result_idx = len(self.results) - 1
        self.show_current_result()
    
    def show_current_result(self):
        """显示当前结果"""
        if 0 <= self.current_result_idx < len(self.results):
            run, time_data, off_data, on_data, beam_data = self.results[self.current_result_idx]
            self.result_label.setText(f"运行: {run}")
            self.result_plot.plot_data(time_data, off_data, on_data, beam_data)
    
    def show_prev_result(self):
        """显示上一个结果"""
        if self.current_result_idx > 0:
            self.current_result_idx -= 1
            self.show_current_result()
    
    def show_next_result(self):
        """显示下一个结果"""
        if self.current_result_idx < len(self.results) - 1:
            self.current_result_idx += 1
            self.show_current_result()
    
    def save_result_image(self):
        """保存当前结果图像"""
        if 0 <= self.current_result_idx < len(self.results):
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存图像", f"beam_result_{self.results[self.current_result_idx][0]}.png",
                "PNG文件 (*.png);;JPEG文件 (*.jpg)", options=options
            )
            
            if file_path:
                time_data, off_data, on_data, beam_data = self.results[self.current_result_idx][1:]
                params = {'font.family': 'serif',
                          'font.serif': 'Times New Roman',
                          'font.style': 'normal',
                          'font.weight': 'normal',  # or 'blod'
                          'font.size': 9.3,  # or large,small
                          'lines.linewidth': 1,
                          'text.usetex': False  # False    # True
                          }

                fig2 = plt.figure(figsize=(85 / 25.4, 75 / 25.4))
                plt.rcParams.update(params)
                ax = fig2.add_subplot(111)
                line1 = ax.plot(time_data, off_data, 'b-', label='ABS-RF-OFF')
                line2 = ax.plot(time_data, on_data, 'g-', label='ABS-RF-ON')
                ax2 = ax.twinx()
                line3 = ax2.plot(time_data, beam_data, 'r-', label='Ion Beam From ABS')
                lines = line1 + line2 + line3
                labels = [_.get_label() for _ in lines]
                ax2.spines['right'].set_color('red')
                ax2.tick_params(axis='y', colors='red')
                ax.legend(lines, labels, frameon=False, borderaxespad=0.2, borderpad=0.2, labelspacing=0.2)
                # ax.set_yticks(np.array([10E10, 10E11, 10E12, 10E13, 10E14, 10E15]))
                ax.set_xlabel(r'Time ($\mu$s)')
                ax.set_ylabel(r'Ion Beam (mA)')
                ax2.set_ylabel(r'Ion Beam from ABS (mA)', color='r')
                fig2.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "成功", f"图像已保存至: {file_path}")
                plt.close(fig2)

    def save_result_data(self):
        """保存当前结果数据"""
        if 0 <= self.current_result_idx < len(self.results):
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存数据", f"beam_data_{self.results[self.current_result_idx][0]}.csv",
                "CSV文件 (*.csv)", options=options
            )
            
            if file_path:
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Time", "ABS-Off Data", "ABS-On Data", "Beam Data"])
                    time_data, off_data, on_data, beam_data = self.results[self.current_result_idx][1:]
                    for t, off, on, beam in zip(time_data, off_data, on_data, beam_data):
                        writer.writerow([t, off, on, beam])
                
                QMessageBox.information(self, "成功", f"数据已保存至: {file_path}")
            
    
    def clear_data(self):
        """清空所有数据"""
        self.stop_acquisition()
        self.run_count = 0
        self.results = []
        self.current_result_idx = -1
        
        self.history_plot.run_data = []
        self.history_plot.update_plot()
        
        self.stat_table.setRowCount(0)
        self.avg_label.setText("总体平均值: 0")
        self.result_label.setText("运行: -")
        self.result_plot.ax1.clear()
        self.result_plot.ax2.clear()
        self.result_plot.draw()