import pyfits
from stwcs.wcsutil import headerlet, HSTWCS
from drizzlepac import updatehdr
from drizzlepac import tweakback
import numpy as N
from scipy.spatial import cKDTree
import glob, sys
import matplotlib.pyplot as plt

class Offsets(object):
    """Check and apply WCS offsets computed by superalign"""
    def __init__(self, infiles, sa_in, sa_out, outfile, refimg):
        super(Offsets, self).__init__()
        self.infiles = infiles
        self.sa_in = sa_in
        self.sa_out = sa_out
        self.outfile = outfile
        self.refimg = refimg
        self.refwcs = HSTWCS(pyfits.open(self.refimg))
        self.sai = {}
        self.sao = {}
        print 'Reading %s...' % sa_in
        for i in [j.split() for j in open(sa_in).readlines()[1:]]:
            self.sai[i[0].replace('_drz_sci.cat', '')] = [float(i[1]), float(i[2]), float(i[3])]
    
        print 'Reading %s...' % sa_out
        for i in [j.split() for j in open(sa_out).readlines()]:
            self.sao[i[0].replace('_drz_sci.cat', '')] = [float(i[1]), float(i[2]), float(i[3])]
        
        self.vshifts = {}
        self.ishifts = {}
        with open(self.outfile, 'w') as sfile:
            for drz in self.infiles:
                wcs = HSTWCS(pyfits.open(drz))
                dsn = drz.replace('_drz_sci.fits', '')
                dx = self.sai[dsn][0] - self.sao[dsn][0]
                dy = self.sai[dsn][1] - self.sao[dsn][1]
                dt = self.sai[dsn][2] - self.sao[dsn][2]
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
        rcat = N.genfromtxt(scat, usecols=(1,2))
        rrdcat = self.refwcs.wcs_pix2sky((rcat/self.refwcs.pscale) + self.refwcs.wcs.crpix, 1)
        robj = open(scat).readlines()
        self.checks = {}
        for n,s in self.ishifts.iteritems():
            csf = n.replace('.fits', '.cat.stars')
            icat = N.genfromtxt(csf, usecols=(1,2))
            wcs = HSTWCS(pyfits.open(n))
            dxp, dyp, dtp = self.ishifts[n]
            dt = dtp*N.pi/180.0
            dx = dxp*N.cos(dt) + dyp*N.sin(dt)
            dy = dyp*N.cos(dt) - dxp*N.sin(dt)
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
            residuals = [round(N.median(N.array(dra)), 5), round(N.median(N.array(ddec)), 5)]
            self.checks[n] = residuals
            rx = 'dRA={:+.5f}'.format(residuals[0])
            ry = 'dDec={:+.5f}'.format(residuals[1])
            print n, rx, ry
            # plot
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
        return self.checks
    
    def applyOffsets(self):
        """Determine offsets from superalign input file and output offsets file and update the DRZ file"""
        for k,v in self.vshifts.iteritems():
            mdx = sum(v[0])/len(v[0])
            mdy = sum(v[1])/len(v[1])
            mdt = sum(v[2])/len(v[2])
            print 'Mean offsets for %s' % k
            print 'dx: %s dy: %s dt: %s' % (mdx, mdy, mdt)
            visdrzs = glob.glob('?%s???_drz_sci.fits' % k[1:])

            for vdrz in visdrzs:
                fl = vdrz.replace('drz_sci.fits', '_flt.fits')
                print 'Updating %s with mean offset' % fl
                updatehdr.updatewcs_with_shift(vdrz, vdrz, wcsname='DRZWCS', xsh=mdx, ysh=mdy, rot=mdt, scale=1.0, force=True)
                tweakback.tweakback(vdrz, input=fl, wcsname='DRZWCS_1', verbose=True)
                headerlet.write_headerlet(fl, k.upper(), output=None, sciext='SCI', wcsname='DRZWCS_1', wcskey='PRIMARY', destim=None, sipname=None, npolfile=None, d2imfile=None, author=None, descrip=None, history=None, nmatch=None, catalog=None, attach=True, clobber=False, logging=False)