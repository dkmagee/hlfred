import click
from hlfred.cli import pass_context
from hlfred.utils import utils
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
    try: 
        ctx.vlog('Creating run directory %s', dsn)
        os.makedirs(procdir)
    except OSError:
        if not os.path.isdir(procdir):
            raise
    os.chdir(procdir)
    outfiles = []
    for f in infiles:
        fn = os.path.basename(f)
        if '_flc.fits' in fn:
            fn = fn.replace('_flc.fits', '_flt.fits')
        if not os.path.exists(fn):
            try:
                ctx.vlog('Copying %s to %s', f, dsn+'/'+fn)
                shutil.copy(f, fn)
                outfiles.append(fn)
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
        if id not in images.keys():
            images[id] = {}
        fid = f.split('_flt.fits')[0]
        if ftr not in images[id].keys():
            images[id][ftr] = []
            images[id][ftr].append(fid)
        else:
            images[id][ftr].append(fid)
    cfg['images'] = images
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)