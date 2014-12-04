import numpy as np
import pyfits
from astropy.io import fits
from stwcs.wcsutil import HSTWCS
from hlfred.utils import sextractor
import os

_sa_config = {
        'acswfc':{
                'low_limit':1.55,
                'hi_limit': 20.0,
                'min_axis_ratio':0.33,
                'edge_buf':12,
                'lower_pixthresh':3.75,
                'orient_adj':2.5
        },
        'wfc3uvis':{
                'low_limit':1.55,
                'hi_limit': 20.0,
                'min_axis_ratio':0.33,
                'edge_buf':12,
                'lower_pixthresh':3.75,
                'orient_adj':2.5
        },
        'wfc3ir':{
                'low_limit':1.55,
                'hi_limit': 20.0,
                'min_axis_ratio':0.33,
                'edge_buf':12,
                'lower_pixthresh':3.75,
                'orient_adj':0.4
        }
}

# SExtractor catalog parameters
_sex_parms = [
        'NUMBER',
        'XWIN_IMAGE',
        'YWIN_IMAGE',
        'ALPHA_J2000',
        'DELTA_J2000',
        'A_IMAGE',
        'B_IMAGE',
        'MAG_AUTO',
        'FLUX_AUTO',
        'FWHM_IMAGE'
]

# SExtractor configuration parameters
_sex_config = {
        'CATALOG_NAME':'sa_temp.cat',
        'CATALOG_TYPE':'ASCII_HEAD',
        'DETECT_THRESH':10.0,
        'DETECT_MINAREA':3,
        'ANALYSIS_THRESH':10.0,
        'FILTER': 'N',
        'DEBLEND_NTHRESH':16,
        'DEBLEND_MINCONT':0.05,
        'CLEAN': 'YES',
        'CLEAN_PARAM': 1.0,
        'MASK_TYPE': 'CORRECT',
        'SATUR_LEVEL': 128000.0,
        'GAIN': 1.0,
        'MAG_ZEROPOINT':0.0,
        'MAG_GAMMA':4.0,
        'PIXEL_SCALE':1,
        'SEEING_FWHM':1.6,
        'WEIGHT_TYPE':None,
        'VERBOSE_TYPE':'NORMAL'
}

class Object:
    def __init__(self, x, y, ra, dec, r, mag, flux):
        self.x = x
        self.y = y
        self.ra = ra,
        self.dec = dec,
        self.r = r
        self.mag = mag
        self.flux = flux
        self.nextToBig = 0
        self.dx = 0
        self.dy = 0

