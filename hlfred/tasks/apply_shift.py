import pyfits
from stwcs.wcsutil import headerlet, HSTWCS
from drizzlepac import updatehdr
from drizzlepac import tweakback
import glob

def applyOffsets(infiles, sa_in, sa_out, outfile):
    """Determine offsets from superalign input file and output offsets file and update the DRZ file"""
    sai = {}
    sao = {}
    print 'Reading %s...' % sa_in
    for i in [j.split() for j in open(sa_in).readlines()[1:]]:
        sai[i[0].replace('_drz_sci.cat', '')] = [float(i[1]), float(i[2]), float(i[3])]
    
    print 'Reading %s...' % sa_out
    for i in [j.split() for j in open(sa_out).readlines()]:
        sao[i[0].replace('_drz_sci.cat', '')] = [float(i[1]), float(i[2]), float(i[3])]
        
    sfile = open(outfile, 'w')
    vshifts = {}
    for drz in infiles:
        wcs = HSTWCS(pyfits.open(drz))
        dsn = drz.replace('_drz_sci.fits', '')
        dx = sai[dsn][0] - sao[dsn][0]
        dy = sai[dsn][1] - sao[dsn][1]
        dt = sai[dsn][2] - sao[dsn][2]
        dxp = round(dx/wcs.pscale, 3)
        dyp = round(dy/wcs.pscale, 3)
        dtp = round(dt, 3)
        sfo = '%s %f %f %f\n' % (dsn, dxp, dyp, dtp)
        sfile.write(sfo)
        vis = drz[:6]
        if vis not in vshifts.keys():
            vshifts[vis] = [[dxp], [dyp], [dtp]]
        else:
            vshifts[vis][0].append(dxp)
            vshifts[vis][1].append(dyp)
            vshifts[vis][2].append(dtp)
    for k,v in vshifts.iteritems():
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