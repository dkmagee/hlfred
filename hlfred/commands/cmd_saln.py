import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import super_align
from stwcs.wcsutil import HSTWCS
import pyfits
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Run superalign on alignment catalogs')
@click.option('--itype', default='_drz_sci.fits', help='Input file type')
@click.option('--ofile', default='offsets.cat', help='Output file')
@click.option('--ptask', default='mcat', help='Previous task run')
@pass_context
def cli(ctx, itype, ofile, ptask):
    """
    Runs superalign on catalogs for alignment
    """
    dsn = ctx.dataset_name
    ctx.log('Running task %s for dataset %s', task, dsn)
    procdir = os.path.join(ctx.rundir, dsn)
    os.chdir(procdir)
    cfgf = '%s_cfg.json' % dsn
    cfg = utils.rConfig(cfgf)
    refimg = ctx.refimg
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['ofile'] = cfg['sfile'] = ofile
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    
    images = utils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    refimg = cfg['refimg']
    refwcs = HSTWCS(pyfits.open(refimg))
    ctx.vlog('Generating the superalign input')
    refcat = refimg.replace('.fits', '.cat')
    super_align.makeSAin(infiles, refwcs, refcat)
    cmd = 'superalign superalign.in sources.cat %s' % ofile
    ctx.vlog('Running: %s', cmd)

    try:
        super_align.runSuperAlign(cmd)
    except Exception, e:
        utils.wConfig(cfg, cfgf)
        print e
        raise

    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)