import numpy as np
from stsci import ndimage as nd
from stsci import imagestats
from astropy.io import fits
from hlfred.utils import sextractor
import numpy.random as ran
import os, glob, sys, shutil
import subprocess
from scipy.ndimage.filters import gaussian_filter
from astropy.stats import sigma_clip

# def fillInNoise(inputdata, badpixdata, segdata):
#     inputdata *= segdata
#     good = inputdata != 0
#     nonzerodata = inputdata[good]
#     nonzerodata.sort()
#     l = len(nonzerodata)
#     bkgdata = nonzerodata[int(l / 4):int(3 * l / 4)]
#     stats = imagestats.ImageStats(bkgdata, fields='stddev')
#     sigma = stats.stddev / 2.
#     noise = ran.standard_normal(inputdata.shape)
#     noise = (noise.astype(np.float32) * sigma + stats.mean)
#     segn = noise * np.where(segdata == 0, 1, 0)
#     bpn = noise * np.where(badpixdata == 0, 1, 0)
#     outputdata = inputdata.astype(np.float32) + segn + bpn
#     return outputdata

# def flatten(ffin, backsize=32):
#     if not os.path.exists('flt_orig'):
#         os.mkdir('flt_orig')
#     shutil.copy(ffin, 'flt_orig')
#     newf = fits.open(ffin, mode='update')
#     bkgimg = ffin.replace('.fits', '_bkg.fits')
#     # zero out bad pixels using the DQ array
#     bpm = np.where(fits.getdata(ffin, ext=3) == 0, 1, 0)
#     sdata = newf[1].data*bpm
#     fits.writeto(bkgimg, sdata, clobber=True)
#     skyName = ffin.replace('flt.fits', 'sky.fits')
#     segName = ffin.replace('flt.fits', 'seg.fits')
#
#     # create segmentation image for masking objects
#     sex = sextractor.SExtractor()
#     sex.config['CATALOG_TYPE'] = 'NONE'
#     sex.config['WEIGHT_TYPE'] = 'NONE'
#     sex.config['BACK_TYPE'] = 'AUTO'
#     sex.config['BACK_SIZE'] = backsize
#     sex.config['BACK_FILTERSIZE'] = 3
#     sex.config['CHECKIMAGE_TYPE'] = 'SEGMENTATION'
#     sex.config['CHECKIMAGE_NAME'] = segName
#     sex.run(bkgimg)
#
#     # clean up segmentation config
#     sex.clean(config=True, catalog=True, check=False)
#
#     # mask out objects and bad pixels and fill with noise
#     seg =  np.where(fits.getdata(segName) == 0, 1, 0)
#     bkg_data = fillInNoise(sdata, bpm, seg)
#     with fits.open(bkgimg, mode='update') as bkg:
#         bkg[0].data = bkg_data
#
#     # Create background image for sky subtraction
#     sex = sextractor.SExtractor()
#     sex.config['CATALOG_TYPE'] = 'NONE'
#     sex.config['WEIGHT_TYPE'] = 'NONE'
#     sex.config['BACK_TYPE'] = 'AUTO'
#     sex.config['BACK_SIZE'] = backsize
#     sex.config['BACK_FILTERSIZE'] = 3
#     sex.config['CHECKIMAGE_TYPE'] = 'BACKGROUND'
#     sex.config['CHECKIMAGE_NAME'] = skyName
#     sex.run(bkgimg)
#
#     # clean up background config
#     sex.clean(config=True, catalog=True, check=False)
#
#     # do the sky subtraction using the sextractor background image
#     sky = fits.getdata(skyName)
#     newf[1].data -= sky
#     medbkg = np.median(sky)
#     print 'final sky value: ', medbkg
#     newf[1].header['BKG'] = medbkg
#     newf[1].data += medbkg
#     print 'writing flattened image', ffin
#     newf.flush()
#     newf.close()

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

def flatten(ffin, backsize=64):
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
        clip2 = sigma_clip(bkgdata2, sigma=3)
        clip10 = sigma_clip(bkgdata10, sigma=3)
        bkg[1].data = np.where(clip2.mask.astype(np.int) == 0, 1, 0) * np.where(clip10.mask.astype(np.int) == 0, 1, 0) * bpm 
        bkg.writeto(mskimg, clobber=True)

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
        print 'final sky value: ', medbkg
        f[1].header.update('BKG', medbkg)
        f[1].data = flattened + medbkg
        print 'writing flattened image', out
        f.writeto(out, clobber=True)
        f.close()
    # move background image data in to bkg directory
    if not os.path.exists('bkg'):
        os.mkdir('bkg')
    shutil.move(ffin, 'bkg')
    shutil.move(bkgimg, 'bkg')
    shutil.move(mskimg, 'bkg')
    shutil.move(skyimg, 'bkg')
    shutil.move(out, ffin)

