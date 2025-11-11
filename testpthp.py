from core.ptnhp_con import PTNhpController
import math
import time

# 使用示例
if __name__ == "__main__":
    # 仪器参数设置(根据实际设备修改)
    INSTRUMENT_IP = "192.168.1.123"
    INSTRUMENT_PORT = 7
    TERMINATOR = '\n'  # 若设备需要回车换行，可改为'\r\n'

    # 创建控制器实例
    controller = PTNhpController(
        ip=INSTRUMENT_IP,
        port=INSTRUMENT_PORT,
        timeout=5,
        terminator=TERMINATOR
    )

    # 连接仪器并执行操作
    if controller.connect():


        controller.set_current(5.0)  # 2. 设定电流
        time.sleep(0.5)  # 4. 等待电源稳定

        volt = controller.measure_voltage()
        print("实测电压:", volt, "V")
        time.sleep(0.1)
        curr = controller.measure_current()
        print("实测电流:", curr, "A")




        # 关闭连接
        controller.close()