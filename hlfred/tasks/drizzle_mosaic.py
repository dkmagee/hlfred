import pyfits
import numpy as np
import shutil
from drizzlepac import astrodrizzle as ad
from stwcs.wcsutil import headerlet, HSTWCS

def drzMosaic(infiles, outfile, refimg=None, optcr=False, drzonly=False, usehlet=False, ctype='imedian'):
    """Run full AstroDrizzle"""
    if usehlet:
        for flt in infiles:
            hdrlet = flt.replace('_flt.fits', '_hlet.fits')
            headerlet.apply_headerlet_as_primary(flt, hdrlet, attach=True, archive=True, force=False, logging=False)
            
    if optcr:
        # first make median image
        print 'Creating median image...'
        ad.AstroDrizzle(infiles,
                        static=False,
                        skysub=False,
                        driz_separate=True,
                        median=True,
                        combine_type='imedian',
                        blot=False,
                        driz_cr=False,
                        driz_combine=False,
                        num_cores=4,
                        preserve=False,
                        context=False)
        shutil.move('final_med.fits', 'median.fits')
        # next make a minmed image
        print 'Creating minmed image...'
        ad.AstroDrizzle(infiles,
                        static=False,
                        skysub=False,
                        driz_separate=False,
                        median=True,
                        combine_type='iminmed',
                        blot=False,
                        driz_cr=False,
                        driz_combine=False,
                        num_cores=4,
                        preserve=False,
                        context=False)
        shutil.move('final_med.fits', 'minmed.fits')
        # make a context image
        print 'Creating combined median/minmed image...'
        ctx = pyfits.getdata('minmed.fits')*0
        for i in infiles:
            ssci = i.replace('_flt.fits', '_single_sci.fits')
            ctx += np.where(pyfits.getdata(ssci)==0, 0, 1)
        # if there are less than 5 overlaping exposures we will use minmed instead of median
        mm_mask = np.where(ctx<=5, 1, 0)
        mm = pyfits.getdata('minmed.fits')
        med = pyfits.getdata('median.fits')
        # create new final_med.fits
        fmed = mm*mm_mask + med*np.where(mm_mask==1, 0, 1)
        pyfits.writeto('final_med.fits', fmed.astype(np.float32))
        # now run blot and driz_cr
        print 'Running blot & driz_cr using combined median image...'
        ad.AstroDrizzle(infiles,
                        static=False,
                        skysub=False,
                        driz_separate=False,
                        median=False,
                        blot=True,
                        driz_cr=True,
                        driz_combine=False,
                        num_cores=4,
                        preserve=False,
                        context=False)
        # # do the final drizzle combine
        # ad.AstroDrizzle(infiles,
        #                 output=outfile,
        #                 static=True,
        #                 skysub=True,
        #                 driz_separate=False,
        #                 median=False,
        #                 blot=False,
        #                 driz_cr=False,
        #                 resetbits=None,
        #                 wcskey='DRZWCS_1',
        #                 driz_combine=True,
        #                 final_refimage=refimg,
        #                 final_pixfrac=0.75,
        #                 num_cores=4,
        #                 preserve=False,
        #                 context=False)

    # else:
    #     ad.AstroDrizzle(
    #         infiles,
    #         output=outfile,
    #         num_cores=4,
    #         preserve=False,
    #         context=False,
    #         wcskey='DRZWCS_1',
    #         combine_type=ctype,
    #         driz_combine=True,
    #         final_wcs=True,
    #         final_refimage=refimg,
    #         final_pixfrac=0.75
    #     )
    if drzonly:
        ad.AstroDrizzle(
                        infiles,
                        output=outfile,
                        static=False,
                        skysub=False,
                        driz_separate=False,
                        median=False,
                        blot=False,
                        driz_cr=False,
                        driz_combine=True,
                        wcskey='DRZWCS_1',
                        final_wcs=True,
                        final_refimage=refimg,
                        final_pixfrac=0.75,
                        resetbits=None,
                        num_cores=4,
                        preserve=False,
                        context=True
                        )