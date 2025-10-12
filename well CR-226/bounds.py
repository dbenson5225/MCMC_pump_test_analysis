import numpy as np
STCPK_guess    = np.array([ 0.1,    200,  -14,  3.0,  -2.35])
lower_bound    = np.array([1.e-3,     1.,  -60,  1.0,  -10.])
upper_bound    = np.array([  0.5,  2000.,    0,  5.0,    5.])