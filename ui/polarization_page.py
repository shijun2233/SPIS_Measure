import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFileDialog, QMessageBox, QTextBrowser,
                             QTableWidget, QTableWidgetItem, QComboBox, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
import csv
from datetime import datetime
from RsInstrument import RsInstrument, BinFloatFormat
import time
from scipy.signal import butter, filtfilt
# 假设 PTNhpController 已正确实现
from core.ptnhp_con import PTNhpController
import re


def calculate_polarization(signal, background, particle_type='proton'):
    def get_max_in_ranges(data, ranges):
        max_results = []
        for r in ranges:
            idx = np.where((data[:, 0] >= r[0]) & (data[:, 0] < r[1]))[0]
            if len(idx) > 0:
                max_idx = idx[np.argmax(data[idx, 1])]
                max_val = data[max_idx, 1]
                max_results.append((max_idx, data[max_idx, 0], max_val))
            else:
                max_results.append((None, None, None))
        return max_results

    result = {}

    if particle_type.lower() in ['proton', 'p', 'h']:
        peak_bp_idx = np.argmax(background[:, 1][0:100])
        peak_bn_idx = np.argmax(background[:, 1][100:200]) + 100
        peak_p_idx = np.argmax(signal[:, 1][0:100])
        peak_n_idx = np.argmax(signal[:, 1][100:200]) + 100

        Nbp_list = sorted(background[:, 1][peak_bp_idx - 5:peak_bp_idx + 5])[:-1]
        Nbp = np.mean(sorted(Nbp_list)[-4:])
        Nbn_list = sorted(background[:, 1][peak_bn_idx - 5:peak_bn_idx + 5])[:-1]
        Nbn = np.mean(sorted(Nbn_list)[-4:])
        Np_list = sorted(signal[:, 1][peak_p_idx - 5:peak_p_idx + 5])[:-1]
        Np = np.mean(sorted(Np_list)[-4:])
        Nn_list = sorted(signal[:, 1][peak_n_idx - 5:peak_n_idx + 5])[:-1]
        Nn = np.mean(sorted(Nn_list)[-4:])

        polarization = ((Np - Nbp) - (Nn - Nbn)) / ((Np - Nbp) + (Nn - Nbn))
        result['polarization'] = polarization
        result['peak_signal'] = [[signal[peak_p_idx, 0], signal[peak_n_idx, 0]], [Np, Nn]]
        result['peak_background'] = [[background[peak_bp_idx, 0], background[peak_bn_idx, 0]], [Nbp, Nbn]]
        return result

    elif particle_type.lower() in ['deuteron', 'd', 'D']:
        ranges = [(560, 570), (570, 580), (580, 590)]
        max_WFT_ON = get_max_in_ranges(signal, ranges)
        max_Background = get_max_in_ranges(background, ranges)
        max_WFT_ON_index = [max_WFT_ON[i][0] for i in range(3)]
        max_Background_index = [max_Background[i][0] for i in range(3)]

        Nbp_list = sorted([background[:, 1][max_Background_index[0] - 5: max_Background_index[0] + 5]])[0][:-1]
        Nbp = np.mean(sorted(Nbp_list)[-4:])
        Nb0_list = sorted([background[:, 1][max_Background_index[1] - 5: max_Background_index[1] + 5]])[0][:-1]
        Nb0 = np.mean(sorted(Nb0_list)[-4:])
        Nbn_list = sorted([background[:, 1][max_Background_index[2] - 5: max_Background_index[2] + 5]])[0][:-1]
        Nbn = np.mean(sorted(Nbn_list)[-4:])

        Np_list = sorted([signal[:, 1][max_WFT_ON_index[0] - 5: max_WFT_ON_index[0] + 5]])[0][:-1]
        Np = np.mean(sorted(Np_list)[-4:])
        N0_list = sorted([signal[:, 1][max_WFT_ON_index[1] - 5: max_WFT_ON_index[1] + 5]])[0][:-1]
        N0 = np.mean(sorted(N0_list)[-4:])
        Nn_list = sorted([signal[:, 1][max_WFT_ON_index[2] - 5: max_WFT_ON_index[2] + 5]])[0][:-1]
        Nn = np.mean(sorted(Nn_list)[-4:])

        P_z = ((Np - Nbp) - (Nn - Nbn)) / ((Np - Nbp) + (N0 - Nb0) + (Nn - Nbn))
        P_zz = ((Np - Nbp) - 2 * (N0 - Nb0) + (Nn - Nbn)) / ((Np - Nbp) + (N0 - Nb0) + (Nn - Nbn))
        result['P_z'] = P_z
        result['P_zz'] = P_zz
        result['peak_signal'] = ([max_WFT_ON[0][1], max_WFT_ON[1][1], max_WFT_ON[2][1]], [Np, N0, Nn])
        result['peak_background'] = ([max_Background[0][1], max_Background[1][1], max_Background[2][1]], [Nbp, Nb0, Nbn])
        return result
    else:
        raise ValueError("Unsupported particle type. Use 'proton' or 'deuteron'.")


