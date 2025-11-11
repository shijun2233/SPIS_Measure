from PyQt5.QtCore import QThread, pyqtSignal
from .instrument import InstrumentCommunicator
from .data_processor import DataProcessor
import numpy as np


class AcquisitionThread(QThread):
    """流强数据采集线程"""
    data_acquired = pyqtSignal(int, np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    finished = pyqtSignal()

    # 新增ip_address和channel参数
    def __init__(self, time_scal, gain, count=0, ip_address=None, channel=None):
        super().__init__()
        self.time_scal = time_scal
        self.gain = gain
        self.count = count
        self.ip_address = ip_address  # 存储IP地址
        self.channel = channel  # 存储通道信息
        self.running = False
        # 将参数传递给仪器通信器
        self.instrument = InstrumentCommunicator(
            ip_address=ip_address,
            channel=channel
        )
    
    def run(self):
        self.running = True
        run_number = 1
        
        try:
            while self.running and (self.count == 0 or run_number <= self.count):
                # 采集数据
                off_data, on_data = self.instrument.acquire_beam_data(
                    self.time_scal, self.gain
                )
                beam_data = on_data - off_data
                rows = len(beam_data)
                time_data = np.arange(rows) * 12 * self.time_scal / rows * 1e6
                
                if time_data.size > 0:
                    self.data_acquired.emit(run_number, time_data, off_data, on_data, beam_data)
                
                run_number += 1
                self.msleep(200)  # 短暂休眠
        
        finally:
            self.instrument.disconnect()
            self.finished.emit()
    
    def stop(self):
        self.running = False
        self.wait()


class PolarizationAcquisitionThread(QThread):
    """极化率数据采集线程"""
    data_acquired = pyqtSignal(int, np.ndarray, np.ndarray, float)
    finished = pyqtSignal()
    
    def __init__(self, time_scal, gain, count=0, analyzing_power=0.3):
        super().__init__()
        self.time_scal = time_scal
        self.gain = gain
        self.count = count
        self.analyzing_power = analyzing_power
        self.running = False
    
    def run(self):
        self.running = True
        run_number = 1
        
        try:
            while self.running and (self.count == 0 or run_number <= self.count):
                # 生成或采集极化率数据
                up_data, down_data = InstrumentCommunicator.generate_polarization_data()
                polarization = DataProcessor.calculate_polarization(
                    up_data, down_data, self.analyzing_power
                )
                
                if up_data.size > 0 and down_data.size > 0:
                    self.data_acquired.emit(run_number, up_data, down_data, polarization)
                
                run_number += 1
                self.msleep(200)
        
        finally:
            self.finished.emit()
    
    def stop(self):
        self.running = False
        self.wait()