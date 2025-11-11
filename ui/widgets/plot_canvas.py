from PyQt5.QtWidgets import QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from core.data_processor import DataProcessor


class BasePlotCanvas(FigureCanvas):
    """基础图表画布"""
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.set_mpl_params()
        super().__init__(self.fig)
        self.setParent(parent)
    
    def set_mpl_params(self):
        """设置matplotlib参数"""
        plt.rcParams.update({'font.family': 'serif',
                  'font.serif': 'Times New Roman',
                  'font.style': 'normal',
                  'font.weight': 'normal',  # or 'blod'
                  'font.size': 9.3,  # or large,small
                  'lines.linewidth': 1,
                  'text.usetex': False,  # False    # True
                   'axes.grid': True,
                   'grid.linestyle': '--',
                   'grid.alpha': 0.7
                  })


        '''plt.rcParams.update({
            'font.family': ['SimHei',  'Times New Roman'],
            'font.size': 9,
            'lines.linewidth': 1,
            'axes.grid': True,
            'grid.linestyle': '--',
            'grid.alpha': 0.7
        })'''


class BeamHistoryPlot(BasePlotCanvas):
    """流强历史趋势图"""
    def __init__(self, parent=None):
        super().__init__(parent, width=8, height=4)
        self.ax = self.fig.add_subplot(111)
        self.run_data = []
    
    def update_plot(self):
        """更新图表"""
        self.ax.clear()
        if not self.run_data:
            self.ax.set_title("No Data")
            self.draw()
            return
        
        runs = [d['run'] for d in self.run_data]
        max_vals = [d['max'] for d in self.run_data]
        
        self.ax.plot(runs, max_vals, "ro", label="Beam Intensity")
        self.ax.set_xlabel("Run Time")
        self.ax.set_ylabel("Beam Intensity (mA)")
        self.ax.set_ylim(0, 1.5)
        self.ax.set_title("Beam Intensity history")
        self.ax.legend()
        self.fig.tight_layout()
        self.draw()
    
    def add_data(self, run, data):
        """添加新数据点"""
        avg1, avg2 = DataProcessor.calculate_averages(data)
        self.run_data.append({
            'run': run,
            'max': np.max(np.abs(data)),
            'avg1': np.abs(avg1),
            'avg2': np.abs(avg2)
        })
        self.run_data.append({
            'run': run,
            'max': np.max(np.abs(data)),
        })
        self.update_plot()



class BeamResultPlot(BasePlotCanvas):
    """流强结果详细图"""

    def __init__(self, parent=None):
        super().__init__(parent, width=8, height=5)
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()
        # 确保右侧y轴标签显示在右侧
        self.ax2.yaxis.set_label_position('right')
        self.ax2.yaxis.tick_right()


    def plot_data(self, time_data, off_data, on_data, beam_data):
        """绘制详细数据"""
        self.ax1.clear()
        self.ax2.clear()

        line1 = self.ax1.plot(time_data, off_data, 'b-', label='ABS-RF-OFF')
        line2 = self.ax1.plot(time_data, on_data, 'g-', label='ABS-RF-ON')

        line3 = self.ax2.plot(time_data, beam_data, 'r-', label='Ion Beam From ABS')

        lines = line1 + line2 + line3
        labels = [_.get_label() for _ in lines]

        # 设置右侧y轴颜色
        self.ax2.spines['right'].set_color('red')
        self.ax2.tick_params(axis='y', colors='red')

        # 确保右侧y轴标签位置和方向正确
        self.ax2.yaxis.set_label_position('right')
        self.ax2.yaxis.tick_right()

        self.ax1.legend(lines, labels, frameon=False, borderaxespad=0.2, borderpad=0.2, labelspacing=0.2)
        self.ax1.set_xlabel(r'Time (μs)')
        self.ax1.set_ylabel(r'Ion Beam (mA)')
        self.ax2.set_ylabel(r'Ion Beam from ABS (mA)', color='red')

        self.fig.tight_layout()
        self.draw()

        '''self.ax1.plot(time_data, off_data, 'b-', label='ABS-RF-OFF')
        self.ax1.plot(time_data, on_data, 'g-', label='ABS-RF-ON')
        self.ax2.plot(time_data, beam_data, 'r-', label='离子束流')
        self.ax2 = self.ax1.twinx()
        
        self.ax1.set_xlabel(r'Time ($\mu$s)')
        self.ax1.set_ylabel(r'Ion Beam (mA)')
        self.ax2.set_ylabel(r'Ion Beam from ABS (mA)', color='red')
        
        # 合并图例
        lines1, labels1 = self.ax1.get_legend_handles_labels()
        lines2, labels2 = self.ax2.get_legend_handles_labels()
        self.ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        self.ax1.grid(True)
        self.ax2.grid(True) 

        self.fig.tight_layout()
        self.draw()'''
