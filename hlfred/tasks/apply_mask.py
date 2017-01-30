import numpy as np
import os, sys, glob
from astropy.io import fits
import pyregion
from hlfred.utils import utils
from PIL import Image, ImageDraw

def applymask(fitsimg, regionfile, dq_ext):
    """Apply a mask to an HST image DQ array given a DS9 region file with polygons regions identifying areas to mask"""
    print 'Reading region file %s' % regionfile
    with fits.open(fitsimg, 'update') as fin:
        print 'Applying %s to DQ ext %s' % (fitsimg, dq_ext)
        data = fin[dq_ext].data
        instdet = utils.getInstDet(fitsimg)
        if instdet == 'wfc3ir':
            w,h = data.shape
        else:
            h,w = data.shape
        img = Image.new('L', (w, h), 0)
        regions = pyregion.open(regionfile).as_imagecoord(header=fin[dq_ext].header)
        for reg in regions:
            if reg.name == 'polygon':
                ImageDraw.Draw(img).polygon(reg.coord_list, outline=1, fill=1)
        data |= np.array(img)*8192
    print 'Updating DQ array complete!'
    
    return

def applypersist(fitsimg, maskimg):
    """Apply persistence mask to WFC3IR image DQ array given a persist mask image"""
    print 'Updating DQ array in image %s using persistent mask image %s' % (fitsimg, maskimg)
    with fits.open(fitsimg,'update') as fin:
        data = fin[3].data
        mask = fits.getdata(maskimg).astype(np.bool)
        data[mask] = 512