def integrate_waveform(data, total_time=1.2E-3, method='trapezoid'):
    dt = total_time / len(data)
    if method == 'trapz':
        return np.trapezoid(data, dx=dt)
    elif method == 'cumtrapz':
        return np.cumsum(data) * dt
    else:
        raise ValueError(f"不支持的积分方法: {method}。请使用'trapz'或'cumtrapz'。")


def moving_average(data, window_size):
    weights = np.repeat(1.0, window_size) / window_size
    return np.convolve(data, weights, 'valid')


def oscilloscope_preset(instr):
    instr.write_str('*RST')
    time.sleep(0.01)

    instr.write_str('CHAN1:STAT ON')
    instr.write_str('CHAN3:STAT ON')
    instr.write_str('CHAN4:STAT ON')
    instr.write_str('CHAN2:STAT ON')

    instr.write_str('TIM:ROLL:AUT OFF')
    instr.write_str('ACQ:HRES AUTO')

    instr.write_str('PROB1:SET:GAIN:MAN 0.1')
    instr.write_str('PROB2:SET:GAIN:MAN 1')

    instr.write_str('TIM:SCAL 1e-4')
    instr.write_str('TIM:REF 8.33')
    instr.write_str('CHAN1:SCAL 1')
    instr.write_str('CHAN1:POS -4')
    instr.write_str('CHAN2:SCAL 1')
    instr.write_str('CHAN2:POL INV')
    instr.write_str('CHAN2:POS -4')
    instr.write_str('CHAN3:SCAL 1')
    instr.write_str('CHAN3:POS -4')
    instr.write_str('CHAN4:SCAL 1')
    instr.write_str('CHAN4:POS -4')
    instr.write_str('CHAN1:COUP DCLimit')
    instr.write_str('CHAN2:COUP DCLimit')
    instr.write_str('CHAN3:COUP DCLimit')
    instr.write_str('CHAN4:COUP DCLimit')
    instr.write_str('TRIG:A:MODE NORM')
    instr.write_str('TRIG:A:SOUR CH3')
    instr.write_str('TRIG:A:TYPE EDGE')
    instr.write_str('TRIG:A:EDGE:SLOP POS')
    instr.write_str('TRIG:A:LEV3:VAL 2')
    instr.write_str('ACQuire:NSINgle:COUNt 1')
    instr.write_str('TRIG:OUT:MODE TRIG')
    instr.write_str('TRIG:OUT:PLEN 2E-4')
    instr.write_str('TRIG:OUT:POL POS')

    instr.query_opc()


class DataAcquisitionThread(QThread):
    update_oscilloscope_signal = pyqtSignal(np.ndarray, np.ndarray)
    update_scatter_signal = pyqtSignal(float, float, str)
    acquisition_finished = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    current_updated = pyqtSignal(float)  # 新增：发送当前电流信号

    def __init__(self, measurement_type, particle_type, gain_factor, bfield_array, parent, last_current=0.0):
        super().__init__()
        self.measurement_type = measurement_type
        self.particle_type = particle_type
        self.gain_1 = gain_factor
        self.bfield_array = bfield_array
        self.parent = parent
        self.last_current = last_current  # 接收上次测量的最终电流
        self.stop_requested = False

    def run(self):
        try:
            ptnhp = PTNhpController(ip="192.168.1.123", port=7, timeout=5, terminator='\n')
            if not ptnhp.connect():
                self.error_occurred.emit("PTNhp 电源连接失败")
                return

            if self.last_current != 0.0:
                ptnhp.set_current(self.last_current)
                time.sleep(0.5)

            instr = RsInstrument('TCPIP::192.168.1.99::INSTR', True, False)

            photons = []
            # 关键修复：创建 bfield_array 的副本，避免修改原始数据
            BFields_settings = self.bfield_array.copy()
            measured_BFields = np.zeros_like(BFields_settings)  # 用于存储实际测量值
            Currents = BFields_settings * 2 / 103.6

            final_current = self.last_current

            for i in range(len(BFields_settings)):
                if self.stop_requested:
                    self.error_occurred.emit("测量已被手动停止")
                    break

                BField_val = BFields_settings[i]
                current = Currents[i]

                ptnhp.set_current(current)
                time.sleep(0.1)
                self.current_updated.emit(current)

                instr.write_str_with_opc("SINGle", 50000)
                instr.write_str("FORMat:DATA REAL,32")
                instr.bin_float_numbers_format = BinFloatFormat.Single_4bytes_swapped
                instr.data_chunk_size = 100000

                data_photon = np.array(instr.query_bin_or_ascii_float_list("CHAN2:DATA?"))
                data_BField = np.array(instr.query_bin_or_ascii_float_list("CHAN3:DATA?"))
                self.update_oscilloscope_signal.emit(data_photon, data_BField)

                temp_photon = moving_average(data_photon, 200)
                photon = integrate_waveform(temp_photon, total_time=1.2E-3, method='trapz')
                photons.append(photon)

                # 将实际测量值存入新数组
                measured_BFields[i] = np.mean(data_BField)

                photon_val = photon * self.gain_1
                # 使用实际测量值更新散点图
                self.update_scatter_signal.emit(measured_BFields[i], photon_val, self.measurement_type)
                time.sleep(0.001)

            self.parent.last_current = final_current
            self.error_occurred.emit(f"测量结束，当前磁场电流为: {final_current:.4f} A")

            photons = np.array(photons) * self.gain_1
            # 使用实际测量的磁场值与光子数据合并
            merged = np.column_stack((measured_BFields, photons))
            self.acquisition_finished.emit(merged)

        except Exception as e:
            self.error_occurred.emit(f'发生错误: {e}')
        finally:
            if 'instr' in locals():
                instr.close()
            if 'ptnhp' in locals():
                ptnhp.close()


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=300):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        para = {'font.family': 'serif',
                'font.serif': 'Times New Roman',
                'font.style': 'normal',
                'font.weight': 'normal',
                'font.size': 9.3,
                'lines.linewidth': 1,
                'text.usetex': False}
        plt.rcParams.update(para)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)


