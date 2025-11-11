import socket
import time
import math
import re

class PTNhpController:
    """仪器控制类，封装了与仪器通信的常用功能"""

    def __init__(self, ip, port, timeout=5, terminator='\n'):
        """
        初始化仪器控制器

        参数:
            ip: 仪器IP地址
            port: 通信端口
            timeout: 超时时间(秒)
            terminator: 命令终止符(默认换行符，部分仪器可能需要\r\n)
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.terminator = terminator
        self.socket = None

    def connect(self):
        """建立与仪器的TCP连接"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip, self.port))
            print(f"已连接到仪器: {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"连接失败: {str(e)}")
            return False

    def close(self):
        """关闭与仪器的连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("连接已关闭")

    def _send_command(self, command):
        """内部方法：发送命令到仪器"""
        if not self.socket:
            print("未建立连接，请先调用connect()")
            return False

        try:
            # 拼接命令和终止符并发送
            full_command = command + self.terminator
            self.socket.sendall(full_command.encode())
            return True
        except Exception as e:
            print(f"命令发送失败: {str(e)}")
            return False

    def _receive_response(self, buffer_size=1024):
        """内部方法：接收仪器响应"""
        if not self.socket:
            print("未建立连接，请先调用connect()")
            return None

        try:
            response = self.socket.recv(buffer_size)
            if response:
                # 解码并去除首尾空白字符(包括终止符)
                return response.decode().strip()
            else:
                print("未收到响应数据")
                return None
        except Exception as e:
            print(f"接收响应失败: {str(e)}")
            return None

    def query_idn(self):
        """查询仪器标识(*IDN?)"""
        if self._send_command("*IDN?"):
            return self._receive_response()
        return None

    def start_output(self):
        """查询仪器标识(*IDN?)"""
        if self._send_command("OUTP ON"):
            return self._receive_response()
        return None

    def stop_output(self):
        """查询仪器标识(*IDN?)"""
        if self._send_command("OUTP OFF"):
            return self._receive_response()
        return None

    def set_voltage(self, value):
        """设置电压(VOLT命令)"""
        # 确保输入是数字
        try:
            value = float(value)
            return self._send_command(f"VOLT {value}")
        except ValueError:
            print("电压值必须是数字")
            return False

    def read_set_voltage(self, value):
        """读取设置电压(VOLT命令)"""
        if self._send_command("VOLT?"):
            response = self._receive_response()
            # 尝试将响应转换为浮点数
            try:
                return float(response) if response else None
            except ValueError:
                print(f"读取设置电压格式错误: {response}")
                return response

    def set_current(self, value):
        """设置电流(CURR命令)"""
        try:
            value = float(value)
            return self._send_command(f"CURR {value}")
        except ValueError:
            print("电流值必须是数字")
            return False

    def read_set_current(self, value):
        """读取设置电流(CURR命令)"""
        if self._send_command("CURR?"):
            response = self._receive_response()
            # 尝试将响应转换为浮点数
            try:
                return float(response) if response else None
            except ValueError:
                print(f"读取设置电流格式错误: {response}")
                return response

    def measure_voltage(self):
        """测量电压(MEAS:VOLT?)"""
        if self._send_command("MEAS:VOLT?"):
            response = self._receive_response()
            if response:
                m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', response)
                if m:
                    try:
                        return float(m.group(0))
                    except ValueError:
                        pass
                try:
                    return float(response)
                except ValueError:
                    return response
            return None
        return None

    def measure_current(self):
        """测量电流(MEAS:CURR?)"""
        if self._send_command("MEAS:CURR?"):
            response = self._receive_response()
            if response:
                m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', response)
                if m:
                    try:
                        return float(m.group(0))
                    except ValueError:
                        pass
                try:
                    return float(response)
                except ValueError:
                    return response
            return None
        return None



