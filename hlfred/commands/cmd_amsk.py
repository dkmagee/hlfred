import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import apply_mask
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Apply masks to images')
@click.option('--itype', default='_flt.fits', help='Input file type')
@click.option('--otype', default='_flt.fits', help='Output file type')
@click.option('--ptask', default='init', help='Previous task run')
@pass_context
def cli(ctx, itype, otype, ptask):
    """
    Applies mask to images
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
    
    images = utils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    
    n = len(infiles)
    with click.progressbar(infiles, label='Generating masks for images') as pbar:
        for i, f in enumerate(pbar):
            ctx.vlog('\n\nChecking masks for image %s - %s of %s', f, i+1, n)
            masks = glob.glob('%s*.reg' % f.replace('.fits', ''))
            if masks:
                try:
                    for m in masks:
                        if 'SCI' in m:
                            # ACSWFC and WFC3UV
                            dq_ext = int(m.split('.reg')[0][-1])
                        else:
                            # WFC3IR
                            dq_ext = 3
                        ctx.vlog('Applying mask to %s - DQ extention %s', f, dq_ext)
                        apply_mask.applymask(f, m, dq_ext)
                except Exception, e:
                    utils.wConfig(cfg, cfgf)
                    print e
                    raise
            else:
                ctx.vlog('No masks found for %s', f)
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)