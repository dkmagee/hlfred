import numpy as np
from stwcs.wcsutil import HSTWCS
import pyfits
import subprocess
import os

def makeSAin(imgs, refwcs, refcat):
    sa_in = open('superalign.in', 'w')
    sa_in.write('%s 0\n' % str(len(imgs)+1))
    sa_in.write('%s 0.000 0.000 0.000\n' % refcat)
    for drz in imgs:
        f = os.path.basename(drz)
        wcs = HSTWCS(pyfits.open(f))
        sky = np.array([[wcs.wcs.crval[0], wcs.wcs.crval[1]]])
        pix = (refwcs.wcs_sky2pix(sky, 1) - refwcs.wcs.crpix) * refwcs.pscale
        rot = round(refwcs.orientat - wcs.orientat, 3)
        sa_in.write('%s %s %s %s\n' % (f.replace('.fits', '.cat'), round(pix[0][0], 3), round(pix[0][1], 3), rot))
    sa_in.close()

def runSuperAlign(cmd):
    """Run SuperAlign on stack of images"""
    print 'Running %s' % cmd
    call = subprocess.call(cmd, shell=True)
    return