class MakeCat(object):
    def __init__(self, refimg):
        super(MakeCat, self).__init__()
        self.refimg = refimg
        self.refwcs = HSTWCS(pyfits.open(self.refimg))
        
    def getInstDet(self, imgfile):
        """Get the instrument/detector of an HST image (e.g. acswfc)"""
        hdr = fits.getheader(imgfile)
        return '%s%s' % (hdr['instrume'].lower(), hdr['detector'].lower())

    def findSources(self, inputfile, outputfile, instdet, weightfile=None, **sconfig):
        """Finds objects in image"""
        # Set up SExtractor
        sex = sextractor.SExtractor()
        # Load the default configuration
        for k,v in _sex_config.iteritems():
            sex.config[k] = v
        if sconfig:
            # Load any runtime configuration
            for k,v in sconfig.iteritems():
                sex.config[k] = v
        if weightfile:
            rmsfile = weightfile.replace('wht.fits', 'rms.fits')
            if not os.path.exists(rmsfile):
                fobj = fits.open(weightfile)
                fobj[0].data = 1/np.sqrt(fobj[0].data)
                fobj.writeto(rmsfile, clobber=True)
            sex.config['WEIGHT_IMAGE'] = rmsfile
            sex.config['WEIGHT_TYPE'] = 'MAP_RMS'
            sex.config['WEIGHT_GAIN'] = 'N'
        sex.config['CATALOG_NAME'] = outputfile
        # Load default parameters'
        sex.config['PARAMETERS_LIST'] = []
        for p in _sex_parms:
            sex.config['PARAMETERS_LIST'].append(p)
        # Run SExtractor
        sex.run(inputfile)
        objectlist = []
        for l in [i.split() for i in open(outputfile).readlines()]:
            if l[0] != '#':
                x = float(l[1])
                y = float(l[2])
                ra = float(l[3])
                if l[4].startswith('+'):
                    dec = float(l[4][1:])
                else:
                    dec = float(l[4])
                aa = float(l[5])
                ba = float(l[6])
                r = ba / aa
                m = float(l[7])
                f = float(l[8])
                fwhm = float(l[9])
                cfg = _sa_config[instdet]
                axis_ratio =  ba / aa
                if min(2.3 * ba, fwhm) >= cfg['low_limit'] and max(2.3 * aa, fwhm) < cfg['hi_limit'] and r > cfg['min_axis_ratio']:
                    objectlist.append(Object(x, y, ra, dec, r, m, f))
        return objectlist

    def removeCloseSources(self, objectlist):
        """Removes objects from catalog with multiple close detections"""
        for objecti in objectlist:
            for objectj in objectlist:
                dist = ((objecti.x - objectj.x) ** 2 + (objecti.y - objectj.y) ** 2) ** 0.5
                if dist < 10 and dist > 0:
                    if objecti.mag < objectj.mag:
                        objectj.nextToBig = 1
                    else:
                        objecti.nextToBig = 1
        objectlist_keep = []
        for objecti in objectlist:
            if not objecti.nextToBig:
                objectlist_keep.append(objecti)
            else:
                print 'Excluding object at %i %i' % (objecti.x, objecti.y)
        return objectlist_keep

    def makeSACat(self, imgfile, instdet, weightfile=None):
        """Makes a catalog of objects to be used for input to superalign and creates a DS9 region file of objects"""
        
        imgfile_cat = '%s.cat' % imgfile.replace('.fits', '')
        imgfile_reg = '%s.reg' % imgfile.replace('.fits', '')
    
        o_radec = []
        ext = 0
        objectlist = self.findSources('%s[%s]' % (imgfile, ext), imgfile_cat, instdet, weightfile)
        cleanobjectlist = self.removeCloseSources(objectlist)
        print 'Found %s sources' % len(cleanobjectlist)
        wcs = HSTWCS(pyfits.open(imgfile))
        for obj in cleanobjectlist:
            sky = wcs.wcs_pix2sky(np.array([[obj.x, obj.y]]), 1)
            o_radec.append([obj.ra[0], obj.dec[0]])
            obj.ra = sky[0][0]
            obj.dec = sky[0][1]
    
        regout = open(imgfile_reg, 'w')
        regout.write('global color=green font="helvetica 8 normal" edit=1 move=1 delete=1 include=1 fixed=0\nfk5\n')
        for i,rd in enumerate(o_radec):
            oid = i+1
            regout.write('circle(%s,%s,%s") # color=%s text={%s}\n' % (rd[0], rd[1], 0.5, 'red', oid))
        regout.close()
    
        # Now we need to write out the catalog in the reference image coords in arcseconds with respect to center of the reference image
        catout = open(imgfile_cat, 'w')
        for i,obj in enumerate(cleanobjectlist):
            oid = i+1
            # arcs = (wcs.wcs_sky2pix(np.array([[obj.ra, obj.dec]]), 1) - wcs.wcs.crpix) * self.refwcs.pscale
            arcs = (self.refwcs.wcs_sky2pix(np.array([[obj.ra, obj.dec]]), 1) - self.refwcs.wcs.crpix) * self.refwcs.pscale
            catout.write('%i %f %f %f\n' % (oid, np.round(arcs[0][0], 3), np.round(arcs[0][1], 3), np.round(obj.mag, 1)))
        catout.close()
        return

