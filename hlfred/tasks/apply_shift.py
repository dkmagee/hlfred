import pyfits
from stwcs.wcsutil import headerlet, HSTWCS
from stwcs.wcsutil.altwcs import deleteWCS
from drizzlepac import updatehdr
from drizzlepac import tweakback
import numpy as np
from scipy.spatial import cKDTree
from hlfred.utils import utils
import glob, sys
import matplotlib.pyplot as plt

def restoreWCSdrz(img, ext):
    wcs = HSTWCS(img, ext=ext, wcskey='A')
    print 'Removing any previous alternative WCS for image %s[%s]' % (img, ext)
    names = wcsnames(img, ext)
    for k, n in names.iteritems():
        if k not in [' ', 'O']:
            deleteWCS(img, ext, wcskey=k, wcsname=n)

    hdu = pyfits.open(img, mode='update')
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
    hdu.flush()
    
def restoreWCSflt(img, origimg,  ext):
    wcs = HSTWCS(origimg, ext=ext)
    print 'Removing any previous alternative WCS for image %s[%s]' % (img, ext)
    names = wcsnames(img, ext)
    for k, n in names.iteritems():
        if k not in [' ', 'O']:
            deleteWCS(img, ext, wcskey=k, wcsname=n)

    hdu = pyfits.open(img, mode='update')
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
    hdu.flush()

