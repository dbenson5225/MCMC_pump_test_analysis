import numpy as np
STCPK_guess    = np.array([ 0.3,    200,  -45,  4.5,  -1.9])
lower_bound    = np.array([1.e-3,     1.,  -60,  1.0,  -10.])
upper_bound    = np.array([  0.5,  2000.,    0,  5.0,    5.])