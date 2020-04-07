import numpy as np
from stsci import ndimage as nd
from stsci import imagestats
from astropy.io import fits
from hlfred.hutils import sextractor
import numpy.random as ran
import os, glob, sys, shutil
import subprocess
from scipy.ndimage.filters import gaussian_filter
from astropy.stats import sigma_clip

def fillInNoise(inputdata, mskdata):
    inputdata *= mskdata
    good = inputdata != 0
    nonzerodata = inputdata[good]
    nonzerodata.sort()
    l = len(nonzerodata)
    bkgdata = nonzerodata[int(l / 4):int(3 * l / 4)]
    stats = imagestats.ImageStats(bkgdata, fields='stddev')
    sigma = stats.stddev / 2.
    noise = ran.standard_normal(inputdata.shape)
    noise = (noise.astype(np.float32) * sigma + stats.mean)
    mskn = noise * np.where(mskdata == 0, 1, 0)
    outputdata = inputdata.astype(np.float32) + mskn
    return outputdata

def flatten(ffin, backsize=128):
    # bad pixels using the DQ array
    bpm = np.where(fits.getdata(ffin, ext=3) == 0, 1, 0)
    bkgimg = ffin.replace('.fits', '_bkg.fits')
    shutil.copy(ffin, bkgimg)
    skyimg = ffin.replace('flt.fits', 'sky.fits')
    mskimg = ffin.replace('flt.fits', 'msk.fits')
    with fits.open(bkgimg) as bkg:
        medbkg = np.median(bkg[1].data)
        bkgdata2 = gaussian_filter(bkg[1].data - medbkg, 2)
        bkgdata10 = gaussian_filter(bkg[1].data - medbkg, 10)
        clip2 = sigma_clip(bkgdata2, sigma=5)
        clip10 = sigma_clip(bkgdata10, sigma=5)
        bkg[1].data = np.where(clip2.mask.astype(np.int) == 0, 1, 0) * np.where(clip10.mask.astype(np.int) == 0, 1, 0) * bpm
        # bkg[1].data = np.where(clip2.mask.astype(np.int) == 0, 1, 0) * bpm 
        bkg.writeto(mskimg, overwrite=True)

    # mask out objects and bad pixels and fill with noise
    msk = fits.getdata(mskimg)
    bkg_data = fillInNoise(fits.getdata(bkgimg), msk)
    with fits.open(bkgimg, mode='update') as bkg:
        bkg[0].data = bkg_data

    # Create background image for sky subtraction
    sex = sextractor.SExtractor()
    sex.config['CATALOG_TYPE'] = 'NONE'
    sex.config['WEIGHT_TYPE'] = 'NONE'
    sex.config['BACK_TYPE'] = 'AUTO'
    sex.config['BACK_SIZE'] = backsize
    sex.config['BACK_FILTERSIZE'] = 3
    sex.config['CHECKIMAGE_TYPE'] = 'BACKGROUND'
    sex.config['CHECKIMAGE_NAME'] = skyimg
    sex.run(bkgimg)

    # clean up background config
    sex.clean(config=True, catalog=True, check=False)

    # do the sky subtraction using the sextractor background image
    sky = fits.getdata(skyimg)
    out = ffin.replace('flt.fits', 'ftn.fits')
    with fits.open(ffin) as f:
        flattened = f[1].data - sky
        medbkg = np.median(sky)
        print('final sky value: ', medbkg)
        f[1].header['BKG'] = (medbkg, 'HLFRED Background')
        f[1].data = flattened + medbkg
        print('writing flattened image', out)
        f.writeto(out, overwrite=True)
        f.close()
    # move background image data in to bkg directory
    if not os.path.exists('bkg'):
        os.mkdir('bkg')
    shutil.move(ffin, 'bkg')
    shutil.move(bkgimg, 'bkg')
    shutil.move(mskimg, 'bkg')
    shutil.move(skyimg, 'bkg')
    shutil.move(out, ffin)