class Offsets(object):
    """Check and apply WCS offsets computed by superalign and simplematch"""
    def __init__(self, infiles, sa_in, sm_out, outfile, refimg):
        super(Offsets, self).__init__()
        self.infiles = infiles
        self.sa_in = sa_in
        self.sm_out = sm_out
        self.outfile = outfile
        self.refimg = refimg
        self.refwcs = HSTWCS(pyfits.open(self.refimg))
        self.sai = {}
        self.sao = {}
    
        print 'Reading %s...' % sm_out
        for i in [j.split() for j in open(sm_out).readlines()]:
            self.sao[i[0].replace('_drz_sci_sa.cat', '')] = [float(i[1]), float(i[2]), float(i[3])]
        
        self.vshifts = {}
        self.ishifts = {}
        with open(self.outfile, 'w') as sfile:
            for drz in self.infiles:
                wcs = HSTWCS(pyfits.open(drz))
                dsn = drz.replace('_drz_sci.fits', '')
                dx = self.sao[dsn][0]
                dy = self.sao[dsn][1]
                dt = self.sao[dsn][2]
                dxp = round(dx/wcs.pscale, 3)
                dyp = round(dy/wcs.pscale, 3)
                dtp = round(dt, 3)
                sfo = '%s %f %f %f\n' % (dsn, dxp, dyp, dtp)
                sfile.write(sfo)
                self.ishifts[drz] = [dxp, dyp, dtp]
                vis = drz[:6]
                if vis not in self.vshifts.keys():
                    self.vshifts[vis] = [[dxp], [dyp], [dtp]]
                else:
                    self.vshifts[vis][0].append(dxp)
                    self.vshifts[vis][1].append(dyp)
                    self.vshifts[vis][2].append(dtp)

    def checkOffsets(self, scat='sources.cat', search_radius=0.001, plot=True):
        """Checks offsets computed by superalign"""
        rcat = np.genfromtxt(scat, usecols=(1,2))
        rrdcat = self.refwcs.wcs_pix2sky((rcat/self.refwcs.pscale) + [self.refwcs.naxis1/2, self.refwcs.naxis2/2], 1)
        regout = open('sources.reg', 'w')
        regout.write('global color=green font="helvetica 8 normal" edit=1 move=1 delete=1 include=1 fixed=0\nfk5\n')
        for i,rd in enumerate(rrdcat.tolist()):
            oid = i+1
            regout.write('circle(%s,%s,%s") # color=%s text={%s}\n' % (rd[0], rd[1], 0.5, 'red', oid))
        regout.close()
        robj = open(scat).readlines()
        self.checks = {}
        all_res = []
        for n,s in self.ishifts.iteritems():
            csf = n.replace('.fits', '.cat.stars')
            icat = np.genfromtxt(csf, usecols=(1,2))
            wcs = HSTWCS(pyfits.open(n))
            dxp, dyp, dtp = self.ishifts[n]
            dt = dtp*np.pi/180.0
            dx = dxp*np.cos(dt) + dyp*np.sin(dt)
            dy = dyp*np.cos(dt) - dxp*np.sin(dt)
            ipix = icat/self.refwcs.pscale + wcs.wcs.crpix - [dx, dy]
            irdcat = wcs.wcs_pix2sky(ipix, 1)
            iobj = open(csf).readlines()
            kdr = cKDTree(rrdcat)
            kdi= cKDTree(irdcat)
            fnobjs = 0
            nearest = kdr.query_ball_tree(kdi, search_radius)
            fnobjs = len([nr for nr in nearest if nr != []])
            print 'Found %s pairs in %s' % (fnobjs, csf)
            dra = []
            ddec = []
            for i,j in enumerate(nearest):
                if j != []:
                    drd = (rrdcat[i] - irdcat[j[0]])*3600
                    dra.append(drd[0])
                    ddec.append(drd[1])
            resx = utils.iterstat(np.array(dra))
            resy = utils.iterstat(np.array(ddec))
            residuals = [round(resx[2], 5), round(resy[2], 5)]
            self.checks[n] = residuals
            all_res.append(residuals)
            rx = 'dRA={:+.5f}'.format(residuals[0])
            ry = 'dDec={:+.5f}'.format(residuals[1])
            print n, rx, ry
            # plot alignment check for each image
            if plot:
                plt.scatter(rrdcat[:,0], rrdcat[:,1], s=50, c='r', alpha=0.5)
                plt.scatter(irdcat[:,0], irdcat[:,1], s=5, c='k')
                plt.xlabel('RA')
                plt.ylabel('Dec')
                plt.title(n)
                plt.annotate(rx , xy=(.8,.1), xycoords='axes fraction')
                plt.annotate(ry, xy=(.8,.05), xycoords='axes fraction')
                plt.savefig(n.replace('.fits', '_plot.pdf'))
                plt.close()
        if plot:
            res = np.array(all_res)
            plt.scatter(res[:,0], res[:,1], s=1, c='k')
            plt.xlabel('dRA')
            plt.ylabel('dDec')
            plt.title('Relative Alignment')
            plt.axes().set_aspect('equal')
            plt.xlim(-0.1, 0.1)
            plt.ylim(-0.1, 0.1)
            plt.grid(True)
            sx = utils.iterstat(res[:,0])
            sy = utils.iterstat(res[:,1])
            s = '%s=%s+/-%s'
            plt.annotate(s % ('Mean dRA', round(sx[0], 4), round(sx[1], 4)) , xy=(.5,.1), xycoords='axes fraction')
            plt.annotate(s % ('Mean dDec', round(sy[0], 4), round(sy[1], 4)), xy=(.5,.05), xycoords='axes fraction')
            plt.savefig('offset_residuals_plot.pdf')
            plt.close()
        return self.checks
    
    def applyOffsets(self, restore=False, dsdir=None, hlet=False):
        """Determine offsets from superalign input file and output offsets file and update the DRZ file"""
        for d, s in self.ishifts.iteritems():
            dx, dy, dt = s[0], s[1], s[2]
            fl = d.replace('drz_sci.fits', 'flt.fits')
            print 'Updating drizzled image %s with offset' % d
            if restore:
                restoreWCSdrz(drz, 0)
                for ext in utils.sciexts[utils.getInstDet(fl)]:
                    ofl = os.path.join(dsdir, fl)
                    restoreWCSflt(fl, ofl, ext)
            
            updatehdr.updatewcs_with_shift(d, d, wcsname='DRZWCS', xsh=dx, ysh=dy, rot=dt, scale=1.0, force=True)
            print 'Updating flt image %s with offset' % fl
            tweakback.tweakback(d, input=fl, wcsname='DRZWCS_1', verbose=True, force=True)
            if hlet:
                headerlet.write_headerlet(fl, d, output=None, sciext='SCI', wcsname='DRZWCS_1', wcskey='PRIMARY', destim=None, sipname=None, npolfile=None, d2imfile=None, author=None, descrip=None, history=None, nmatch=None, catalog=None, attach=True, clobber=False, logging=False)