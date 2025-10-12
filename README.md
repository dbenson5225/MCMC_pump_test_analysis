# MCMC_pump_test_analysis (work in progress)
Python-based MCMC analysis of step-drawdown pumping test parameters and operational costs

This repository contains Python-based codes to perform Markov-chain Monte Carlo (MCMC) analysis of step-drawdown pumping tests.  The codes are easily modified to do any sort of variable-rate or constant-rate pumping tests.  The codes use an off-the-shelf MCMC sampler called emcee (https://emcee.readthedocs.io). You will need to have already intalled Python 3.X, and you will have to install the emcee package using standard methods (i.e. type "pip install emcee" at the command line or use conda).  To speed up various parts of this process, we also invoke parallel processing using the package multiprocessing, and save the MCMC chain on-the-fly using the h5 protocol (so install these two packages as well). To summarize, we use the following packages, so have them installed before running:
- numpy
- scipy
- matplotlib
- time
- os
- multiprocessing
- h5py

If you prefer to have an entire environment file, I provide a yaml file.

The two Python codes are contained in the scripts "step_test_mcmc_GR.py" and "step_test_mcmc.py". The former may be used to run several shorter independent chains and uses a Gelman-Rubin statistic on each parameter to help ensure convergence of the posterior.  The latter is a single chain that is most useful for final production runs. Both of these codes need to access two user-created files, in the user's current working directory, called "well_data.txt" and "bounds.py", which looks like the following.  On each line of "well_data.txt" there is a data value followed by a comment for readability. Only the first thing matters. In this file you also specify the names of the drawdown and well discharge time series:

    True        # optimize flag
    True        # minimize flag
    True        # MCMC flag
    True        # prediction flag
    False        # IES flag
    226_dd.txt  # Drawdown file with columns of time, drawdown
    226_Q.txt   # Well discahrge file with olumns of start time for Q_i, then Q_i for i pumping rates
    0.5         # Well radius (ft)
    241         # screened interval length (ft)
    1086        # Depth to static water (ft)
    1720        # Total well (i.e., discharge pipe) depth 
    0.417       # Piping diameter (ft)
    0.7         # Pump efficiency (NOT well efficiency) 
    120         # Hazen-Williams friction for piping
    0.3         # porosity of gravel pack
    3.0         # duration of a single pumping episode (for prediction)
    4000        # total pump hours per year (for prediction)
    0.1         # electricity cost in dollars per kW (for prediction)

    
The first time through, you should have the first 4 flags set to True - this will perform 1) classical Levenberg-Marquardt optimization, then 2) a minimization of your specified -log-likelihood function, then 3) the MCMC "optimization" based on the starting neighborhood defined by the minimization(s). Each step saves a file of the results, so you may turn to False if good results were gotten and you want to save time. The IES flag does nothing at the present time.
The next two lines are names of files that contain the time/drawdown data, and the variable pumping rates (all in consistent units, i.e. feet, days, cubic feet per day).  The next 8 lines define the well parameters, and the last 3 define a pumping scenario for predicitive runs.
In the file "bounds.py", you specify three vectors that contain values of [S, T, ln(C), p, ln(k)], the first line is an initial guess, the second is a lower bound and the third is an upper bound:

    import numpy as np
    STCPK_guess    = np.array([ 0.1,    200,  -14,  3.0,  -2.35])
    lower_bound    = np.array([1.e-3,     1.,  -60,  1.0,  -10.])
    upper_bound    = np.array([  0.5,  2000.,    0,  5.0,    5.])

Within the Python codes are a few lines that the user might want to modify.  These all reside in the __main__ part of the program.  Specifically, one may change the "normalized" pumping rate for predictions, which for the purposes of the published paper was 1 GPM per vertical foot of screen:

    norm_pump_rate = 1.0*2*3.14*r*screen_intvl*por*1440/7.48   # 1 gpm per ft^2 of screen converted to ft^3/day

Also, the amount of noise (the std dev) in each observed data point is considered a function of the observation $\sigma(o_i) = k f(o_i)$. The user specifies the function and the program "figures out" the magnitude k of the noise. Two choices of $f(o_i)$ are shown here with one commented out.  

    obs_err = np.where(obs_dd<1,1,obs_dd)   # error *proportional* to measured drawdown  
    #obs_err = np.ones_like(obs_dd)

Once the user has created (or copied from these repositories) the well_data.txt, bounds.py, and drawdown and pumping rate files, then simply type "python step_test_mcmc_GR.py" or "python step_test_mcmc.py" at the command line.  The optimized, minimized, and MCMC "parameters" will be displayed on the screen as well as written to disk.  The entire MCMC chain is written to disk in an h5 file, which can be extremely big.  But if the chain is successful, you may turn the MCMC flag in "well_data.txt" to False and never need to run the MCMC again.  Any future scenarios that you would like to test can just read the h5 file from disk.  
