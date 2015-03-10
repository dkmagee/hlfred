from drizzlepac import astrodrizzle
from stwcs.wcsutil import headerlet, HSTWCS

def drzMosaic(infiles, outfile, refimg=None, usehlet=False, ctype='imedian'):
    """Run full AstroDrizzle"""
    if usehlet:
        for flt in infiles:
            hdrlet = flt.replace('_flt.fits', '_hlet.fits')
            headerlet.apply_headerlet_as_primary(flt, hdrlet, attach=True, archive=True, force=False, logging=False)
    astrodrizzle.AstroDrizzle(
        infiles,
        output=outfile,
        num_cores=4,
        preserve=False,
        context=False,
        wcskey='DRZWCS_1',
        combine_type=ctype,
        driz_combine=False,
        final_wcs=True,
        final_refimage=refimg,
        final_pixfrac=0.75
    )