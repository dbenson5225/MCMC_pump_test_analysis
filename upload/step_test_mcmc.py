#!/usr/bin/env python3
# This will make the optimization slower, but speed up MCMC somewhat:
import os
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import emcee

#matplotlib.use('Qt5agg')

#######  First define the functions to calculate 

def fun_pump(params,Q,Q_at_data,tvec,ds_dt_at_data):
    S=params[0]
    T=params[1]
    C=np.exp(params[2])
    p=params[3]
    #print('p = ' +str(p))
    Q_corrector=1.0  # 1 for on, 0 for off.
    dt=tvec[2]-tvec[1]
    green=(np.exp(-(r*r*S/4./T/tvec)))/tvec
    green[0]=0.0
    lwant=len(tvec)
    ltot=len(green)+len(Q)
    #print('number of convolution points = '+str(ltot)+'  working on it ...')
    z=np.zeros(ltot-lwant)   # Zero padding
    # This is the calculated Theis drawdown:
    s1=np.fft.irfft( np.fft.rfft(np.append(green,z))*np.fft.rfft(np.append(Q,z)) )
    s1=dt*s1[0:len(tvec)]
    s1_at_data=(1/(4*np.pi*T)) * np.interp(obs_time,tvec,s1)  # Theissian solution interp at data points
    Q_corr=np.maximum(np.zeros_like(Q_at_data), np.sign(Q_at_data) * (Q_at_data - Q_corrector*np.pi*r*r*ds_dt_at_data))
    model_dd = s1_at_data + C*np.sign(Q_at_data)*Q_corr**p;   # Add the nonlinear losses
    efficiency=s1_at_data/model_dd

    # Plot the progress of the optimization.  Remove for better speed.
    # ax1.cla()
    # ax1.plot(obs_time,model_dd,'r-')
    # ax1.plot(obs_time,s1_at_data,'b-')
    # ax1.plot(obs_time,obs_dd,'o',markersize=3, fillstyle = 'none')
    # plt.legend(["full model", "Theis portion","data"], loc ="upper left")
    # plt.pause(0.01)
    return model_dd, efficiency

def resid(params):

    global tvec
    tvec=make_tvec((params[0]),params[1],max(obs_time))
    Q=makeQ_of_t()   
#    ds_dt_at_data=make_ds_dt(tvec)
    model_dd,efficiency=fun_pump(params,Q,Q_at_data,tvec,ds_dt_at_data)
    ################## Set the weights here ##################
    #weights=np.ones_like(obs_dd)
    #weights=1.0/obs_dd
    weights=1/obs_err
    resid=weights*(model_dd - obs_dd)
    print('Classical RMSE = '+str(np.sqrt(np.mean(model_dd - obs_dd)**2)) + 
          ' Weighted RMSE = '+str(np.sqrt(np.mean((weights*(model_dd - obs_dd))**2))), end='\r' )
    return resid

def makeQ_of_t():
    # tvec and Q_data must be global
    Q=np.zeros_like(tvec)
    for k in range(0,len(Q_data[:,0])):
        Qnow=Q_data[k,1]
        tnow=Q_data[k,0]
        Q[tvec>tnow]=Qnow
    return Q

def make_Q_at_data():
    # Q_data and obs_time must be global 
    Q_at_data=np.zeros_like(obs_time)
    for k in range(0,len(Q_data[:,0])):
        Qnow=Q_data[k,1]
        tnow=Q_data[k,0]
        Q_at_data[obs_time>tnow]=Qnow
    return Q_at_data

def make_ds_dt():
    ds_dt_at_data=obs_dd.copy()
    ds_dt_at_data[1:-1]=(obs_dd[1:-1] - obs_dd[0:-2])/(obs_time[1:-1]-obs_time[0:-2])
    ds_dt_at_data[0]=(obs_dd[1] - obs_dd[0])/(obs_time[1]-obs_time[0])
    return ds_dt_at_data

def make_tvec(S,T,tmax):
    extrat=1.2
    tmin=0.0
        # This may need to be adjusted based on Green's function:
    tpeak=r*r*S/4.0/T
    dt=tpeak/4.0 # Divisor is points between zero and peak of Green's fn. Check fig 3 for a decent peak!
    ntpoints = 1+int(np.ceil((extrat*tmax-tmin)/dt))
    tvec=np.linspace(tmin,extrat*tmax,ntpoints)
    tvec[0]=1e-30
    return tvec

