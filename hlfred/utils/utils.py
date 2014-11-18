import os
from astropy.io import fits
import pyfits
import pywcs
import json
from itertools import chain

sciexts = {'wfc3ir':[1], 'wfc3uvis':[1,4], 'acswfc':[1,4]}

def imgList(imgsdict, onlyacs=False):
    """Flattens the images dictionary to a list of images"""
    images = []
    for id in imgsdict.keys():
        if onlyacs:
            for fltr in imgsdict['acswfc'].keys():
                for i in imgsdict['acswfc'][fltr]:
                    images.append(i)
        else:
            for fltr in imgsdict[id].keys():
                for i in imgsdict[id][fltr]:
                    images.append(i)
    return images
    
def wConfig(cfgobj, cfgfile):
    """Write out a configuration file"""
    with open(cfgfile, 'w') as f:
        json.dump(cfgobj, f, sort_keys=True, indent=4)

def rConfig(cfgfile):
    """Read a configuration file"""
    with open(cfgfile, 'r') as f:
        cfgobj = json.load(f)
    return cfgobj

def getInstDet(fitsfile):
    """Get the instrument/detector of an HST image (e.g. acswfc)"""
    hdr = fits.getheader(fitsfile)
    return '%s%s' % (hdr['instrume'].lower(), hdr['detector'].lower())

def getFilter(fitsfile):
    """Return filter name"""
    instdet = getInstDet(fitsfile)
    if instdet == 'acswfc':
        ftr = fits.getval(fitsfile, 'filter1')
        if 'CLEAR' in ftr:
            ftr = fits.getval(fitsfile, 'filter2')
    else:
        ftr = fits.getval(fitsfile, 'filter')
    return ftr.lower()