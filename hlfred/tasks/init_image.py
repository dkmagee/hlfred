from hlfred.hutils import hutils
from astropy.io import fits
from drizzlepac import updatenpol
import stwcs
from stwcs import updatewcs
from astropy.io.fits.card import Undefined

def initImage(fitsfile):
    """Prepare an image for pipeline run
        - Checks if ACSWFC NPOL needs updating
        - Checks if moving target
        - Returns metadata (instdet, filter)
    """
    instdet = hutils.getInstDet(fitsfile)
    hdr = fits.getheader(fitsfile)
    
    if instdet == 'acswfc':
        if not 'SIPNAME' in list(hdr.keys()):
            print('Updating NPOL')
            updatenpol.update(fitsfile,'jref$')
        updatewcs.updatewcs(fitsfile)
        wnames = stwcs.wcsutil.altwcs.wcsnames(fitsfile, 1)
        if 'IDCFIX' in wnames.values():
            stwcs.wcsutil.altwcs.restoreWCS(fitsfile, [1,4], wcsname='IDCFIX')
        print('Fixing empty keys')
        with fits.open(fitsfile, mode='update') as hdu:
            for ext in [1, 4]:
                tddkeys = ['TDDALPHA', 'TDDBETA', 'TDD_CTA', 'TDD_CTB', 'TDD_CYA', 'TDD_CYB', 'TDD_CXA', 'TDD_CXB']
                for k in tddkeys:
                    if isinstance(hdu[ext].header[k], Undefined):
                        hdu[ext].header[k] = ''
            hdu.flush()
    
    if instdet == 'wfc3ir':
        if 'WCSAXESO' not in list(hdr.keys()):
            print('Updating WCS')
            updatewcs.updatewcs(fitsfile)
            wnames = stwcs.wcsutil.altwcs.wcsnames(fitsfile, 1)
            if 'IDCFIX' in wnames.values():
                stwcs.wcsutil.altwcs.restoreWCS(fitsfile, 1, wcsname='IDCFIX')
    
    if instdet == 'wfc3uvis':
        if 'WCSAXESO' not in list(hdr.keys()):
            print('Updating WCS')
            updatewcs.updatewcs(fitsfile)
            wnames = stwcs.wcsutil.altwcs.wcsnames(fitsfile, 1)
            if 'IDCFIX' in wnames.values():
                stwcs.wcsutil.altwcs.restoreWCS(fitsfile, [1,4], wcsname='IDCFIX')
    
    print('Checking if moving target observation')
    with fits.open(fitsfile, mode='update') as hdu:
        hdr = hdu[0].header
        if hdr['mtflag'] == 'T':
            hdr['mtflag'] = ' '
    
    filter = hutils.getFilter(fitsfile)
    return instdet, filter