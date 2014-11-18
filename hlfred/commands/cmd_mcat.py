import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import make_catalog
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

@click.command(task, short_help='Generate object catalogs for alignment')
@click.option('--itype', default='_drz_sci.fits', help='Input file type')
@click.option('--otype', default='_drz_sci.cat', help='Output file type')
@click.option('--ptask', default='drzi', help='Previous task run')
@pass_context
def cli(ctx, itype, otype, ptask):
    """
    Generates object catalogs for each input image sutable for alignment
    """
    dsn = ctx.dataset_name
    useacs = ctx.useacs
    ctx.log('Running task %s for dataset %s', task, dsn)
    procdir = os.path.join(ctx.rundir, dsn)
    os.chdir(procdir)
    cfgf = '%s_cfg.json' % dsn
    cfg = utils.rConfig(cfgf)
    refimg = ctx.refimg
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['otype'] = otype
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    
    images = utils.imgList(cfg['images'], onlyacs=useacs)
    infiles = [str('%s%s' % (i, itype)) for i in images]
    if not refimg:
        # For now if a reference image is not given just use the first image
        # TODO Need to determine best image to use for the reference image from the input list if no refimg is given
        refimg = infiles[0]
        cfg['refimg'] = refimg
    mkcat = make_catalog.MakeCat(refimg)
    for inf in infiles:
        ctx.vlog('Generating catalog for image %s', inf)
        whtf = inf.replace('sci', 'wht')
        instdet = utils.getInstDet(inf)
        mkcat.makeSACat(inf, instdet, weightfile=whtf)
    
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)