import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import apply_shift
from stwcs.wcsutil import HSTWCS
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Apply shifts to images')
@click.option('--restore', is_flag=True, help='Restore original WCS before applying offset')
@click.option('--hlet', is_flag=True, help='Create a headerlet file')
@click.option('--itype', default='_drz_sci.fits', help='Input file type')
@click.option('--otype', default='_flt.fits', help='Output file type')
@click.option('--ptask', default='saln', help='Previous task run')
@pass_context
def cli(ctx, restore, hlet, itype, otype, ptask):
    """
    Applies offsets to images computed by superalign
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
    originf = cfg['infiles']
    
    images = utils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    
    n = len(infiles)
    with click.progressbar(infiles, label='Generating catalogs for images') as pbar:
        for i, inf in enumerate(pbar):
            outf = inf.replace('_drz_sci.fits', '_flt.fits')
            ctx.vlog('\nApplying offsets image %s - %s of %s', inf, i+1, n)
            try:
                if restore:
                    apply_shift.restoreWCSdrz(inf, 0)
                    for ext in utils.sciexts[utils.getInstDet(outf)]:
                        origflt = [s for s in originf if outf in s][0]
                        restoreWCSflt(outf, origflt, ext)
                ctx.vlog('Applying offsets')
                apply_shift.applyOffset(inf, outf, hlet=hlet)
        
            except Exception, e:
                utils.wConfig(cfg, cfgf)
                print e
                raise
        
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)