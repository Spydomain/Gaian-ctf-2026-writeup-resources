#!/usr/bin/env python3
"""Fit a topocentric short-arc orbit and rank the Cerro Tololo tracklets.

Requires scipy, numpy, spiceypy and astropy. The DE440s kernel and MPC site
parallax constants are cached in ``reference/``; their URLs are in the writeup.
"""
import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import spiceypy as spice
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from astropy.coordinates import EarthLocation
from astropy.time import Time
from astropy import units as u
from astropy.utils import iers

warnings.filterwarnings('ignore')
iers.conf.auto_download = False
ROOT = Path(__file__).parent
REF = ROOT / 'reference'
spice.furnsh(str(REF / 'naif0012.tls'))
spice.furnsh(str(REF / 'de440s.bsp'))
AU = 149597870.7  # km
MU_SUN = 0.0002959122082855911  # AU^3 / day^2
MU_EARTH = 8.887692587e-10
C = 173.144632674240  # AU/day


def unit(ra, dec):
    return np.array([np.cos(dec)*np.cos(ra), np.cos(dec)*np.sin(ra), np.sin(dec)])


def tangent(ra, dec):
    return np.array([-np.sin(ra), np.cos(ra), 0.0]), np.array([
        -np.sin(dec)*np.cos(ra), -np.sin(dec)*np.sin(ra), np.cos(dec)])


def parse_mpc():
    rows = []
    for line in (ROOT / '2041QM23.obs').read_text().splitlines():
        date = line[15:32].strip().split()
        day = float(date[2]); whole = int(day)
        stamp = pd.Timestamp(f'{date[0]}-{date[1]}-{whole:02}') + pd.Timedelta(days=day-whole)
        h,m,s = map(float,line[32:44].split())
        d,am,asec = line[44:56].split(); sign = -1 if d[0]=='-' else 1
        rows.append((stamp, np.deg2rad(15*(h+m/60+s/3600)),
                     np.deg2rad(sign*(abs(int(d))+float(am)/60+float(asec)/3600)),
                     line[77:80]))
    return rows


sites = json.loads((REF / 'observatories.json').read_text())
def station_j2000(stamp, code):
    info = sites[code]
    lon = np.deg2rad(float(info['longitude']))
    east = 6378.137 * float(info['rhocosphi'])
    xyz = [east*np.cos(lon), east*np.sin(lon), 6378.137*float(info['rhosinphi'])]
    site = EarthLocation.from_geocentric(*xyz, unit=u.km)
    return site.get_gcrs(Time(stamp.to_pydatetime(), scale='utc')).cartesian.xyz.to_value(u.km) / AU


observations = parse_mpc()
# Start before the first shutter so the light-time correction never asks the
# propagator for a state before its initial epoch.
T0 = observations[0][0] - pd.Timedelta(hours=2)
ET0 = spice.str2et(T0.strftime('%Y-%m-%dT%H:%M:%S.%f'))
def days(stamp): return (stamp-T0).total_seconds()/86400
def earth(t):
    state,_ = spice.spkezr('399', ET0+t*86400, 'J2000','NONE','10')
    return np.r_[np.array(state[:3])/AU, np.array(state[3:])*86400/AU]

obs_days=np.array([days(row[0]) for row in observations])
obs_earth=np.array([earth(t)[:3] for t in obs_days])
obs_site=np.array([station_j2000(row[0],row[3]) for row in observations])
obs_ra=np.array([row[1] for row in observations]);obs_dec=np.array([row[2] for row in observations])
tracklets=pd.read_csv(ROOT/'recovery_tracklets.csv')
recovery_stamps=[pd.Timestamp(tracklets.iloc[0][key]) for key in ('t1_utc','t2_utc')]
recovery_days=np.array([days(stamp) for stamp in recovery_stamps])
recovery_earth=np.array([earth(t)[:3] for t in recovery_days])
recovery_site=np.array([station_j2000(stamp,'807') for stamp in recovery_stamps])


def orbit(params, final):
    dra,ddec,mra,mdec,rho,rhodot=params
    ra=obs_ra[0]+dra;dec=obs_dec[0]+ddec
    east,north=tangent(ra,dec)
    start_earth=earth(0)
    r=start_earth[:3]+rho*unit(ra,dec)
    v=start_earth[3:]+rhodot*unit(ra,dec)+rho*(mra*east+mdec*north)
    def derivative(t,y):
        pos=y[:3];epos=earth(t)[:3];gap=pos-epos
        acc=-MU_SUN*pos/np.linalg.norm(pos)**3-MU_EARTH*gap/np.linalg.norm(gap)**3
        return np.r_[y[3:],acc]
    sol=solve_ivp(derivative,(0,final),np.r_[r,v],rtol=3e-10,atol=1e-12,dense_output=True,max_step=.4)
    if not sol.success: raise RuntimeError(sol.message)
    return sol


def angles(sol,times,epos,site):
    # One iteration suffices for the retarded astrometric light time.
    p=sol.sol(times)[:3].T
    delay=np.linalg.norm(p-epos-site,axis=1)/C
    p=sol.sol(np.maximum(0,times-delay))[:3].T
    q=p-epos-site
    return np.arctan2(q[:,1],q[:,0])%(2*np.pi), np.arctan2(q[:,2],np.linalg.norm(q[:,:2],axis=1))


def residual(params):
    try:
        sol=orbit(params,obs_days.max()+.01)
        ra,dec=angles(sol,obs_days,obs_earth,obs_site)
        # 703's unsynchronised clock: exclude it from the orbit fit.
        good=np.array([row[3]!='703' for row in observations])
        return np.r_[((ra-obs_ra)*np.cos(obs_dec))[good],(dec-obs_dec)[good]]*206265
    except Exception:
        return np.full(24,1e6)


if __name__=='__main__':
    results=[]
    for rho in (.02,.05,.10,.20,.40):
        guess=np.array([0.,0.,np.deg2rad(-1.1),np.deg2rad(-.35),rho,.003])
        fit=least_squares(residual,guess,x_scale=[.01,.01,.02,.02,.1,.01],
                          max_nfev=150,ftol=1e-10,xtol=1e-10,gtol=1e-10)
        results.append((np.linalg.norm(fit.fun),fit.x))
        print('start range',rho,'fit arcsec',np.linalg.norm(fit.fun),'range',fit.x[-2:])
    error,params=min(results,key=lambda item:item[0])
    sol=orbit(params,recovery_days.max()+.01)
    ra,dec=angles(sol,recovery_days,recovery_earth,recovery_site)
    print('predicted Cerro Tololo positions:',list(zip(np.rad2deg(ra),np.rad2deg(dec))))
    residuals=[]
    for _,row in tracklets.iterrows():
        d=np.array([(row.ra1_deg-np.rad2deg(ra[0]))*np.cos(dec[0]),row.dec1_deg-np.rad2deg(dec[0]),
                    (row.ra2_deg-np.rad2deg(ra[1]))*np.cos(dec[1]),row.dec2_deg-np.rad2deg(dec[1])])
        residuals.append((np.linalg.norm(d)*3600,row.tracklet))
    for distance,name in sorted(residuals)[:10]:print(name,round(distance,2),'arcsec combined')
    best=min(residuals)[1]
    print('best',best)
    print(f'GAIANSPACE{{{best}}}')
