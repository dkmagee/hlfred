import shutil
from drizzlepac import astrodrizzle as ad
import pyfits
    
def drzImage(flt, pscale, rot):
    """drzImage: Drizzle out a image with an orientation of 0 (north up) and no cr-cleaning="""
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
                    final_rot=rot,
                    resetbits=None
                    )
    
    return