import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import drizzle_mosaic
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Drizzle final mosaic')
@click.option('--optcr', is_flag=True, help='Run with 2-pass cr-rejection (minmed & median)')
@click.option('--drzonly', is_flag=True, help='Only run astrodrizzle final combine')
@click.option('--usehlet', is_flag=True, help='Use headerlets for updating WCS')
@click.option('--ctype', default='imedian', help='Type of combine operation')
@click.option('--itype', default='_flt.fits', help='Input file type')
@click.option('--ofile', help='Output file (defaults to dsname_instdet_filter)')
@click.option('--ptask', default='apsh', help='Previous task run')
@pass_context
def cli(ctx, optcr, drzonly, usehlet, ctype, itype, ofile, ptask):
    """
    Drizzles final mosaic for each filter
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
    tcfg['ofile'] = ofile
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    
    for instdet, data in cfg['images'].iteritems():
        for fltr, images in data.iteritems():
            outfile = '%s_%s_%s' % (dsn, instdet, fltr.lower())
            infiles = [str('%s%s' % (i, itype)) for i in images]
            ctx.vlog('Drizzling mosaic %s', outfile)
            try:
                if cfg['refimg']:
                    refimg = str(cfg['refimg'])
                    drizzle_mosaic.drzMosaic(infiles, outfile, refimg=refimg, optcr=optcr, drzonly=drzonly, usehlet=usehlet, ctype=ctype)
                else:
                    drizzle_mosaic.drzMosaic(infiles, outfile, optcr=optcr, drzonly=drzonly, usehlet=usehlet, ctype=ctype)
            except Exception, e:
                utils.wConfig(cfg, cfgf)
                print e
                raise
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)