import shutil
from drizzlepac import astrodrizzle
import pyfits
import lacosmicx

def runCosmic(image):
    exts = [1,4]
    img = pyfits.open(image, mode='update')
    for ext in exts:
        print 'CR-cleaning %s extension %s' % (image, ext)
        data = img[ext].data
        mask, clean = lacosmicx.lacosmicx(data, inmask=None, sigclip=4.5, sigfrac=0.3, objlim=2.5, gain=1.0, readnoise=6.5, satlevel=65536.0, pssl=0.0, niter=8,
                         sepmed=True, cleantype='medmask', fsmode='convolve', psfmodel='gauss', psffwhm=2.5, psfsize=7, psfk=None, psfbeta=4.765, verbose=False, retclean=True)
        img[ext].data = clean
    img.flush()
    img.close()
    return
    
def drzImage(flt, pscale, rot):
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
                                final_scale=pscale,
                                final_rot=rot
                        )
    
    return