class ResultCanvas(MplCanvas):
    def __init__(self, parent=None, width=6, height=4, dpi=300):
        super().__init__(parent, width, height, dpi)
        self.background_points = []
        self.unpolarized_points = []
        self.polarized_points = []
        self.axes.set_title("Measurement Results")
        self.axes.set_xlabel('B-Field (Gs)')
        self.axes.set_ylabel('PMT Anode Signal (A. U.)')
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.axes.plot([], [], ' ', label=' ')
        self.fig.tight_layout()

    def add_scatter_point(self, x, y, data_type):
        if data_type == "background":
            self.background_points.append((x, y))
            color = 'blue'
            marker = 'o'
            label = 'Background' if len(self.background_points) == 1 else ""
        elif data_type == "unpolarized":
            self.unpolarized_points.append((x, y))
            color = 'green'
            marker = 's'
            label = 'Unpolarized Ion Beam' if len(self.unpolarized_points) == 1 else ""
        elif data_type == "polarized":
            self.polarized_points.append((x, y))
            color = 'red'
            marker = '^'
            label = 'Polarized Ion Beam' if len(self.polarized_points) == 1 else ""
        else:
            return

        self.axes.scatter(x, y, color=color, marker=marker, label=label, alpha=0.7)
        self.update_legend()
        self.fig.tight_layout()
        self.draw()

    def update_legend(self):
        if self.axes.get_legend():
            self.axes.get_legend().remove()

        handles, labels = self.axes.get_legend_handles_labels()
        valid_labels = []
        valid_handles = []

        for handle, label in zip(handles, labels):
            if label and label != ' ' and label not in valid_labels:
                valid_labels.append(label)
                valid_handles.append(handle)

        if valid_handles:
            self.axes.legend(valid_handles, valid_labels)

    def clear(self):
        self.background_points = []
        self.unpolarized_points = []
        self.polarized_points = []
        self.axes.clear()
        self.axes.set_title("Measurement Results")
        self.axes.set_xlabel('B-Field (Gs)')
        self.axes.set_ylabel('PMT Anode Signal (A. U.)')
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.axes.plot([], [], ' ', label=' ')
        self.fig.tight_layout()
        self.draw()


