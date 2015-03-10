import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import apply_shift
from stwcs.wcsutil import HSTWCS
import pyfits
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Apply shifts to images')
@click.option('--sin', default='superalign.in', help='Superalign input file')
# @click.option('--sout', default='offsets.cat', help='Superalign output offsets file')
@click.option('--sout', default='simplematch.out', help='Simplematch output offsets file')
@click.option('--sfile', default='shifts.cat', help='Output shift file')
@click.option('--plot/--noplot', default=True, help='Make plots for checking alignment')
@click.option('--check', is_flag=True, help='Just check alignment and do not apply offsets')
@click.option('--itype', default='_drz_sci.fits', help='Input file type')
@click.option('--otype', default='_flt.fits', help='Output file type')
@click.option('--ptask', default='saln', help='Previous task run')
@pass_context
def cli(ctx, sin, sout, sfile, plot, check, itype, otype, ptask):
    """
    Applies offsets to images computed by superalign
    """
    dsn = ctx.dataset_name
    useacs = ctx.useacs
    ctx.log('Running task %s for dataset %s', task, dsn)
    procdir = os.path.join(ctx.rundir, dsn)
    os.chdir(procdir)
    cfgf = '%s_cfg.json' % dsn
    cfg = utils.rConfig(cfgf)
    tcfg = cfg['tasks'][task] = {}
    tcfg['sin'] = sin
    tcfg['sout'] = sout
    tcfg['sfile'] = sfile
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['otype'] = otype
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    refimg = cfg['refimg']
    
    images = utils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    try:
        ctx.vlog('Computing offsets')
        ashift = apply_shift.Offsets(infiles, sin, sout, sfile, refimg)
        # ctx.vlog('Checking offsets')
        # checks = ashift.checkOffsets(plot=plot)
        # tcfg['checks'] = checks
        if not check:
            ctx.vlog('Applying offsets')
            ashift.applyOffsets()
        else:
            ctx.wlog('Offsets have not been applied')
            utils.wConfig(cfg, cfgf)
    except Exception, e:
        utils.wConfig(cfg, cfgf)
        print e
        raise
        
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)