import numpy as np

b1 = np.linspace(518, 548, 5)
b2 = np.linspace(548, 590, 42)
b3 = np.linspace(590, 618, 5)
bfield = np.concatenate((b1, b2[1:-1], b3))
bfields = np.concatenate((bfield , bfield[::-1], bfield , bfield[::-1], bfield , bfield[::-1]))
np.savetxt('custom_bfields.txt', bfields, fmt='%.2f')