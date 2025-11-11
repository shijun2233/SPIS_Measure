import numpy as np
from scipy import integrate

class DataProcessor:
    """数据处理工具类，提供各类数据计算方法"""
    
    @staticmethod
    def moving_average(data, window_size):
        """计算移动平均值"""
        weights = np.repeat(1.0, window_size) / window_size
        return np.convolve(data, weights, 'valid')
    
    @staticmethod
    def calculate_averages(data):
        """计算两个区间的平均值"""
        data1 = data[len(data) // 6:int(len(data) / 4)]
        data2 = data[len(data) // 6:int(len(data) / 3.25)]
        return np.average(data1), np.average(data2)

    @staticmethod
    def calculate_sigma(data):
        """计算数据的样本标准差"""
        if len(data) < 2:
            return 0.0  # 数据量不足时返回0，避免除以0错误
        # 使用numpy计算样本标准差（ddof=1表示自由度为n-1）
        return np.std(data, ddof=1)
    
    @staticmethod
    def calculate_integral(data, total_time=1200):
        """计算积分值"""
        dt = total_time / len(data)  # 时间间隔（μs）
        integral = dt * integrate.trapz(data)  # 积分结果
        integral_s = integral * 1e-6  # 转换为秒单位
        integral_per_pulse = integral / 150  # 每脉冲积分
        return integral_s, integral_per_pulse


    def calculate_particle_count(current, time):
        """
        根据电流和时间数据计算粒子数量（假设每个粒子带1C电量）

        参数:
        current: 电流数据，单位为mA（毫安）
        time: 时间数据，单位为us（微秒）

        返回:
        particle_count: 粒子数量
        total_charge: 总电荷量（库仑）
        """
        # 转换为numpy数组以便处理
        current = np.asarray(current)
        time = np.asarray(time)

        # 检查输入数据长度是否一致
        if len(current) != len(time):
            raise ValueError("电流和时间数据的长度必须相同")

        # 检查时间是否按顺序排列
        if not np.all(np.diff(time) >= 0):
            raise ValueError("时间数据必须按升序排列")

        # 计算时间间隔（微秒转换为秒：1微秒 = 1e-6秒）
        dt = np.diff(time) * 1e-6  # 转换为秒

        # 电流转换为安培（1毫安 = 0.001安培）
        current_amp = current * 0.001  # 转换为安培

        # 使用梯形法则计算积分（电荷 = 电流 × 时间）
        total_charge = np.sum((current_amp[:-1] + current_amp[1:]) / 2 * dt)

        # 计算粒子数量（每个粒子带1C电量）
        particle_count = total_charge  / 1.6e-19 # 因为1e/粒子，所以数量等于总电荷量/1.9e19

        return particle_count

    def calculate_peak_and_fwhm(x, y):
        """
        计算单峰数据的最大值（峰值）和半高全宽（FWHM）

        参数:
        x: 横坐标数据（数组或列表）
        y: 纵坐标数据（数组或列表）

        返回:
        peak_value: 峰值（最大值）
        peak_position: 峰值所在的横坐标位置
        fwhm: 半高全宽
        """
        # 转换为numpy数组以便处理
        x = np.asarray(x)
        y = np.asarray(y)

        # 检查输入数据长度是否一致
        if len(x) != len(y):
            raise ValueError("x和y的长度必须相同")

        # 找到峰值（最大值）及其位置
        peak_index = np.argmax(y)
        peak_value = y[peak_index]

        # 计算半高值
        half_max = peak_value / 2

        # 找到峰值左侧第一个小于等于半高值的点
        left_indices = np.where(y[:peak_index] <= half_max)[0]
        if len(left_indices) == 0:
            left_position = x[0]  # 如果所有左侧点都高于半高，取第一个点
        else:
            # 取最靠近峰值的那个点
            left_idx = left_indices[-1]
            # 线性插值以获得更精确的半高点
            if left_idx < peak_index - 1:
                # 找到刚好高于半高的点
                above_left_idx = left_idx + 1
                # 线性插值计算精确的半高位置
                left_position = x[above_left_idx] - (y[above_left_idx] - half_max) * \
                                (x[above_left_idx] - x[left_idx]) / (y[above_left_idx] - y[left_idx])
            else:
                left_position = x[left_idx]

        # 找到峰值右侧第一个小于等于半高值的点
        right_indices = np.where(y[peak_index:] <= half_max)[0] + peak_index
        if len(right_indices) == 0:
            right_position = x[-1]  # 如果所有右侧点都高于半高，取最后一个点
        else:
            # 取最靠近峰值的那个点
            right_idx = right_indices[0]
            # 线性插值以获得更精确的半高点
            if right_idx > peak_index:
                # 找到刚好高于半高的点
                above_right_idx = right_idx - 1
                # 线性插值计算精确的半高位置
                right_position = x[above_right_idx] + (half_max - y[above_right_idx]) * \
                                 (x[right_idx] - x[above_right_idx]) / (y[right_idx] - y[above_right_idx])
            else:
                right_position = x[right_idx]

        # 计算半高全宽
        fwhm = right_position - left_position

        return peak_value, fwhm