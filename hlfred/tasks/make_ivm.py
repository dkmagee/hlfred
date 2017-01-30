from astropy.io import fits
import numpy as np
import os, sys, glob, shutil

def makeweight(ffin, iref):
    """Make inverse variance map for WFC3IR data"""
    ffout = ffin.replace('flt', 'ivm')
    print 'Generating IVM image %s' % ffout
    ffo = fits.open(ffin)
    sci = ffo['SCI'].data
    etime = ffo['TIME'].data
    bkg = float(ffo[1].header.get('BKG'))
    etimez = np.where(etime==0, 1, etime)
    flat = ffo[0].header['PFLTFILE'].replace('iref$', iref)
    ffd = fits.getdata(flat)
    flatfield = ffd[5:1019,5:1019]
    flatfieldz = np.where(flatfield==0, 1, flatfield)
    invflat = 1.0/flatfieldz
    gain = 1.0 # because already in electrons / s
    # Readnoise: 21 e- (CDS) 15.5 e- (16-read linear fit)
    readnoise = 21.0
    variance = ((etimez*flatfieldz*bkg + readnoise**2)/(etimez**2 * flatfieldz**2))
    weight = 1/(variance)
    weight /= (etimez**2) # correct for the fact that multidrizzle multiples by the etime**2
    ffo[1].header['EXTNAME'] = 'IVM'
    ffo[1].data = weight
    ffo.writeto(ffout,clobber=True)
    ffo.close()