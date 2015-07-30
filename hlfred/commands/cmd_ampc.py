import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import amp_correct
from stwcs.wcsutil import HSTWCS
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Correct ACS amplifier discontinuity')
@click.option('--itype', default='_flt.fits', help='Input file type')
@click.option('--otype', default='_flt.fits', help='Output file type')
@click.option('--ptask', default='apsh', help='Previous task run')
@pass_context
def cli(ctx, itype, otype, ptask):
    """
    Correct for ACS amplifier discontinuities
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
    images = utils.imgList(cfg['images'], useacs=True)
    if not images:
        print 'ampc can only be used on ACSWFC images'
    else:
        infiles = [str('%s%s' % (i, itype)) for i in images]
        n = len(infiles)
        with click.progressbar(infiles, label='Generating amplifier corrected image') as pbar:
            for i, f in enumerate(pbar):
                ctx.vlog('\n\nCorrecting image %s - %s of %s', f, i+1, n)
                try:
                    amp_correct.ampcorr(f)
                except Exception, e:
                    utils.wConfig(cfg, cfgf)
                    print e
                    raise
        
        tcfg['etime'] = ctx.dt()
        tcfg['completed'] = True
        ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
        utils.wConfig(cfg, cfgf)