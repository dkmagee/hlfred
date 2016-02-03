import numpy as np
from stwcs.wcsutil import HSTWCS
import pyfits
import subprocess
import os, sys
import math

def makeSAin(imgs, refwcs, refcat):
    sa_in = open('superalign.in', 'w')
    sa_in.write('%s 1\n' % str(len(imgs)+1))
    sa_in.write('%s 0.000 0.000 0.000\n' % refcat)
    for drz in imgs:
            f = os.path.basename(drz)
            wcs = HSTWCS(pyfits.open(f))
            sky = wcs.wcs_pix2sky([[wcs.naxis1/2, wcs.naxis2/2]], 1)
            arc = (refwcs.wcs_sky2pix(sky, 1) - [refwcs.naxis1/2, refwcs.naxis2/2]) * refwcs.pscale
            rot = round(refwcs.orientat - wcs.orientat, 3)
            sa_in.write('%s %s %s %s\n' % (f.replace('.fits', '_sa.cat'), round(arc[0][0], 3), round(arc[0][1], 3), rot))
    sa_in.close()

def runSuperAlign(cmd):
    """Run SuperAlign on stack of images"""
    print 'Running: %s' % cmd
    call = subprocess.call(cmd, shell=True)
    return
    
def runSimpleMatch():
    """Run SimpleMatch on stack of images"""
    print 'Reading superalign.in'
    sa_in = {}
    sm_out = open('simplematch.out', 'w')
    for i in open('superalign.in', 'r').readlines()[2:]:
        s = i.split()
        cs = s[0].replace('.cat', '.cat.stars')
        cf = s[0].replace('.cat', '.cat.fit')
        cmd = 'simplematch sources.cat %s %s %s %s %s' % (cs, s[1], s[2], s[3], cf)
        print 'Running: %s' % cmd
        call = subprocess.call(cmd, shell=True)
        # Get the fitted shifts an put them in simplematch.out
        fit = open(cf, 'r').readlines()
        aa = float(fit[1].split()[1])
        bb = float(fit[2].split()[1])
        cc = float(fit[3].split()[1])
        dd = float(fit[4].split()[1])
        ee = float(fit[5].split()[1])
        ff = float(fit[6].split()[1])
        if bb == 0.:
            angle_x = 90.0
        else:
            angle_x = -(180. / math.pi) * math.atan2(ee, bb)
        if ff == 0.:
            angle_y = 90.0
        else:
            angle_y = 180. / math.pi * math.atan2(cc, ff)
            
        if abs(angle_x - angle_y - 360) < 1:
            angle_x -= 360
        if abs(angle_x - angle_y + 360) < 1:
            angle_x += 360
        
        print 'Shift: dx = %s dy = %s theta = %s' % (aa, dd, (angle_x + angle_y)/2)
        
        dx = float(s[1]) - aa
        dy = float(s[2]) - dd
        dt = float(s[3]) - (angle_x + angle_y)/2
        
        print 'Final shift: dx = %s dy = %s dt = %s' % (dx, dy, dt)
        sm_out.write('%s %s %s %s\n' % (s[0], dx, dy, dt))
    sm_out.close()
    return