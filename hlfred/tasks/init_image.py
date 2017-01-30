from hlfred.utils import utils
from astropy.io import fits
from drizzlepac import updatenpol
from stwcs import updatewcs

def initImage(fitsfile):
    """Prepare an image for pipeline run
        - Checks if ACSWFC NPOL needs updating
        - Checks if moving target
        - Returns metadata (instdet, filter)
    """
    instdet = utils.getInstDet(fitsfile)
    hdr = fits.getheader(fitsfile)
    
    if instdet == 'acswfc':
        if not 'SIPNAME' in hdr.keys():
            print 'Updating NPOL'
            updatenpol.update(fitsfile,'jref$')
            updatewcs.updatewcs(fitsfile)
    if instdet == 'wfc3ir' or instdet == 'wfc3uvis':
        if 'WCSAXESO' not in hdr.keys():
            print 'Updating WCS'
            updatewcs.updatewcs(fitsfile)
    
    print 'Checking if moving target observation'
    with fits.open(fitsfile, mode='update') as hdu:
        hdr = hdu[0].header
        if hdr['mtflag'] == 'T':
            hdr['mtflag'] = ' '
    
    filter = utils.getFilter(fitsfile)
    return instdet, filter