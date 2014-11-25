import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import drizzle_image
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Drizzle single images')
@click.option('--itype', default='_flt.fits', help='Input file type')
@click.option('--otype', default='_drz.fits', help='Output file type')
@click.option('--ptask', default='init', help='Previous task run')
@pass_context
def cli(ctx, itype, otype, ptask):
    """
    Drizzles and individual image with at an orientation of 0.0 (north up)
    """
    dsn = ctx.dataset_name
    useacs = ctx.useacs
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
    images = utils.imgList(cfg['images'], onlyacs=useacs)
    infiles = [str('%s%s' % (i, itype)) for i in images]
    
    n = len(infiles)
    for i, f in enumerate(infiles):
        ctx.vlog('Drizzling image %s - %s of %s', f, i+1, n)
        try:
            drizzle_image.drzImage(f)
        except Exception, e:
            utils.wConfig(cfg, cfgf)
            print e
            raise
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)