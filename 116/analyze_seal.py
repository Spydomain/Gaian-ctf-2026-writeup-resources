#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timedelta,timezone
import json
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
x=np.genfromtxt(ROOT/'calibrated_env.csv',delimiter=',',names=True)
t=x['ms']/1000;T=x['temperature_C'];P=x['pressure_hPa'];RH=x['humidity_pct']
# Water vapour mixing fraction removes RH's dependence on temperature.
water_hPa=(RH/100)*6.112*np.exp(17.62*T/(243.12+T))
water_ppm=water_hPa/P*1e6
c=np.genfromtxt(ROOT/'cl3_0419_co2.csv',delimiter=',',names=True)
ct=c['ms']/1000

# Fit the late pressure transition. Avoid the periodic radio heating bursts.
# While sealed, pressure is linear in absolute gas temperature. When open,
# pressure relaxes towards chamber pressure. The change time is continuous.
sel=(t>=6150)&(t<=6500);tt=t[sel];temp=T[sel];pp=P[sel]

def model(v):
    q,offset,ambient,slope,onset,tau=v
    sealed=q*(temp+273.15)+offset
    chamber=ambient+slope*(tt-6300)
    fraction=np.exp(-np.maximum(tt-onset,0)/tau)
    return chamber+(sealed-chamber)*fraction
bounds=([3,-100,995,-.01,6295,1],[4,100,1020,.01,6310,100])
fit=least_squares(lambda v:model(v)-pp,[3.444,0,1006.95,0,6303.2,20],bounds=bounds,
                  x_scale='jac',ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=10000)
v=fit.x;res=model(v)-pp;noise=np.sqrt(np.sum(res**2)/(len(res)-len(v)))
cov=np.linalg.pinv(fit.jac.T@fit.jac)*noise**2
onset_se=np.sqrt(cov[4,4]);onset=v[4]
rec=int(x['rec'][np.flatnonzero(t>onset)[0]])
start=datetime(2041,3,18,8,12,4,tzinfo=timezone.utc)
print('Pressure-model parameters:',dict(zip(['sealed_P_per_K','sealed_offset_hPa','chamber_hPa','chamber_drift_hPa_s','onset_s','tau_s'],v.tolist())))
print(f'Pressure residual RMS {noise:.6f} hPa; onset standard error {onset_se:.6f} s')
print(f'Opening estimate {onset:.6f}s = {(start+timedelta(seconds=float(onset))).isoformat()}')
print('Last sample before opening:',int(x['rec'][rec-1]),t[rec-1])
print('First sample after opening:',rec,t[rec])
assert t[rec-1]<onset<t[rec]
# Check whether alternate first-record intervals can explain the transition.
for proposed in [rec-1,rec,rec+1]:
    lo=t[proposed-1]+1e-6;hi=t[proposed]-1e-6
    lower=np.array(bounds[0],float);upper=np.array(bounds[1],float)
    lower[4]=lo;upper[4]=hi
    initial=v.copy();initial[4]=np.clip(v[4],lo+1e-7,hi-1e-7)
    alt=least_squares(lambda a:model(a)-pp,initial,bounds=(lower,upper),x_scale='jac',max_nfev=10000)
    print('Constrained first record',proposed,'SSE',float(np.sum(alt.fun**2)),'opening',alt.x[4])

fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True)
axs[0].plot(tt,pp,'.',markersize=2,label='Calibrated pressure');axs[0].plot(tt,model(v),label='Pressure transition fit');axs[0].set_ylabel('Pressure (hPa)');axs[0].legend()
zoom=(t>=6150)&(t<=6500)
axs[1].plot(t[zoom],water_ppm[zoom],'.',markersize=2);axs[1].set_ylabel('Water vapour (ppm)')
cz=(ct>=6150)&(ct<=6500);axs[2].plot(ct[cz],c['co2_ppm'][cz],'.-');axs[2].set_ylabel('CO2 sensor (ppm)');axs[2].set_xlabel('Seconds after logger start')
for ax in axs:ax.axvline(onset,color='r',ls='--');ax.grid(alpha=.25)
fig.tight_layout();fig.savefig(ROOT/'seal_opening.png',dpi=160)

flag=f'GAIANSPACE{{{rec}}}'
result={'flag':flag,'opening_seconds_estimate':float(onset),'onset_standard_error_seconds':float(onset_se),
        'first_record_after_opening':rec,'sample_seconds':float(t[rec]),
        'utc_sample':(start+timedelta(seconds=float(t[rec]))).isoformat(),
        'pressure_residual_rms_hPa':float(noise)}
(ROOT/'seal_result.json').write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'flag.txt').write_text(flag+'\n')
print(flag)
