from drizzlepac import astrodrizzle

def drzMosaic(infiles, outfile, ctype='minmed'):
    """Run full AstroDrizzle"""
    astrodrizzle.AstroDrizzle(
        infiles,
        output=outfile,
        num_cores=4,
        preserve=False,
        context=False,
        wcskey='DRZWCS_1',
        combine_type=ctype,
        final_wcs=True,
        final_rot=0
    )