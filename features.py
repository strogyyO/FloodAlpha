"""Sensor features and causal temporal features shared by fitting and inference."""
from __future__ import annotations
import numpy as np
from scipy import ndimage

BANDS = ["B02", "B03", "B04", "B08", "B11", "B12"]
SPECTRAL_NAMES = BANDS + ["NDWI", "MNDWI", "NDVI", "NDBI", "AWEI_sh", "AWEI_nsh", "visible_mean", "nir_swir_mean", "green_swir_difference", "swir_ratio"]
TEMPORAL_NAMES = ["current_p", "previous_p", "daily_change", "normal_p", "history_water_frequency", "current_minus_normal", "local_mean_3", "local_mean_11", "distance_to_water_px", "distance_to_dry_px", "distance_to_normal_water_px", "lead_days", "previous_age_days", "annual_sin", "annual_cos"]


def safe_ratio(a, b):
    return np.divide(a,b,out=np.zeros_like(a,dtype="float32"),where=np.abs(b)>1e-5)


def spectral_features(cube):
    x=np.clip(np.asarray(cube,dtype="float32"),-.05,1.5)
    blue,green,red,nir,s1,s2=np.moveaxis(x,-1,0)
    extra=[safe_ratio(green-nir,green+nir),safe_ratio(green-s1,green+s1),
           safe_ratio(nir-red,nir+red),safe_ratio(s1-nir,s1+nir),
           blue+2.5*green-1.5*(nir+s1)-.25*s2,4*(green-s1)-(.25*nir+2.75*s2),
           (blue+green+red)/3,(nir+s1+s2)/3,green-s1,safe_ratio(s1,s2+.02)]
    return np.nan_to_num(np.concatenate([x,np.stack(extra,axis=-1)],axis=-1),nan=0,posinf=0,neginf=0).astype("float32")


def scene_valid(data, buffer=1):
    cube=np.stack([data[b] for b in BANDS],axis=-1)
    bad=np.isin(data["SCL"],[0,1,3,8,9,10,11])
    if buffer:bad=ndimage.binary_dilation(bad,iterations=buffer)
    return ~bad & np.isfinite(cube).all(axis=-1) & (cube.min(axis=-1)>-.05) & (cube.max(axis=-1)<1.5)


def temporal_features(current, previous, normal, frequency, valid, lead_days, age_days, day_of_year):
    """No future observations or interpolation. Every argument is known at issue time."""
    current=np.nan_to_num(current,nan=.5).astype("float32")
    previous=np.where(np.isfinite(previous),previous,current).astype("float32")
    normal=np.nan_to_num(normal,nan=.5).astype("float32")
    wet=(current>=.5)&valid
    def distance(mask):
        if not mask.any():return np.full(current.shape,100,dtype="float32")
        return np.minimum(ndimage.distance_transform_edt(~mask),100).astype("float32")
    # Normalized convolution: masked pixels do not contribute as false dry pixels.
    def local(size):
        den=ndimage.uniform_filter(valid.astype("float32"),size=size,mode="nearest")
        num=ndimage.uniform_filter(np.where(valid,current,0),size=size,mode="nearest")
        return np.divide(num,den,out=current.copy(),where=den>0)
    const=lambda v:np.full(current.shape,v,dtype="float32")
    xs=[current,previous,(current-previous)/max(age_days,1),normal,np.nan_to_num(frequency,nan=.5),current-normal,
        local(3),local(11),distance(wet),distance(valid&~wet),distance((normal>=.5)&valid),
        const(lead_days),const(age_days),const(np.sin(2*np.pi*day_of_year/365.25)),const(np.cos(2*np.pi*day_of_year/365.25))]
    return np.stack(xs,axis=-1).astype("float32")