# def flatten(ffin, backsize=32):
#     outname = ffin.replace('flt.fits', 'ftn.fits')
#     newf = fits.open(ffin)
#     d = newf[1].data
#     h = newf[1].header
#     bkgimg = ffin.replace('.fits', '_bkg.fits')
#     # zero out bad pixels using the DQ array
#     bpm = np.where(fits.getdata(ffin, ext=3) == 0, 1, 0)
#     sdata = d*bpm
#     fits.writeto(bkgimg, sdata, h, clobber=True)
#     skyimg = ffin.replace('flt.fits', 'sky.fits')
#     segimg = ffin.replace('flt.fits', 'seg.fits')
#
#     # create segmentation image for masking objects
#     sex = sextractor.SExtractor()
#     sex.config['CATALOG_TYPE'] = 'NONE'
#     sex.config['WEIGHT_TYPE'] = 'NONE'
#     sex.config['BACK_TYPE'] = 'AUTO'
#     sex.config['BACK_SIZE'] = backsize
#     sex.config['BACK_FILTERSIZE'] = 3
#     sex.config['CHECKIMAGE_TYPE'] = 'SEGMENTATION'
#     sex.config['CHECKIMAGE_NAME'] = segimg
#     sex.run(bkgimg)
#
#     # clean up segmentation config
#     sex.clean(config=True, catalog=True, check=False)
#
#     # mask out objects and bad pixels and fill with noise
#     seg =  np.where(fits.getdata(segimg) == 0, 1, 0)
#     bkg_data = fillInNoise(sdata, bpm, seg)
#     with fits.open(bkgimg, mode='update') as bkg:
#         bkg[0].data = bkg_data
#
#     # Create background image for sky subtraction
#     sex = sextractor.SExtractor()
#     sex.config['CATALOG_TYPE'] = 'NONE'
#     sex.config['WEIGHT_TYPE'] = 'NONE'
#     sex.config['BACK_TYPE'] = 'AUTO'
#     sex.config['BACK_SIZE'] = backsize
#     sex.config['BACK_FILTERSIZE'] = 3
#     sex.config['CHECKIMAGE_TYPE'] = 'BACKGROUND'
#     sex.config['CHECKIMAGE_NAME'] = skyimg
#     sex.run(bkgimg)
#
#     # clean up background config
#     sex.clean(config=True, catalog=True, check=False)
#
#     # do the sky subtraction using the sextractor background image
#     sky = fits.getdata(skyimg)
#     flattened = d - sky
#     medbkg = np.median(sky)
#     print 'final sky value: ', medbkg
#     newf[1].header.update('BKG', medbkg)
#     newf[1].data = flattened + medbkg
#     print 'writing flattened image', outname
#     newf.writeto(outname, clobber=True)
#     newf.close()
#
#     # move background image data in to bkg directory
#     if not os.path.exists('bkg'):
#         os.mkdir('bkg')
#     shutil.move(ffin, 'bkg')
#     shutil.move(bkgimg, 'bkg')
#     # shutil.move(segimg, 'bkg')
#     shutil.move(mskimg, 'bkg')
#     shutil.move(skyimg, 'bkg')
#     shutil.move(outname, ffin)
    
    # confName = 'default.sex'
    # if not os.path.exists(confName):
    #     fid = open(confName,'w')
    #     lines = """
    #     CATALOG_TYPE     NONE     # NONE,ASCII,ASCII_HEAD, ASCII_SKYCAT,\n
    #     BACK_TYPE        AUTO           # AUTO or MANUAL \n
    #     BACK_SIZE        32             # Background mesh: <size> or <width>,<height>\n
    #     BACK_FILTERSIZE  3              # Background filter: <size> or <width>,<height>\n
    #     CHECKIMAGE_TYPE  BACKGROUND     # can be NONE, BACKGROUND, BACKGROUND_RMS,\n
    #     CHECKIMAGE_NAME  check.fits     # Filename for the check-image
    #     """
    #
    #     fid.write(lines)
    #     fid.close()
    #
    #     parf = open('default.param','w')
    #     parf.write('NUMBER')
    #     parf.close()
    #
    #     parf = open('default.conv','w')
    #     parf.write("CONV NORM\n# 3x3 ``all-ground'' convolution mask with FWHM = 2 pixels.\n1 2 1\n2 4 2\n1 2 1")
    #     parf.close()
    #
    # # create a segmentation image
    # cmd = 'sex -c %s -CHECKIMAGE_NAME %s -CHECKIMAGE_TYPE SEGMENTATION %s'%(confName, segName, bkgimg)
    # print cmd
    # spc = subprocess.call(cmd, shell=True)
    #
    # # mask out objects and bad pixels and fill with noise
    # seg =  nd.binary_fill_holes(np.where(fits.getdata(segName) == 0, 1, 0))
    # bkg_data = fillInNoise(sdata, bpm, seg)
    # with fits.open(bkgimg, mode='update') as bkg:
    #     bkg[0].data = bkg_data
    #
    # # create the sky background image
    # cmd = 'sex -c %s -CHECKIMAGE_NAME %s %s'%(confName, skyName, bkgimg)
    # print cmd
    # spc = subprocess.call(cmd, shell=True)
    # sky = fits.getdata(skyName)
    # flattened = d - sky
    # medbkg = np.median(sky)
    # print 'final sky value: ', medbkg
    # newf[1].header.update('BKG', medbkg)
    # newf[1].data = flattened + medbkg
    # print 'writing flattened image', outname
    # newf.writeto(outname, clobber=True)
    # newf.close()
    #
    # shutil.move(ffin, 'orig_%s' % ffin)
    # os.symlink(outname, ffin)

    