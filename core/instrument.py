from RsInstrument import *
import numpy as np
from .data_processor import DataProcessor

class InstrumentCommunicator:
    """仪器通信类，负责与测量设备交互"""
    
    def __init__(self, ip_address="192.168.1.100", channel=1):
        self.ip_address = ip_address
        self.channel = channel  # 新增：通道属性
        self.instrument = None
    
    def connect(self):
        """连接到仪器"""
        try:
            self.instrument = RsInstrument(
                f'TCPIP::{self.ip_address}::INSTR', True, False
            )
            return True
        except Exception as e:
            print(f"仪器连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开与仪器的连接"""
        if self.instrument:
            self.instrument.close()
            self.instrument = None
    
    def acquire_beam_data(self, time_scal, gain, samples=2):
        """采集束流数据（使用指定通道）"""
        if not self.instrument:
            if not self.connect():
                return np.array([]), np.array([])
        
        try:
            beam_data = []
            for _ in range(samples):
                self.instrument.write_str_with_opc("SINGle", 50000)
                self.instrument.write_str("FORMat:DATA REAL,32")
                self.instrument.bin_float_numbers_format = BinFloatFormat.Single_4bytes_swapped
                self.instrument.data_chunk_size = 100000
                # 修改：使用指定通道获取数据
                raw_data = self.instrument.query_bin_or_ascii_float_list(f"CHAN{self.channel}:DATA?")
                smoothed = DataProcessor.moving_average(np.array(raw_data), 200)
                beam_data.append(smoothed)
            
            # 转换为物理单位（mA）
            off_data = np.array(beam_data[0]).reshape(-1, 1) / gain * 1e3
            on_data = np.array(beam_data[1]).reshape(-1, 1) / gain * 1e3
            
            # 确保数据顺序正确（OFF <= ON）
            if np.average(off_data) > np.average(on_data):
                off_data, on_data = on_data, off_data
            
            return off_data.flatten(), on_data.flatten()
        
        except Exception as e:
            print(f"数据采集失败: {e}")
            return np.array([]), np.array([])
