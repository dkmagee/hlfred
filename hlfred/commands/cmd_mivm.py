import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import make_ivm
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Create IVM weight maps for WFC3IR images')
@click.option('--itype', default='_flt.fits', help='Input file type')
@click.option('--otype', default='_ivm.fits', help='Output file type')
@click.option('--ptask', default='ssub', help='Previous task run')
@pass_context
def cli(ctx, itype, otype, ptask):
    """
    Create IMV weight maps for WFC3IR images
    """
    dsn = ctx.dataset_name
    ctx.log('Running task %s for dataset %s', task, dsn)
    procdir = os.path.join(ctx.rundir, dsn)
    os.chdir(procdir)
    cfgf = '%s_cfg.json' % dsn
    cfg = utils.rConfig(cfgf)
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['otype'] = otype
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    iref = ctx.iref
    images = utils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    n = len(infiles)
    with click.progressbar(infiles, label='Generating sky subtracted image') as pbar:
        for i, f in enumerate(pbar):
            ctx.vlog('\n\nCreating weight map for image %s - %s of %s', f, i+1, n)
            instdet = utils.getInstDet(f)
            if instdet == 'wfc3ir':
                try:
                    make_ivm.makeweight(f, iref)
                except Exception, e:
                    utils.wConfig(cfg, cfgf)
                    print e
                    raise
    
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)