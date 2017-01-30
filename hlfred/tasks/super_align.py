import numpy as np
from stwcs.wcsutil import HSTWCS
from drizzlepac import updatehdr
from scipy.spatial import cKDTree
from astropy.io import fits
import subprocess
import os, sys
import math
from hlfred.utils import mcmcShifts

def nn_match(imgcat, refcat, refwcs, oimgcat, orefcat, iter=1):
    """Use Nearest Neighbors to match objects"""
    rcat = np.genfromtxt(refcat, usecols=(3,4))
    icat = np.genfromtxt(imgcat, usecols=(3,4))
    robj = open(refcat).readlines()
    iobj = open(imgcat).readlines()
    rout = open(orefcat, 'w')
    iout = open(oimgcat, 'w')
    xyout = open(oimgcat.replace('.cat', '_xyxy.cat'), 'w')
    kdr = cKDTree(rcat)
    kdi= cKDTree(icat)
    fnobjs = 0
    lnobjs = 0
    ldobjs = []
    nl = []
    for r in range(iter):
        rd = 5
        near = kdr.query_ball_tree(kdi, rd)
        fnobjs = len([n for n in near if n != []])
        dobjs = fnobjs-lnobjs
        print 'Radius: %s, Diff %s' % (r, dobjs)
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
            xyout.write('%s %s %s %s\n' % (rx, refwcs.naxis2-ry, rx-ix, ry-iy))
            matches.append([robj[i], iobj[j[0]]])
    xyout.close()
    print '%s: Found %s pairs' % (imgcat, len(matches))
    for n in matches:
        rout.write(n[0])
        iout.write(n[1])
    rout.close()
    iout.close()
    return

def makeSAin(visit, imgs, refwcs, refcat_sa):
    sa_file = '%s_superalign.in' % visit
    print 'Creating %s' % sa_file
    sa_in = open(sa_file, 'w')
    sa_in.write('%s 1\n' % str(len(imgs)+1))
    sa_in.write('%s 0.000 0.000 0.000\n' % refcat_sa)
    for drz in imgs:
        f = os.path.basename(drz)
        wcs = HSTWCS(fits.open(drz))
        sky = wcs.all_pix2world([[wcs.naxis1/2, wcs.naxis2/2]], 1)
        arc = (refwcs.all_world2pix(sky, 1) - [refwcs.naxis1/2, refwcs.naxis2/2]) * refwcs.pscale
        rot = round(refwcs.orientat - wcs.orientat, 3)
        sa_in.write('%s %s %s %s\n' % (f.replace('.fits', '_sa.cat'), round(arc[0][0], 3), round(arc[0][1], 3), rot))
    sa_in.close()

def runSuperAlign(cmd):
    """Run SuperAlign on stack of images"""
    print 'Running: %s' % cmd
    call = subprocess.call(cmd, shell=True)
    return
    
def runSimpleMatch(visit):
    """Run SimpleMatch on stack of images"""
    print 'Reading %s_superalign.in' % visit
    sa_in = {}
    no_star = []
    sm_out = open('%s_simplematch.out' % visit, 'w')
    for i in open('%s_superalign.in' % visit, 'r').readlines()[2:]:
        s = i.split()
        cs = s[0].replace('.cat', '.cat.stars')
        cf = s[0].replace('.cat', '.cat.fit')
        cmd = 'simplematch %s_sources.cat %s %s %s %s %s' % (visit, cs, s[1], s[2], s[3], cf)
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
    if no_star:
        print 'No star file found for:'
        for i in no_star:
            print i
    return


def applyShiftsSA(visit):
    sa_out = '%s_simplematch.out' % visit
    drzs = {}
    print 'Reading %s...' % sa_out
    for i in [j.split() for j in open(sa_out).readlines()]:
        drz = i[0].replace('_sa.cat', '.fits')
        drzs[drz] = [float(i[1]), float(i[2]), float(i[3])]
    print "Applying shifts..."
    for d, s in drzs.iteritems():
        if os.path.exists(d):
            if d[:6] == visit:
                if s:
                    dx, dy, dt = s
                    wcs = HSTWCS(fits.open(d))
                    dxp = round(dx/wcs.pscale, 3)
                    dyp = round(dy/wcs.pscale, 3)
                    dtp = round(dt, 3)
                    print d, dxp, dyp, dtp
                    updatehdr.updatewcs_with_shift(d, d, wcsname='DRZWCS', xsh=dxp, ysh=dyp, rot=dtp, scale=1.0, force=True)

def makeSourceCat(visit, refwcs):
    scat = '%s_sources.cat' % visit
    rcat = np.genfromtxt(scat, usecols=(1,2))
    rrdcat = refwcs.all_pix2world((rcat/refwcs.pscale) + [refwcs.naxis1/2, refwcs.naxis2/2], 1)

    regout = open('%s_sources_rd.reg' % visit, 'w')
    regout.write('global color=green font="helvetica 8 normal" edit=1 move=1 delete=1 include=1 fixed=0\nfk5\n')
    for i,rd in enumerate(rrdcat.tolist()):
        oid = i+1
        regout.write('circle(%s,%s,%s") # color=%s text={%s}\n' % (rd[0], rd[1], 0.5, 'red', oid))
    regout.close()

    gsc = '%s_sources_rd.cat' % visit
    gsources = open(gsc, 'w')
    for i,rd in enumerate(rrdcat.tolist()):
        oid = i+1
        gsources.write('%s %s %s 22.0\n' % (oid, rd[0], rd[1]))
    gsources.close()


def stars2cat(drzfile, refwcs):
    """
     Makes catalog file from a superalign .stars file
    """
    wcs = HSTWCS(fits.open(drzfile))
    starsfile = drzfile.replace('.fits', '_sa.cat.stars')
    catfile = '%s.cat' % starsfile
    rcat = np.genfromtxt(starsfile, usecols=(1,2))
    rrdcat = wcs.all_pix2world((rcat/wcs.pscale) + [wcs.naxis1/2, wcs.naxis2/2], 1).tolist()
    xy = refwcs.all_world2pix(rrdcat, 1).tolist()
    with open(catfile, 'w') as catout:
        for i,rd in enumerate(rrdcat):
            catout.write('%d %.8f %.8f %.3f %.3f %d\n' % (i, rd[0], rd[1], xy[i][0], xy[i][1], i))

def refineShiftMCMC(drzfile):
    """
     Refine shifts using MCMC
    """
    dsn = drzfile[:9]
    wcs = HSTWCS(fits.open(drzfile))
    wcsn = fits.getval(drzfile, 'wcsname')
    try:
        refcat = np.loadtxt('%s_drz_sci_sa_ref_match.cat' % dsn , usecols=(1,2))
        imgcat = np.loadtxt('%s_drz_sci_sa_match.cat' % dsn , usecols=(1,2))

        refcatw = wcs.all_world2pix(refcat, 1)
        imgcatw = wcs.all_world2pix(imgcat, 1)

        ox, oy = wcs.wcs.crpix.tolist()

        offset, err = mcmcShifts.findOffsetMCMC(imgcatw, refcatw, maxShift=(5, 5, 0.3), rotOrigin=(ox, oy), precision=0.01, visualize=False)
        print drzfile, offset, err

        dxp, dyp, dtp = offset
        updatehdr.updatewcs_with_shift(drzfile, drzfile, wcsname='DRZWCS', xsh=dxp, ysh=dyp, rot=dtp, scale=1.0, force=True)
        return offset
    except UserWarning:
        pass
