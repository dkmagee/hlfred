from astropy.io import fits
from stwcs.wcsutil import headerlet, HSTWCS
from stwcs.wcsutil.altwcs import deleteWCS
from drizzlepac import tweakback
from hlfred.utils import utils
import glob, sys

def restoreWCSdrz(img, ext):
    wcs = HSTWCS(img, ext=ext, wcskey='A')
    print 'Removing any previous alternative WCS for image %s[%s]' % (img, ext)
    names = wcsnames(img, ext)
    for k, n in names.iteritems():
        if k not in [' ', 'O']:
            deleteWCS(img, ext, wcskey=k, wcsname=n)

    with fits.open(img, mode='update') as hdu:
        hdu[ext].header['CD1_1'] = wcs.wcs.cd[0][0]
        hdu[ext].header['CD1_2'] = wcs.wcs.cd[0][1]
        hdu[ext].header['CD2_1'] = wcs.wcs.cd[1][0]
        hdu[ext].header['CD2_2'] = wcs.wcs.cd[1][1]
        hdu[ext].header['CRVAL1'] = wcs.wcs.crval[0]
        hdu[ext].header['CRVAL2'] = wcs.wcs.crval[1]
        hdu[ext].header['CRPIX1'] = wcs.wcs.crpix[0]
        hdu[ext].header['CRPIX2'] = wcs.wcs.crpix[1]
        hdu[ext].header['ORIENTAT'] = 0.0
        hdu[ext].header['WCSNAME'] = 'DRZWCS'
        del hdu[ext].header['LATPOLE']
        del hdu[ext].header['LONPOLE']
    
def restoreWCSflt(img, origimg,  ext):
    wcs = HSTWCS(origimg, ext=ext)
    print 'Removing any previous alternative WCS for image %s[%s]' % (img, ext)
    names = wcsnames(img, ext)
    for k, n in names.iteritems():
        if k not in [' ', 'O']:
            deleteWCS(img, ext, wcskey=k, wcsname=n)
    
    with fits.open(img, mode='update') as hdu:
        hdu[ext].header['CD1_1'] = wcs.wcs.cd[0][0]
        hdu[ext].header['CD1_2'] = wcs.wcs.cd[0][1]
        hdu[ext].header['CD2_1'] = wcs.wcs.cd[1][0]
        hdu[ext].header['CD2_2'] = wcs.wcs.cd[1][1]
        hdu[ext].header['CRVAL1'] = wcs.wcs.crval[0]
        hdu[ext].header['CRVAL2'] = wcs.wcs.crval[1]
        hdu[ext].header['CRPIX1'] = wcs.wcs.crpix[0]
        hdu[ext].header['CRPIX2'] = wcs.wcs.crpix[1]
        hdu[ext].header['ORIENTAT'] = wcs.orientat
        del hdu[ext].header['WCSNAME']
        del hdu[ext].header['LATPOLE']
        del hdu[ext].header['LONPOLE']
  
def applyOffset(drzfile, fltfile, hlet=False):
    """Apply offset to an flt image from an aligned drizzled image"""
    tweakback.tweakback(drzfile, input=fltfile, origwcs='DRZWCS', verbose=True, force=True)
    if hlet:
        headerlet.write_headerlet(fltfile, 'HLFRED', output=None, sciext='SCI', wcsname='DRZWCS_2', wcskey='PRIMARY', destim=None, sipname=None, npolfile=None, d2imfile=None, author=None, descrip=None, history=None, nmatch=None, catalog=None, attach=True, clobber=False, logging=False)