# emcee package functions ----------------------------------------------------

def run_model(params):
    S,T = params[0:2]
    global tvec
    tvec = make_tvec(S, T,max(obs_time))
    Q = makeQ_of_t()

    model_dd,efficiency = fun_pump(params,Q,Q_at_data,tvec,ds_dt_at_data)
    ################## Set the weights here ##################
    weights=1/obs_err  # Stad dev, not VAR
    #weights=np.ones_like(obs_dd)
    #weights=1.0/obs_dd
    resid=weights*(model_dd - obs_dd)
    return model_dd, resid

def log_likelihood(params):
    dd_params=params[0:4]
    log_K_mag=params[-1]
    model_dd, resid = run_model(dd_params)
    #l_hood = -0.5 * np.sum(((model_dd - obs_dd)/obs_err)**2)
    n=len(model_dd)
    sigma2 = (np.exp(log_K_mag)*obs_err)**2 
    l_hood = -0.5 * (n*np.log(2*np.pi) + np.sum( (model_dd - obs_dd) ** 2 / sigma2 + np.log(sigma2) ) )
    
    return l_hood

def log_prior(params):
    S, T, C, p, log_K_mag = params
    #lower = np.array([1.e-2, 1.e-6, np.log(1.e-40), 1, np.log(1.e-10)  ])
    #upper = np.array([0.5, 1000., np.log(1.), 5, np.log(10000)])
    lS,lT,lC,lp,lK = lower_bound
    uS,uT,uC,up,uK = upper_bound
    if lS < S < uS and lT < T < uT and lC < C < uC and lp < p < up and lK < log_K_mag < uK:
        return 0.0
    else:
        return -np.inf

def log_probability(params):

    lp = log_prior(params)
    if not np.isfinite(lp):
        return -np.inf
    return lp + log_likelihood(params)

#def run_mcmc(p0, nwalkers, niter, ndim, log_probability):
#    sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability, args=data)
#    print("Running burn-in...")
#    p0, _, _ = sampler.run_mcmc(p0, 100, progress=True)
#    sampler.reset()

#    print("Running production...")
#    pos, prob, state = sampler.run_mcmc(p0, niter, progress=True)
    #tau = sampler.get_autocorr_time()
    #print(tau)
    #time.sleep(5)
#    return sampler, pos, prob, state

def plotter(sampler,x,y, Q_data):
    plt.ion()
    #plt.plot(x,y,label='Drawdown (ft)')
    samples = sampler.flatchain
    for theta in samples[np.random.randint(len(samples), size=200)]:
        y_model, resid = run_model(theta, x, y, Q_data)
        plt.plot(x, y_model, color="r", alpha=0.1)

    plt.plot(x,y,label="Observed Data")
    plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
    plt.xlabel('Time (d)')
    plt.ylabel(r'Drawdown (ft)')
    plt.legend()
    plt.show()

def sample_walkers(nsamples, flattened_chain):
    models = []
    draw = np.floor(np.random.uniform(0,len(flattened_chain),size=nsamples)).astype(int)
    thetas = flattened_chain[draw]
    for i in thetas:
        dd_params=i[0:-1]
        mod, res = run_model(dd_params)
        models.append(mod)
    spread = np.std(models,axis=0)
    med_model = np.median(models,axis=0)
    return med_model,spread

def energy_calc(d_total_well,d_to_water,model_dd,pipe_D,Pump_E,efficiency,Hazen,Q_predict):
    h_f = (4.73*d_total_well*(Q_predict/(86400*Hazen))**1.85)/(pipe_D**4.87)
    TDH = d_to_water + model_dd + h_f
    TDH_Theis = d_to_water + efficiency*model_dd + h_f
    kW =(0.001/Pump_E)*(Q_predict/86400)*TDH*(3.3**(-4))*9810.0
    kW_Theis =(0.001/Pump_E)*(Q_predict/86400)*TDH_Theis*(1/3.3**4)*9810.0
    return kW, kW_Theis

#########  Main Program - user inputs required in this section ###############

if __name__ == "__main__":

