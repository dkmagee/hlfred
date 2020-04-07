import os
from astropy.io import fits
import json
from itertools import chain
import numpy as np
from stwcs.wcsutil import HSTWCS
from scipy.spatial import ConvexHull, cKDTree

sciexts = {'wfc3ir':[1], 'wfc3uvis':[1,4], 'acswfc':[1,4]}
filters = {
    'F150LP':'violet',
    'F225W':'blueviolet',
    'F275W':'indigo',
    'F336W':'darkblue',
    'F435W':'green',
    'F606W':'yellow',
    'F775W':'gold',
    'F814W':'goldenrod',
    'F850LP':'darkorange',
    'F098M':'hotpink',
    'F105W':'orangered',
    'F125W':'salmon',
    'F140W':'red',
    'F160W':'darkred'
}


def imgList(imgsdict):
    """Flattens the images dictionary to a list of images"""
    images = []
    for id in list(imgsdict.keys()):
        for fltr in list(imgsdict[id].keys()):
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

def wImgLists(cfgobj):
    """Write out image lists"""
    for inst, data in cfgobj['images'].items():
        for fltr, dat in data.items():
            lstn = '%s_%s_%s.lst' % (cfgobj['dsname'], inst, fltr)
            print('Writing %s' % lstn)
            with open(lstn, 'w') as f:
                for i in dat:
                    f.write('%s\n' % i)

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

def getPScale(fitsfile):
    """Get plate scale of image"""
    wcs = HSTWCS(fits.open(fitsfile))
    return wcs.pscale

def getFootprint(fitsfile):
    """Get footprint of image"""
    instdet = getInstDet(fitsfile)
    fin = fits.open(fitsfile)
    exts = sciexts[instdet]
    wcs = HSTWCS(fin, exts[0])
    points = wcs.calc_footprint()
    if len(exts) > 1:
        wcs = HSTWCS(fin, exts[1])
        points = np.vstack((points, wcs.calc_footprint()))
    else:
        points = wcs.calc_footprint()
    hull = ConvexHull(points)
    vertices = np.take(points, hull.vertices, axis=0).flatten().tolist()
    fltr = getFilter(fitsfile).upper()
    dsn = fitsfile[:9]
    with open(fitsfile.replace('.fits', '_footprint.reg'), 'w') as reg:
        reg.write('global color=green font="helvetica 8 normal" edit=1 move=1 delete=1 include=1 fixed=0\nfk5\n')
        if fltr in list(filters.keys()):
            c = filters[fltr]
        else:
            c = 'white'
        reg.write('polygon(%s) # color=%s text={%s}\n' % (str(vertices)[1:-1], c, dsn))
            
def iterstat(inputarr, sigrej=3.0, maxiter=10, mask=0, max='', min='', rejval=''):
    ### routine for iterative sigma-clipping
    ngood    = inputarr.size
    arrshape = inputarr.shape
    if ngood == 0: 
        print('no data points given')
        return 0, 0, 0, 0
    if ngood == 1:
        print('only one data point; cannot compute stats')
        return 0, 0, 0, 0

    #determine max and min
    if max == '':
        max = inputarr.max()
    if min == '':
        min = inputarr.min()

    if np.unique(inputarr).size == 1:
        return 0, 0, 0, 0

    mask  = np.zeros(arrshape, dtype=np.byte)+1
    #reject those above max and those below min
    mask[inputarr > max] = 0
    mask[inputarr < min] = 0
    if rejval != '' :
        mask[inputarr == rejval]=0
    fmean = np.sum(1.*inputarr*mask) / ngood
    fsig  = np.sqrt(np.sum((1.*inputarr-fmean)**2*mask) / (ngood-1))

    nlast = -1
    iter  =  0
    ngood = np.sum(mask)
    if ngood < 2:
        return -1, -1, -1, -1

    while (iter < maxiter) and (nlast != ngood) and (ngood >= 2) :
        loval = fmean - sigrej*fsig
        hival = fmean + sigrej*fsig
        nlast = ngood
        
        mask[inputarr < loval] = 0
        mask[inputarr > hival] = 0
        ngood = np.sum(mask)

        if ngood >= 2:
            fmean = np.sum(1.*inputarr*mask) / ngood
            fsig  = np.sqrt(np.sum((1.*inputarr-fmean)**2*mask) / (ngood-1))

    savemask = mask.copy()
    iter = iter+1
    if np.sum(savemask) > 2:
        fmedian = np.median(inputarr[savemask == 1])
    else:
        fmedian = fmean
    return fmean, fsig, fmedian, savemask

def nn_match_radec(imgcat, refcat, oimgcat, orefcat):
    """Use Nearest Neighbors to match objects"""
    rcat = np.genfromtxt(refcat, usecols=(1,2))
    icat = np.genfromtxt(imgcat, usecols=(1,2))
    robj = open(refcat).readlines()
    iobj = open(imgcat).readlines()
    rout = open(orefcat, 'w')
    iout = open(oimgcat, 'w')
    kdr = cKDTree(rcat)
    kdi= cKDTree(icat)
    fnobjs = 0
    lnobjs = 0
    ldobjs = []
    nl = []
    rd = 0.0003
    near = kdr.query_ball_tree(kdi, rd)
    fnobjs = len([n for n in near if n != []])
    dobjs = fnobjs-lnobjs
    print('Radius: %s, Diff %s' % (1, dobjs))
    ldobjs.append(dobjs)
    nl.append(near)
    lnobjs = fnobjs
    bestr = np.array(ldobjs).argmax()
    matches = []
    # nearest = nl[bestr+5]
    nearest = nl[bestr]
    dxl = []
    dyl = []
    for i,j in enumerate(nearest):
        if j != []:
            ri, rx, ry, rr, rd, rm = [float(s) for s in robj[i].split()]
            ii, ix, iy, iir, iid, im, = [float(s) for s in iobj[j[0]].split()]
            matches.append([robj[i], iobj[j[0]]])
    nmatch = len(matches)
    print('%s: Found %s pairs' % (imgcat, nmatch))
    if nmatch < 5:
        print('Not enough pairs found!')
        print('Creating new reference catalog centered around image.')
        iimg = imgcat.replace('_all.cat', '.fits')
        cra = fits.getval(iimg, 'crval1')
        cdec = fits.getval(iimg, 'crval2')
        for i, rd in enumerate(rcat):
            # check if in 0.1 degree radius
            if (rd[0] - cra)**2 + (rd[1] - cdec)**2 < 0.0001:
                rout.write(robj[i])
        iout.writelines(iobj)
    else:
        for n in matches:
            rout.write(n[0])
            iout.write(n[1])
    rout.close()
    iout.close()
    return

