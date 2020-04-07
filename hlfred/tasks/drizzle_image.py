from drizzlepac import astrodrizzle as ad
import os
    
def drzImage(flt, pscale, rot):
    """drzImage: Drizzle out a image with no cr-cleaning to be used for alignment"""
    ad.AstroDrizzle(
                    flt,
                    static=False,
                    skysub=True,
                    driz_separate=False,
                    median=False,
                    blot=False,
                    driz_cr=False,
                    num_cores=4,
                    preserve=False,
                    context=False,
                    final_wcs=True,
                    final_scale=pscale,
                    final_rot=rot
                    )
    return