class PolarizationPage(QWidget):
    def __init__(self):
        super().__init__()
        self.time_scal = 1e-4
        self.gain = 100
        self.gain_photon = 1e-6
        self.analyzing_power = 0.3
        self.background_data = None
        self.unpolarized_data = None
        self.polarized_data = None
        self.acquisition_thread = None
        self.last_photon_data = None
        self.last_BField_data = None
        self.bfield_array = None  # 关键：存储全局磁场表
        self.prepare_thread = None
        self.ramp_steps = 100
        self.ramp_target_I = 10.0
        self.ramp_start_I = 0.0
        self.stop_requested = False
        self.stop_thread = None
        self.last_current = 0.0
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        control_layout = QHBoxLayout()
        self.btn_prepare = QPushButton("准备测量")
        self.btn_prepare.clicked.connect(self.prepare_measurement)
        control_layout.addWidget(self.btn_prepare)
        self.btn_stop = QPushButton("停止测量")
        self.btn_stop.clicked.connect(self.stop_measurement)
        control_layout.insertWidget(1, self.btn_stop)
        self.btn_stop_current = QPushButton("停止电流输出")
        self.btn_stop_current.clicked.connect(self.stop_current)
        control_layout.insertWidget(1, self.btn_stop_current)
        self.btn_redefine_bfield = QPushButton("定义磁场表")
        self.btn_redefine_bfield.clicked.connect(self.redefine_bfield)
        control_layout.addWidget(self.btn_redefine_bfield)

        self.btn_background = QPushButton("测量本底")
        self.btn_background.clicked.connect(self.measure_background)
        self.btn_unpolarized = QPushButton("测量非极化离子")
        self.btn_unpolarized.clicked.connect(self.measure_unpolarized)
        self.btn_polarized = QPushButton("测量极化离子")
        self.btn_polarized.clicked.connect(self.measure_polarized)
        self.btn_clear = QPushButton("清除数据")
        self.btn_clear.clicked.connect(self.clear_data)
        self.btn_save = QPushButton("保存结果")
        self.btn_save.clicked.connect(self.save_results)
        self.btn_load = QPushButton("读取数据")
        self.btn_load.clicked.connect(self.load_results)
        self.cb_particle = QComboBox()
        self.cb_particle.addItems(["H", "D"])
        self.cb_osc_channel = QComboBox()
        self.cb_osc_channel.addItems(["CHAN2 (光子)", "CHAN3 (磁场)"])
        self.cb_osc_channel.currentIndexChanged.connect(self.update_oscilloscope_display)
        self.gain_label = QLabel("光信号增益：")
        self.gain_input = QLineEdit(str(self.gain_photon))

        for widget in [self.btn_background, self.btn_unpolarized, self.btn_polarized,
                       self.btn_clear, self.btn_save, self.btn_load, self.cb_particle, self.cb_osc_channel,
                       self.gain_label, self.gain_input]:
            control_layout.addWidget(widget)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        self.gridLayout = QGridLayout()
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.setRowStretch(1, 2)
        self.gridLayout.setRowStretch(3, 2)

        self.gridLayout.addWidget(QLabel("测量结果"), 0, 0)
        self.result_canvas = ResultCanvas(self, width=6, height=4, dpi=100)
        self.gridLayout.addWidget(self.result_canvas, 1, 0)

        self.gridLayout.addWidget(QLabel("输出"), 0, 1)
        self.textBrowser = QTextBrowser()
        self.gridLayout.addWidget(self.textBrowser, 1, 1)

        self.gridLayout.addWidget(QLabel("示波器输出"), 2, 1)
        self.Lightsignal = QWidget()
        lightsignal_layout = QVBoxLayout(self.Lightsignal)
        self.oscilloscope_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        lightsignal_layout.addWidget(self.oscilloscope_canvas)
        self.gridLayout.addWidget(self.Lightsignal, 3, 1)

        self.gridLayout.addWidget(QLabel("数据表格"), 2, 0)
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(6)
        headers = ["磁场", "本底测量值", "磁场", "非极化离子测量值", "磁场", "极化离子测量值"]
        self.tableWidget.setHorizontalHeaderLabels(headers)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.gridLayout.addWidget(self.tableWidget, 3, 0)

        main_layout.addLayout(self.gridLayout)
        self.resize(1248, 1000)

    def prepare_measurement(self):
        if self.bfield_array is None:
            self.textBrowser.append("请先通过 [定义磁场表] 按钮导入磁场表。")
            QMessageBox.warning(self, "提示", "请先定义磁场表，再准备测量。")
            return

        if self.prepare_thread and self.prepare_thread.isRunning():
            return
        self.textBrowser.append("准备测量中：设置电压 70 V，10 s 内电流 ramp 到目标值 …")
        self.prepare_thread = PrepareThread(self)
        self.prepare_thread.ramp_finished.connect(self.on_ramp_finished)
        self.prepare_thread.error_occurred.connect(self.textBrowser.append)
        self.prepare_thread.start()

    def redefine_bfield(self):
        new_bfield = self.get_bfield_array()
        if new_bfield is not None and len(new_bfield) > 0:
            self.bfield_array = new_bfield
            self.textBrowser.append(f"已成功导入磁场表，共 {len(self.bfield_array)} 个点。")
            self.update_bfield_status()
        else:
            self.textBrowser.append("定义磁场表已取消或导入了空表，操作未完成。")

    def update_bfield_status(self):
        if self.bfield_array is None:
            self.textBrowser.append("磁场表：未定义")
        else:
            self.textBrowser.append(
                f"磁场表：{len(self.bfield_array)} 点 [{self.bfield_array[0]:.1f}~{self.bfield_array[-1]:.1f} Gs]")

    def get_bfield_array(self):
        if self.ask_bfield_array():
            return self.bfield_array
        return None

    def ask_bfield_array(self) -> bool:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("定义磁场表")
        layout = QVBoxLayout(dlg)

        btn_manual = QPushButton("手工输入磁场值")
        btn_file = QPushButton("从 txt 文件导入")
        layout.addWidget(btn_manual)
        layout.addWidget(btn_file)

        def manual():
            text, ok = QtWidgets.QInputDialog.getMultiLineText(
                self, "手工输入",
                "每行一个磁场值(Gs)，可用逗号/空格分隔：\n例：518 520 630")
            if ok and text.strip():
                try:
                    arr = np.array([float(x) for x in re.findall(r"[+-]?\d+(?:\.\d+)?", text)])
                    if arr.size == 0:
                        raise ValueError
                    self.bfield_array = arr
                    dlg.accept()
                except Exception:
                    QMessageBox.warning(self, "错误", "解析失败，请检查格式！")

        def load_file():
            path, _ = QFileDialog.getOpenFileName(self, "选取磁场表 txt", "", "TXT (*.txt)")
            if path:
                try:
                    raw = np.loadtxt(path, comments='#', ndmin=2)
                    arr = raw[:, 1] if raw.shape[1] >= 2 else raw.ravel()
                    if arr.size == 0:
                        raise ValueError
                    self.bfield_array = arr
                    dlg.accept()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"读取失败：{e}")

        btn_manual.clicked.connect(manual)
        btn_file.clicked.connect(load_file)
        return dlg.exec_() == QtWidgets.QDialog.Accepted

    def on_stop_finished(self):
        self.stop_requested = False
        self.textBrowser.append("已安全下电，可重新准备测量。")

    def stop_measurement(self):
        self.stop_requested = True
        if self.acquisition_thread and self.acquisition_thread.isRunning():
            self.acquisition_thread.stop_requested = True
            self.textBrowser.append("正在停止当前测量...")
        else:
            self.textBrowser.append("没有正在进行的测量")

    def stop_current(self):
        """停止测量：中断采集 -> 电流 ramp 到 0 -> 电压设 0"""
        # 1. 立旗，让采集线程尽快退出
        self.stop_requested = True

        # 2. 禁用按钮，防止重复点击
        self.textBrowser.append("正在安全下电：电流 ramp → 0 A，电压 → 0 V …")

        # 3. 启动停止线程
        self.stop_thread = StopRampThread(self)
        self.stop_thread.finished.connect(self.on_stop_finished)
        self.stop_thread.start()

    def on_ramp_finished(self, success):
        if success:
            self.textBrowser.append("准备完成，可以开始测量！")
        else:
            self.textBrowser.append("准备失败，请检查电源！")

    def update_oscilloscope_display(self):
        if self.last_photon_data is None or self.last_BField_data is None:
            return

        self.oscilloscope_canvas.axes.clear()
        ax = self.oscilloscope_canvas.axes

        total_time = 1.2E-3
        if self.cb_osc_channel.currentIndex() == 0:
            data = self.last_photon_data
            ax.set_title(" CHAN2 (photon)")
        else:
            data = self.last_BField_data
            ax.set_title(" CHAN3 (B-Field)")

        time = np.linspace(0, total_time, len(data)) * 1000
        ax.plot(time, data)
        ax.set_xlabel('Time (ms)')
        ax.set_ylabel('Voltage (V)')
        ax.tick_params(axis='both', labelsize=7)
        self.oscilloscope_canvas.fig.tight_layout()
        self.oscilloscope_canvas.draw()

    def handle_oscilloscope_update(self, data_photon, data_BField):
        self.last_photon_data = data_photon
        self.last_BField_data = data_BField
        self.update_oscilloscope_display()

    def handle_scatter_update(self, x, y, data_type):
        self.result_canvas.add_scatter_point(x, y, data_type)

    def measure_background(self):
        self._start_acquisition("本底", "background", lambda data: setattr(self, 'background_data', data))

    def measure_unpolarized(self):
        self._start_acquisition("非极化离子", "unpolarized", lambda data: setattr(self, 'unpolarized_data', data))

    def measure_polarized(self):
        self._start_acquisition("极化离子", "polarized", lambda data: setattr(self, 'polarized_data', data), True)

    def _start_acquisition(self, name, data_type, data_setter, calculate_polarization=False):
        if self.acquisition_thread and self.acquisition_thread.isRunning():
            self.textBrowser.append(f"正在进行{name}测量，请等待完成...")
            return

        # 关键：每次测量前都检查磁场表是否已定义
        if self.bfield_array is None or len(self.bfield_array) == 0:
            QMessageBox.critical(
                self, "磁场表未设置",
                "请先点击「定义磁场表」按钮来设置磁场配置，然后再进行测量。"
            )
            return

        particle_type = self.cb_particle.currentText()
        gain_factor = float(self.gain_input.text())
        self.textBrowser.append(f"开始测量{name}... (粒子类型: {particle_type})")

        self.acquisition_thread = DataAcquisitionThread(
            data_type, particle_type, gain_factor, self.bfield_array, self,
            last_current=self.last_current
        )
        self.acquisition_thread.update_scatter_signal.connect(self.handle_scatter_update)
        self.acquisition_thread.update_oscilloscope_signal.connect(self.handle_oscilloscope_update)
        self.acquisition_thread.acquisition_finished.connect(
            lambda data: self._on_acquisition_finished(data, name, data_setter, calculate_polarization))
        self.acquisition_thread.error_occurred.connect(self.textBrowser.append)

        self.acquisition_thread.start()

    def _on_acquisition_finished(self, data, name, data_setter, calculate_polarization):
        self.stop_requested = False
        if data is not None:
            data_setter(data)
            self.textBrowser.append(f"{name}测量完成。")  # 明确提示电流未归零
            self._update_table()
            if calculate_polarization:
                self.calculate_and_plot_polarization()

    def clear_data(self):
        self.background_data = None
        self.unpolarized_data = None
        self.polarized_data = None
        self.last_photon_data = None
        self.last_BField_data = None

        self.result_canvas.clear()
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(0)
        self.oscilloscope_canvas.axes.clear()
        self.oscilloscope_canvas.draw()
        self.textBrowser.append("测量数据已清除，磁场表仍保留。")

    def load_results(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "读取测量结果", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if not file_path:
            return

        try:
            self.clear_data()
            self.textBrowser.append(f"正在从 {os.path.basename(file_path)} 读取数据...")

            with open(file_path, 'r', newline='') as csvfile:
                reader = list(csv.reader(csvfile))

            particle_type_line = reader[2]
            if len(particle_type_line) > 1 and particle_type_line[0] == "粒子类型:":
                particle_type = particle_type_line[1].strip()
                if particle_type in ["H", "D"]:
                    self.cb_particle.setCurrentText(particle_type)
                    self.textBrowser.append(f"成功读取粒子类型: {particle_type}")
                else:
                    self.textBrowser.append(f"警告: 未知的粒子类型 '{particle_type}'")
            else:
                raise ValueError("CSV文件格式错误: 无法在第3行找到粒子类型。")

            data_rows = reader[9:]
            background = []
            unpolarized = []
            polarized = []

            for row in data_rows:
                if row[0] and row[1]:
                    background.append([float(row[0]), float(row[1])])
                if row[2] and row[3]:
                    unpolarized.append([float(row[2]), float(row[3])])
                if row[4] and row[5]:
                    polarized.append([float(row[4]), float(row[5])])

            if background:
                self.background_data = np.array(background)
            if unpolarized:
                self.unpolarized_data = np.array(unpolarized)
            if polarized:
                self.polarized_data = np.array(polarized)

            self._update_table()
            self.calculate_and_plot_polarization()
            self.textBrowser.append("数据加载并显示完成。")

        except Exception as e:
            error_msg = f"读取文件失败: {e}"
            self.textBrowser.append(error_msg)
            QMessageBox.critical(self, "读取错误", error_msg)

    def save_results(self):
        if self.background_data is None and self.unpolarized_data is None and self.polarized_data is None:
            QMessageBox.warning(self, "警告", "没有可保存的测量数据！")
            return

        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"polarization_results_{current_time}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存测量结果", default_filename, "CSV文件 (*.csv);;所有文件 (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                writer.writerow(["极化率测量结果"])
                writer.writerow(["测量时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(["粒子类型:", self.cb_particle.currentText()])
                writer.writerow([])

                writer.writerow(["极化率计算结果:"])
                if self.background_data is not None and self.polarized_data is not None:
                    if self.cb_particle.currentText() == 'H':
                        polarization = calculate_polarization(self.polarized_data, self.background_data, 'proton')
                        writer.writerow(["质子极化率 Pz:", f"{polarization['polarization']:.3f}"])
                    else:
                        polarization = calculate_polarization(self.polarized_data, self.background_data, 'deuteron')
                        writer.writerow(["氘极化率 Pz:", f"{polarization['P_z']:.3f}", "氘极化率 Pzz:",
                                         f"{polarization['P_zz']:.3f}"])
                writer.writerow([])

                writer.writerow(["表格数据:"])
                headers = ["磁场", "本底测量值", "磁场", "非极化离子测量值", "磁场", "极化离子测量值"]
                writer.writerow(headers)

                max_rows = max(
                    len(self.background_data) if self.background_data is not None else 0,
                    len(self.unpolarized_data) if self.unpolarized_data is not None else 0,
                    len(self.polarized_data) if self.polarized_data is not None else 0
                )

                for row in range(max_rows):
                    row_data = []
                    if self.background_data is not None and row < len(self.background_data):
                        row_data.extend([f"{self.background_data[row, 0]:.4f}", f"{self.background_data[row, 1]:.6e}"])
                    else:
                        row_data.extend(["", ""])

                    if self.unpolarized_data is not None and row < len(self.unpolarized_data):
                        row_data.extend(
                            [f"{self.unpolarized_data[row, 0]:.4f}", f"{self.unpolarized_data[row, 1]:.6e}"])
                    else:
                        row_data.extend(["", ""])

                    if self.polarized_data is not None and row < len(self.polarized_data):
                        row_data.extend([f"{self.polarized_data[row, 0]:.4f}", f"{self.polarized_data[row, 1]:.6e}"])
                    else:
                        row_data.extend(["", ""])

                    writer.writerow(row_data)

            self.textBrowser.append(f"测量结果已保存至: {file_path}")

            fig_path = os.path.splitext(file_path)[0] + "_plot.png"
            params = {'font.family': 'serif',
                      'font.serif': 'Times New Roman',
                      'font.style': 'normal',
                      'font.weight': 'normal',
                      'font.size': 12,
                      'lines.linewidth': 1,
                      'text.usetex': False
                      }
            plt.rcParams.update(params)
            original_size = self.result_canvas.fig.get_size_inches()
            self.result_canvas.fig.set_size_inches(6, 4)
            self.result_canvas.fig.savefig(fig_path, dpi=300, bbox_inches='tight')
            self.result_canvas.fig.set_size_inches(original_size)
            self.textBrowser.append(f"测量图表已保存至: {fig_path}")

        except Exception as e:
            self.textBrowser.append(f"保存失败: {str(e)}")
            QMessageBox.critical(self, "保存错误", f"无法保存文件: {str(e)}")

    def _update_table_rows(self, required_rows):
        current_rows = self.tableWidget.rowCount()
        if required_rows > current_rows:
            self.tableWidget.setRowCount(required_rows)
            for i in range(current_rows, required_rows):
                self.tableWidget.setVerticalHeaderItem(i, QTableWidgetItem(f"Row {i + 1}"))

    def _update_table(self):
        max_rows = 0
        if self.background_data is not None:
            max_rows = max(max_rows, len(self.background_data))
        if self.unpolarized_data is not None:
            max_rows = max(max_rows, len(self.unpolarized_data))
        if self.polarized_data is not None:
            max_rows = max(max_rows, len(self.polarized_data))

        if max_rows == 0:
            return

        self._update_table_rows(max_rows)

        if self.background_data is not None:
            for row, (bfield, value) in enumerate(self.background_data):
                item_b = QTableWidgetItem(f"{bfield:.4f}")
                item_b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tableWidget.setItem(row, 0, item_b)

                item_v = QTableWidgetItem(f"{value:.6e}")
                item_v.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tableWidget.setItem(row, 1, item_v)

        if self.unpolarized_data is not None:
            for row, (bfield, value) in enumerate(self.unpolarized_data):
                item_b = QTableWidgetItem(f"{bfield:.4f}")
                item_b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tableWidget.setItem(row, 2, item_b)

                item_v = QTableWidgetItem(f"{value:.6e}")
                item_v.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tableWidget.setItem(row, 3, item_v)

        if self.polarized_data is not None:
            for row, (bfield, value) in enumerate(self.polarized_data):
                item_b = QTableWidgetItem(f"{bfield:.4f}")
                item_b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tableWidget.setItem(row, 4, item_b)

                item_v = QTableWidgetItem(f"{value:.6e}")
                item_v.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tableWidget.setItem(row, 5, item_v)

    def calculate_and_plot_polarization(self):
        if self.background_data is None or self.polarized_data is None:
            self.textBrowser.append("请先完成本底和极化离子测量。")
            return

        self.result_canvas.axes.clear()
        ax = self.result_canvas.axes

        particle_type = self.cb_particle.currentText()

        if particle_type == 'H':
            polarization = calculate_polarization(self.polarized_data, self.background_data, 'proton')
            self.textBrowser.append(f"Nbp: {polarization['peak_background'][1][0]:.3e}")
            self.textBrowser.append(f"Nbn: {polarization['peak_background'][1][1]:.3e}")
            self.textBrowser.append(f"Np: {polarization['peak_signal'][1][0]:.3e}")
            self.textBrowser.append(f"Nn: {polarization['peak_signal'][1][1]:.3e}")
            self.textBrowser.append(f"质子极化率: {polarization['polarization']:.3f}")
            ax.plot(self.polarized_data[:, 0], self.polarized_data[:, 1], ".", label="WFT-ON", color='red')
            ax.plot(self.background_data[:, 0], self.background_data[:, 1], "*", label="background", color='blue')
            ax.text(0.5, 0.85, f"Pz = {polarization['polarization']:.3f}",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=9, fontweight='bold')
            ax.set_title("Polarization of Proton", fontsize=18)

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("测量结果")
            msg_box.setText(f"<html><body><h2 style='color:blue;'>质子束极化率</h2>"
                            f"<p style='font-size:40px;'>"
                            f"<span style='color:red; font-weight:bold;'>{polarization['polarization']:.2%}</span>"
                            f"</p></body></html>")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f0f8ff;
                    border: 2px solid #4682b4;
                    min-width: 450px;
                    min-height: 250px;
                    font-size: 20pt;
                }
                QMessageBox QLabel {
                    font-size: 16pt;
                    color: #333333;
                    padding: 10px;
                }
                QPushButton {
                    font-size: 14pt;
                    padding: 8px 20px;
                    background-color: #4682b4;
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #5a9bd3;
                }
            """)
            msg_box.exec_()

        elif particle_type == 'D':
            polarization = calculate_polarization(self.polarized_data, self.background_data, 'deuteron')
            self.textBrowser.append(f"Nbp: {polarization['peak_background'][1][0]:.3e}")
            self.textBrowser.append(f"Nb0: {polarization['peak_background'][1][1]:.3e}")
            self.textBrowser.append(f"Nbn: {polarization['peak_background'][1][2]:.3e}")
            self.textBrowser.append(f"Np: {polarization['peak_signal'][1][0]:.3e}")
            self.textBrowser.append(f"N0: {polarization['peak_signal'][1][1]:.3e}")
            self.textBrowser.append(f"Nn: {polarization['peak_signal'][1][2]:.3e}")
            self.textBrowser.append(f"氘极化率 Pz: {polarization['P_z']:.3f}, Pzz: {polarization['P_zz']:.3f}")
            ax.plot(self.unpolarized_data[:, 0], self.unpolarized_data[:, 1], "x", label="WFT-OFF", color='green')
            ax.plot(self.polarized_data[:, 0], self.polarized_data[:, 1], ".", label="WFT-ON", color='red')
            ax.plot(self.background_data[:, 0], self.background_data[:, 1], "*", label="background", color='blue')
            ax.text(0.3, 0.85, f'Pz = {polarization["P_z"]:.3f}',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=9, fontweight='bold')
            ax.text(0.3, 0.65, f'Pzz = {polarization["P_zz"]:.3f}',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=9, fontweight='bold')
            ax.set_title("Polarization of Deuteron", fontsize=18)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("测量结果")
            msg_box.setText(f"<html><body><h2 style='color:blue;'>氘离子束极化率</h2>"
                            f"<p style='font-size:40px;'>"
                            f"<span style='color:red; font-weight:bold;'>{polarization['P_z'] / 0.66666:.2%}</span>"
                            f"</p></body></html>")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet("""
                            QMessageBox {
                                background-color: #f0f8ff;
                                border: 2px solid #4682b4;
                                min-width: 450px;
                                min-height: 250px;
                                font-size: 20pt;
                            }
                            QMessageBox QLabel {
                                font-size: 16pt;
                                color: #333333;
                                padding: 10px;
                            }
                            QPushButton {
                                font-size: 14pt;
                                padding: 8px 20px;
                                background-color: #4682b4;
                                color: white;
                                border-radius: 5px;
                            }
                            QPushButton:hover {
                                background-color: #5a9bd3;
                            }
                        """)
            msg_box.exec_()

        ax.set_xlabel('Magnetic Field (Gs)', fontsize=15)
        ax.set_ylabel('PMT Anode Signal (A. U.)', fontsize=15)
        ax.tick_params(axis='both', labelsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        self.result_canvas.update_legend()
        self.result_canvas.fig.tight_layout()
        self.result_canvas.draw()


class PrepareThread(QThread):
    ramp_finished = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        try:
            ptnhp = PTNhpController(ip="192.168.1.123", port=7, timeout=5, terminator='\n')
            if not ptnhp.connect():
                self.error_occurred.emit("PTNhp 电源连接失败")
                self.ramp_finished.emit(False)
                return

            if not ptnhp.set_voltage(70):
                self.error_occurred.emit("设置 70 V 失败")
                self.ramp_finished.emit(False)
                return
            ptnhp.start_output()
            time.sleep(0.1)

            I_now = ptnhp.measure_current()
            self.error_occurred.emit(f"当前电流: {I_now:.3f} A")

            if 9 < I_now < 11:
                self.error_occurred.emit(f"当前电流已接近目标值：10 A，可以测量")
                self.parent.last_current = I_now  # 保存当前电流
                self.ramp_finished.emit(True)
                return

            steps = self.parent.ramp_steps
            I_start = I_now
            I_end = 1 # 目标电流10A
            for i in range(steps + 1):
                I = I_start + (I_end - I_start) * i / steps
                if not ptnhp.set_current(I):
                    self.error_occurred.emit(f"第 {i} 步设置电流 {I:.3f} A 失败")
                    self.ramp_finished.emit(False)
                    return
                self.msleep(100)

            self.parent.last_current = I_end  # 保存最终电流
            self.ramp_finished.emit(True)
        except Exception as e:
            self.error_occurred.emit(f"PrepareThread 异常：{e}")
            self.ramp_finished.emit(False)


class StopRampThread(QThread):
    finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        try:
            ptnhp = PTNhpController(ip="192.168.1.123", port=7, timeout=5, terminator='\n')
            if not ptnhp.connect():
                self.parent.textBrowser.append("StopRamp：电源连接失败")
                return

            time.sleep(0.1)
            steps = 100
            I_now = ptnhp.measure_current()
            for i in range(steps + 1):
                I = I_now * (1 - i / steps)
                ptnhp.set_current(I)
                self.msleep(100)

            ptnhp.set_voltage(0)
            self.parent.last_current = 0.0  # 重置电流记录
        except Exception as e:
            self.parent.textBrowser.append(f"StopRamp 异常：{e}")
        finally:
            self.finished.emit()

