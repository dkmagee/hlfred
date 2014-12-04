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
        sa_in.write('%s %s %s %s\n' % (f.replace('.fits', '.cat'), round(0, 3), round(0, 3), 0))
    sa_in.close()

def runSuperAlign(cmd):
    """Run SuperAlign on stack of images"""
    print 'Running %s' % cmd
    call = subprocess.call(cmd, shell=True)
    return