#   Open up the required file that contains workflow booleans, drawdown and Q filenames,
#   and a list of data pertaining to the well:
    f=open('well_data.txt','r')
    store_data=[]
    while 1:
        a=f.readline()
        if a=='': break
        store_data.append(a.split()[0])
    f.close()

    # Extract the workflow booleans (True/False)
    to_bool = [item.lower().capitalize() == "True" for item in store_data[0:5]]
    optimize,minimize,mcmc,predict_E,ies=to_bool

    # Extract the filenames for drawdow data and Q data:
    obs_filename=store_data[5]
    Q_filename=store_data[6]
    
    # Extract the various real-valued well and operation parameters:
    to_real = [eval(item) for item in store_data[7:]]
    [r,screen_intvl,d_to_water,d_total_well,pipe_D,Pump_E,Hazen,
                       por,pump_duration,pump_hr_year,elec_cost]=to_real


##  Reminder of input data names used by many functions
# r              : Well radius (ft)
# screen_intvl   : screened interval length (ft)
# d_to_water     : Depth to static water (ft)
# d_total_well   : Total well (i.e., discharge pipe) depth 
# pipe_D         : Piping diameter (ft)
# Pump_E         : Pump efficiency (NOT well efficiency) 
# Hazen          : Hazen-Williams friction for piping
# por            : porosity of gravel pack
# pump_duration  : duration of a single pumping episode for predition
# pump_hr_year   : total pump hours per year
# elec_cost      : dollars per kW
 

    norm_pump_rate = 1.0*2*3.14*r*screen_intvl*por*1440/7.48   # 1 gpm per ft^2 of screen converted to ft^3/day
    print('prediction pump rate :',norm_pump_rate)

    # Initial guess and bounds of parameters [S, T, ln(C), p, ln(k)]:
    params         = np.array([ 0.24,    179,  -31,  3.1,  1.0]) 
    lower_bound    = np.array([1.e-3,     1.,  -60,  1.0,  -10.])
    upper_bound    = np.array([  0.5,  2000.,    0,  5.0,    5.])

###################### Done with user inputs - now make some calcs of global variables #############
#  The user may want to change some of these calcs, e.g. functional form of obs error

    obs_data = np.loadtxt(obs_filename)
    Q_data = np.loadtxt(Q_filename)
    obs_time = obs_data[:,0]
    obs_dd = obs_data[:,1]
#    The user *might* want to change this:
    obs_err = np.where(obs_dd<1,1,obs_dd)   # error *proportional* to measured drawdown  
#    obs_err = np.ones_like(obs_dd)    # errors constant
#  Now perform the guts of the program 
    if optimize:
        print('--------------------------------------------------------------------------')
        print('Running classical ML optimization of parameters ...')

        from scipy.optimize import least_squares
        start_time = time.process_time()
 
        # Define starting value of parameters, and lower and upper bounds
        # Parameters: S (storativity or specific yield), T (transmissivity), C & p (constants?)

        ST=params[0:4]

        #  Run some functions once for data that is needed
        ds_dt_at_data = make_ds_dt()
        Q_at_data = make_Q_at_data()
 
        #ST = np.array([0.01, 300, np.log(1e-12) , 2.])          # Initial guess
        lower = lower_bound[0:-1]
        upper = upper_bound[0:-1]
 
