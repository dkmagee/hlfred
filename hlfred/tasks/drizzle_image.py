from drizzlepac import astrodrizzle

def drzImage(flt):
    """drzImage: Drizzle out a image with an orientation of 0 (north up) and no cr-cleaning="""
    astrodrizzle.AstroDrizzle(  
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
                                final_rot=0.0
                            )