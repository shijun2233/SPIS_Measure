import numpy as np



b1 = np.linspace(518, 548, 10)
b2 = np.linspace(548, 590, 180)
b3 = np.linspace(590, 618, 10)
bfields = np.concatenate((b1, b2, b3))
np.savetxt('custom_bfields.txt', bfields, fmt='%.2f')