#        lower = np.array([1.e-3, 1.e-6, np.log(1.e-80), 1.])    # Lower bound
#       upper = np.array([0.5, 2000., np.log(1.), 5.])          # Upper bound

        # Do the nonlinear least squares

        #res_lsq=least_squares(resid,ST,tr_solver='lsmr',loss='soft_l1',args=(obs_dd,Q,tvec,r,obs_time))
        res_lsq = least_squares(resid,ST,bounds=(lower, upper),args=())

        # Calculate some approx statistics of the optimization:
        final_params=res_lsq.x

        # Save final optimized parameters, simulated drawdown, and residuals
        np.savetxt('final_params.txt', final_params)

        X=res_lsq.jac
        residuals=res_lsq.fun
        degrees_freedom = X.shape[0]-X.shape[1]
        COV=(np.abs(np.sum(residuals))/(degrees_freedom))*(np.linalg.inv(X.transpose()@X ))
        sd=np.sqrt(np.diag(COV))
        np.savetxt('COV.txt',COV)
        np.savetxt('SD.txt',sd)
        
        print(' ')
        print('Covariance matrix:')
        print(COV)
        print(' ')
        print('Linear standard dev. est.:')
        print(sd)
        print(' ')
        print('Correlation matrix:')
        print(COV/(np.outer(sd,sd)))
        print(' ')
        print('Final Parameters                 (saving to "final_params.txt") ')
        print('[    S,          T,          log(C),           p    ]')
        print(final_params)

        #  Get the final modeled drawdown and plot against data

        final_dd, final_res = run_model(final_params)

        np.savetxt('final_dd.txt', final_dd)
        np.savetxt('final_residual.txt', final_res)

        elapsed_time = time.process_time()-start_time

        print('Execution time (h:m:s):', time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))

        #  Make some decent plots.

        tplotmin=0.9*min(obs_time)
        tplotmax=1.1*max(obs_time)
        splotmin=0.9*min(obs_dd)
        splotmax=1.1*max(obs_dd)

        fig3, ax3 = plt.subplots(figsize=(5,5))
        ax3.loglog(obs_time,final_dd,'r-',label="model")
        ax3.loglog(obs_time,obs_dd,'o',markersize=5, fillstyle = 'none', label="data")
        ax3.set_xlim(tplotmin,tplotmax)
        ax3.set_ylim(splotmin,splotmax)
        ax3.set_xlabel("Time (d)")
        ax3.set_ylabel("Drawdown (ft)")
        ax3.legend(loc ="upper left")

        fig4, ax4 = plt.subplots(figsize=(5,5))
        ax4.plot(obs_time,final_dd,'r-',label="model")
        ax4.plot(obs_time,obs_dd,'o',markersize=3, fillstyle = 'none', label="data")
        ax4.set_xlim(tplotmin,tplotmax)
        ax4.set_ylim(splotmin,splotmax)
        ax4.set_xlabel("Time (d)")
        ax4.set_ylabel("Drawdown (ft)")
        ax4.legend()

        #fig5, ax5 = plt.subplots(figsize=(5,5))
        #ax5.plot(obs_time,np.pi*r*r*ds_dt_at_data,label="pi*r^2*ds/dt")
        #ax5.plot(tvec,Q,label="Q")
        #ax5.plot(obs_time,Q_at_data-np.pi*r*r*ds_dt_at_data,label="corrected Q")
        #ax5.plot(obs_time,200.0*obs_dd,'o',label="200*dd")
        #ax5.legend()
        plt.show(block=False)


