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
    refcat = ctx.refcat
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['otype'] = otype
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    
    images = utils.imgList(cfg['images'], onlyacs=useacs)
    infiles = [str('%s%s' % (i, itype)) for i in images]
    refwht = None
    extref = False
    
    if refimg:
        extref = True
    
    if not refimg:
        # For now if a reference image is not given just use one of the input images
        # TODO Need to determine best image to use for the reference image from the input list if no refimg is given
        refimg = infiles.pop()
        refwht = refimg.replace('drz_sci.fits', 'drz_wht.fits')
        cfg['refimg'] = refimg 
    
    mkcat = make_catalog.MakeCat(refimg)
    if refcat:
        cfg['refcat'] = refcat
        refcat_sa = '%s_refcat.cat' % dsn
        mkcat.makeSACatExtRef(refcat, refcat_sa)
        cfg['refcat_sa'] = refcat_sa
    else:
        cfg['refcat_sa'] = refimg.replace('.fits', '.cat')
        instdet = utils.getInstDet(refimg)
        if extref:
            ctx.vlog('Generating catalog for external reference image %s', refimg)
            mkcat.makeSACat(refimg, instdet, weightfile=refwht, extref=True)
        else:
            ctx.vlog('Generating catalog for internal reference image %s', refimg)
            mkcat.makeSACat(refimg, instdet, weightfile=refwht)
    
    n = len(infiles)
    with click.progressbar(infiles, label='Generating catalogs for images') as pbar:
        for i, inf in enumerate(pbar):
            ctx.vlog('\nGenerating catalog for image %s - %s of %s', inf, i+1, n)
            whtf = inf.replace('sci', 'wht')
            instdet = utils.getInstDet(inf)
            mkcat.makeSACat(inf, instdet, weightfile=whtf)

    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)