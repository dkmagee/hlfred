from hlfred.utils import utils
from astropy.io import fits
from drizzlepac import updatenpol

def initImage(fitsfile):
    """Prepare an image for pipeline run
        - Checks if ACSWFC NPOL needs updating
        - Checks if moving target
        - Returns metadata (instdet, filter)
    """
    instdet = utils.getInstDet(fitsfile)
    if instdet == 'acswfc':
        hdr = fits.getheader(fitsfile)
        if not 'SIPNAME' in hdr.keys():
            print 'Updating NPOL'
            updatenpol.update(fitsfile,'jref$')
    print 'Checking if moving target observation'
    hdu = fits.open(fitsfile, mode='update')
    hdr = hdu[0].header
    if hdr['mtflag'] == 'T':
        hdr['mtflag'] = ' '
    hdu.flush()
    hdu.close()
    
    filter = utils.getFilter(fitsfile)
    return instdet, filter