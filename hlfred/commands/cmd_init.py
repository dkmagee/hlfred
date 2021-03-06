import click
from hlfred.cli import pass_context
from hlfred.hutils import hutils
from hlfred.tasks import init_image
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Initializes a HLFRED pipeline run')
@pass_context
def cli(ctx):
    """Initializes a pipeline run. The init task copies the fits files from the input dataset directory to the rundir/dataset_name.
    All input fits image should be of type flt.fits or flc.fits. For convenience the init task will copy all fits files to the dataset_name directory as type flt.fits.
    """
    cfg = {}
    dsn = cfg['dsname'] = ctx.dataset_name
    ctx.log('Initializing pipeline for dataset %s', dsn)
    cfgf = '%s_cfg.json' % dsn
    cfg['tasks'] = {}
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = None 
    tcfg['otype'] = '_flt.fits'
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    dsdir = os.path.join(ctx.dsdir, dsn)
    if not os.path.isdir(dsdir):
        ctx.elog('Input dataset %s not found! Bye.', dsdir)
        sys.exit(1)
    procdir = cfg['procdir'] = os.path.join(ctx.rundir, dsn)
    infiles = cfg['infiles'] = glob.glob(os.path.join(dsdir, '*_flt.fits')) + glob.glob(os.path.join(dsdir, '*_flc.fits'))
    cfg['refimg'] = ctx.refimg
    cfg['refcat'] = ctx.refcat
    try: 
        ctx.vlog('Creating run directory %s', dsn)
        os.makedirs(procdir)
    except OSError:
        if not os.path.isdir(procdir):
            raise
    os.chdir(procdir)
    outfiles = []
    n = len(infiles)
    with click.progressbar(infiles, label='Copying images to run directory') as pbar:
        for i, f in enumerate(pbar):
            fn = str(os.path.basename(f))
            if '_flc.fits' in fn:
                fn = fn.replace('_flc.fits', '_flt.fits')
            if not os.path.exists(fn):
                try:
                    ctx.vlog('\nCopying image %s of %s to %s', i+1, n, dsn)
                    shutil.copy(f, fn)
                    outfiles.append(fn)
                    masks = glob.glob(os.path.join(dsdir, '*.reg'))
                    if masks:
                        for m in masks:
                            shutil.copy(m, os.path.basename(m))
                except shutil.Error as e:
                    ctx.elog('Error: %s', e)
                    # eg. source or destination doesn't exist
                    raise
                except IOError as e:
                    ctx.elog('Error: %s', e.strerror)
                    raise
            else:
                outfiles.append(fn)
    images = {}
    for f in outfiles:
        ctx.vlog('Preping fits file %s for pipeline run', f)
        id, ftr = init_image.initImage(f)
        ctx.vlog('Creating footprint for fits file %s', f)
        hutils.getFootprint(f)
        if id not in list(images.keys()):
            images[id] = {}
        fid = f.split('_flt.fits')[0]
        if ftr not in list(images[id].keys()):
            images[id][ftr] = []
            images[id][ftr].append(fid)
        else:
            images[id][ftr].append(fid)
    cfg['images'] = images
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    hutils.wConfig(cfg, cfgf)
    ctx.vlog('Writing image lists')
    hutils.wImgLists(cfg)