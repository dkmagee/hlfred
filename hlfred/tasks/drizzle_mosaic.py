from astropy.io import fits
import numpy as np
import shutil
from drizzlepac import astrodrizzle as ad
from stwcs.wcsutil import headerlet, HSTWCS

def drzMosaic(infiles, outfile, refimg=None, optcr=False, drzonly=False, usehlet=False, ctype='imedian', pixfrac=0.75):
    """Run full AstroDrizzle"""
    if usehlet:
        for flt in infiles:
            hdrlet = flt.replace('_flt.fits', '_hlet.fits')
            headerlet.apply_headerlet_as_primary(flt, hdrlet, attach=True, archive=True, force=False, logging=False)
            
    if optcr:
        # first make median image
        print('Creating median image...')
        ad.AstroDrizzle(infiles,
                        static=False,
                        skysub=False,
                        driz_separate=True,
                        median=True,
                        combine_type='imedian',
                        blot=False,
                        driz_cr=False,
                        driz_combine=False,
                        preserve=False,
                        context=False)
        shutil.move('final_med.fits', 'median.fits')
        # next make a minmed image
        print('Creating minmed image...')
        ad.AstroDrizzle(infiles,
                        static=False,
                        skysub=False,
                        driz_separate=False,
                        median=True,
                        combine_type='iminmed',
                        blot=False,
                        driz_cr=False,
                        driz_combine=False,
                        preserve=False,
                        context=False)
        shutil.move('final_med.fits', 'minmed.fits')
        # make a context image
        print('Creating combined median/minmed image...')
        ctx = fits.getdata('minmed.fits')*0
        for i in infiles:
            ssci = i.replace('_flt.fits', '_single_sci.fits')
            ctx += np.where(fits.getdata(ssci)==0, 0, 1)
        # if there are less than 5 overlaping exposures we will use minmed instead of median
        mm_mask = np.where(ctx<=5, 1, 0)
        mm = fits.getdata('minmed.fits')
        med = fits.getdata('median.fits')
        # create new final_med.fits
        fmed = mm*mm_mask + med*np.where(mm_mask==1, 0, 1)
        fits.writeto('final_med.fits', fmed.astype(np.float32))
        # now run blot and driz_cr
        print('Running blot & driz_cr using combined median image...')
        ad.AstroDrizzle(infiles,
                        static=False,
                        skysub=False,
                        driz_separate=False,
                        median=False,
                        blot=True,
                        driz_cr=True,
                        driz_combine=False,
                        preserve=False,
                        context=False)
        # # do the final drizzle combine
        ad.AstroDrizzle(infiles,
                        output=outfile,
                        static=True,
                        skysub=True,
                        driz_separate=False,
                        median=False,
                        blot=False,
                        driz_cr=False,
                        driz_combine=True,
                        final_refimage=refimg,
                        final_pixfrac=pixfrac,
                        final_fillval=0,
                        final_wht_type='IVM',
                        preserve=False,
                        context=False)

    elif drzonly:
        ad.AstroDrizzle(
                        infiles,
                        output=outfile,
                        static=False,
                        skysub=True,
                        driz_separate=False,
                        median=False,
                        blot=False,
                        driz_cr=False,
                        driz_combine=True,
                        final_wcs=True,
                        final_refimage=refimg,
                        final_pixfrac=0.75,
                        final_fillval=0,
                        final_wht_type='IVM',
                        preserve=False,
                        context=False
                        )
    else:
        ad.AstroDrizzle(
            infiles,
            output=outfile,
            preserve=False,
            context=False,
            combine_type=ctype,
            driz_combine=True,
            final_wcs=True,
            final_refimage=refimg,
            final_pixfrac=0.75,
            final_wht_type='IVM',
            final_fillval=0
        )