#  Use this to estimate the magnitude of the error function based on prior estimates of [S,T,C,p]
#  It does not do a good job estimating all the (nonlinear) bits
    if minimize:
        print('--------------------------------------------------------------------------')
        print('Running minimization including error magnitude using log likelihood fn ...')
        from scipy.optimize import minimize

        initial = np.loadtxt('final_params.txt') # read in params estimated by nonlinear LS
        initial = np.append(initial,params[-1])      # put in initial guess of ln(K_mag)

        #  Run some functions once for data that is needed
        ds_dt_at_data = make_ds_dt()
        Q_at_data = make_Q_at_data()
 
        #obs_data = np.loadtxt(obs_filename)
        #obs_time = obs_data[:, 0]
        #obs_dd = obs_data[:, 1]
        #Q_data = np.loadtxt(Q_filename)
 
        # Drawdown observation error
        # Make a guess of the functional form - the magnitude K_mag will be estimated
        #obs_err = 0 + np.sqrt(np.abs(obs_dd)) * 0.1   # Variance propto drawdown
        #obs_err = 0 + np.abs(obs_dd) * 1.0            # Std. proto drawdown
       
        # First guess of parmaeters [S, T, log(C), p, log(k)]
        bnds = ((lower_bound[0], upper_bound[0]), (lower_bound[1], upper_bound[1]), 
                (lower_bound[2], upper_bound[2]), (lower_bound[3], upper_bound[3]), 
                (lower_bound[4], upper_bound[4])) 
 
        nll = lambda *args: -log_likelihood(*args)
        soln = minimize( nll, initial, args=(), bounds=bnds )
        #nll = lambda *args: -log_likelihood(*args)
        #soln = minimize( nll, initial, args=(obs_time, obs_dd, obs_err, Q_data, r), bounds=bnds )
        final_params=soln.x
        print('')
        print('Final Parameters                 (saving to "final_params_min.txt") ')
        print('[    S,          T,          log(C),           p,        log(k)  ]')
        print(final_params)
        np.savetxt('final_params_min.txt', final_params)

    if mcmc:
        import multiprocessing
        multiprocessing.set_start_method("fork")

        from multiprocessing import Pool
        from multiprocessing import cpu_count

        print('--------------------------------------------------------------------------')
        print('Setting up MCMC after optimization/minimization ...')
        #ncpu = cpu_count()
        print('This should run on',cpu_count(),' cores')

        # Set up the backend
        # Don't forget to clear it in case the file already exists
        mcmc_filename = "mcmc_save.h5"
        backend = emcee.backends.HDFBackend(mcmc_filename)
 
        # Read in optimized parameters and observed data
        final_params = np.loadtxt('final_params_min.txt')

        data = (obs_time, obs_dd, obs_err, Q_data, r)  # Q_data, r, obs_err, lower, upper)
        nwalkers = 10                       # number of walkers
        niter = 10000                        # number of steps in the chain
        initial = final_params.copy()
        ndim = len(initial)
        backend.reset(nwalkers, ndim)

        #initial=np.append(initial,[-3.5])      # put in initial guess of ln(K_mag)

        # make some needed vectors once
        ds_dt_at_data = make_ds_dt()
        Q_at_data = make_Q_at_data()
 
        # spread the walkers over about 1 percent the mean optimal parameters:
        p0 = [np.array(initial) + 1e-2 * np.abs(initial) * np.random.randn(ndim) for i in range(nwalkers)]

        with Pool() as pool:

            sampler = emcee.EnsembleSampler(nwalkers,ndim,log_probability,backend=backend,pool=pool)
        #sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability)
            print("Running burn-in...")
            p0, _, _ = sampler.run_mcmc(p0, 100, progress=True)
        
            sampler.reset()

            print("Running production...")
            pos, prob, state = sampler.run_mcmc(p0, niter, progress=True)
        
        tau = sampler.get_autocorr_time(tol=0)
        print(' ')
        print('Autocorrelation times tau = ',tau)
        print('Mean autocorrelation time = ',np.mean(tau)) 
        print('Should run for approx.',int(100*np.mean(tau)))

        #sampler, pos, prob, state = run_mcmc(p0,nwalkers,niter,ndim,log_probability,data)

        #plotter(sampler,obs_time,obs_dd, Q_data)
        samples = sampler.flatchain
        new_theta_max = samples[np.argmax(sampler.flatlnprobability)]
        new_best_fit_model, new_res = run_model(new_theta_max[0:-1])
        med_model, spread = sample_walkers(50,samples)

        import corner

        labels = ["S", "T", "ln(C)", "p", "ln(k_mag)"]
        fig = corner.corner(samples, labels=labels ,truths=[initial[0], initial[1], initial[2], initial[3], initial[4]]);
        plt.savefig('corner.pdf')

        plt.figure(figsize=(12, 6))
        plt.subplot(1,2,1)
        plt.plot(obs_time,obs_dd, ".k", label='Observed Drawdown')
        plt.plot(obs_time,new_best_fit_model,label='Highest Likelihood Model')
        plt.fill_between(obs_time,med_model-2*spread,med_model+2*spread,color='grey',alpha=0.5,label=r'$2\sigma$ Posterior Spread')
        plt.legend()
        plt.ylabel('Drawdown (ft)')
        plt.xlabel('Time (d)')

        plt.subplot(1,2,2)
        plt.semilogy(obs_time,obs_dd, ".k", label='Observed Drawdown')
        plt.semilogy(obs_time,new_best_fit_model,label='Highest Likelihood Model')
        plt.fill_between(obs_time,med_model-2*spread,med_model+2*spread,color='grey',alpha=0.5,label=r'$2\sigma$ Posterior Spread')
        plt.legend()
        plt.ylabel('Drawdown (ft)')
        plt.xlabel('Time (d)')

        plt.savefig('model_spread.pdf')
        plt.show()

    if predict_E:
        print('--------------------------------------------------------------------------')
        print('Setting up MC predictions ...')
        # Now that a sample chain is saved to disk (even if you just ran one!), read it
        # and make some predictions.  This allows one to turn off the MCMC if it's already
        # been done.
        mcmc_filename = "mcmc_save.h5"
 #      backend = emcee.backends.HDFBackend(mcmc_filename)
 
        reader = emcee.backends.HDFBackend(mcmc_filename)

        tau = reader.get_autocorr_time()
        burnin = int(1* np.max(tau))
        thin = int(1 * np.min(tau))
        flat_samples = reader.get_chain(discard=burnin, flat=True, thin=thin)
        print('Tau is still: ',tau)
        #log_prob_samples = reader.get_log_prob(discard=burnin, flat=True, thin=thin)
        #log_prior_samples = reader.get_blobs(discard=burnin, flat=True, thin=thin)

        tau_max=np.max(tau)
            
        # For speed, overwrite Q_data, obs_time, obs_dd and call functions normally
            
        Q_data=np.array([[0.0, norm_pump_rate]])
        obs_time=np.logspace(np.log10(.001),np.log10(pump_duration),40)
        obs_dd = np.ones_like(obs_time)
            
            # Make some functions once based on size of new observation (prediction) times
        ds_dt_at_data = np.zeros_like(obs_dd)
        Q_at_data = make_Q_at_data()
 
        #flat_samples = sampler.get_chain(discard=int(np.mean(tau)), thin=int(tau_max/2), flat=True)
        print('flat samples shape: ',flat_samples.shape)
        n_samp=400
        Eff_save=np.zeros(n_samp)
        kW_save=np.zeros(n_samp)
        kW_Theis_save=np.zeros(n_samp)

        inds = np.random.randint(len(flat_samples), size=n_samp)
        print('Running this many forward models: ',inds.shape)
        n_ind = 0
        # Note to reader: This loop could be parallelized if it takes too long
        for ind in inds:
            sample_now = flat_samples[ind]
            S,T,C,p = sample_now[0:4]
            tvec = make_tvec(S, T, max(obs_time))
            Q = makeQ_of_t()
            model_dd,efficiency = fun_pump(sample_now[0:4],Q,Q_at_data,tvec,ds_dt_at_data)
            energy_kW,energy_kW_Theis = energy_calc(d_total_well,d_to_water,model_dd[-1],pipe_D,Pump_E,efficiency[-1],Hazen,Q_at_data[-1])

            Eff_save[n_ind]=100*efficiency[-1]
            kW_save[n_ind]=energy_kW
            kW_Theis_save[n_ind]=energy_kW_Theis

            n_ind=n_ind+1
            plt.plot(obs_time, model_dd, "C1", alpha=0.05)
        plt.ylabel('Drawdown (ft)')
        plt.xlabel('Time (d)')
 
        dollars_NL=pump_hr_year*(kW_save-kW_Theis_save)*elec_cost # 4000 hours per year at $0.1/kWh
        dollars_total=pump_hr_year*elec_cost*kW_save
        dollars_Theis=pump_hr_year*elec_cost*kW_Theis_save
        # Get the expectation of dollars per cubic foot
        quants=[0.1, 0.5, 0.9]
        print('[0.1 0.5 0.9] quantiles of total cost per cubic foot :',np.quantile((dollars_total/(norm_pump_rate*pump_hr_year/24)),quants) )
        print('[0.1 0.5 0.9] quantiles of Theis cost per cubic foot :',np.quantile((dollars_Theis/(norm_pump_rate*pump_hr_year/24)),quants) )
        print('[0.1 0.5 0.9] qualtiles of nonlinear cost per cubic foot :',np.quantile((dollars_NL/(norm_pump_rate*pump_hr_year/24)),quants) )

        bins=np.linspace(50,100,26)
        #print(bins)
        plt.figure(figsize=(14, 4))

        plt.subplot(1,4,1)
        plt.hist(100*efficiency, bins, density=True)
        plt.xlabel('Well Efficiency (%)')
        plt.ylabel('pdf')
        plt.xlim(0, 100)
        plt.ylim(0, .5)
        plt.subplot(1,4,2)
        plt.hist(pump_hr_year*elec_cost*kW_save, density=True)
        plt.xlabel('Total Pumping Cost ($/yr)')
        plt.subplot(1,4,3)
        plt.hist(pump_hr_year*elec_cost*kW_Theis_save, density=True)
        plt.xlabel('Theis Pumping Cost ($/yr)')
        plt.subplot(1,4,4)
        plt.hist(dollars_NL, density=True)
        plt.xlabel('Nonlinear Drawdown Cost ($/yr)')

        plt.savefig('efficiency.svg')
        plt.show()

    if ies:
        # Sav to setup ies here
        print('Done!')