import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # 设置中文字体支持
    import matplotlib
    matplotlib.use('Qt5Agg')
    import matplotlib.pyplot as plt
    params = {'font.family': 'serif',
                  'font.serif': 'Times New Roman',
                  'font.style': 'normal',
                  'font.weight': 'normal',  # or 'blod'
                  'font.size': 9.3,  # or large,small
                  'lines.linewidth': 1,
                  'text.usetex': False  # False    # True
                  }
    plt.rcParams.update(params)
    plt.grid = True
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")  # 使用Fusion风格，跨平台一致性更好
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 进入应用主循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()