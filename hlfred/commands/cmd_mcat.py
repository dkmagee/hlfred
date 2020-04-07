import click
from hlfred.cli import pass_context
from hlfred.hutils import hutils
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
    ctx.log('Running task %s for dataset %s', task, dsn)
    procdir = os.path.join(ctx.rundir, dsn)
    os.chdir(procdir)
    cfgf = '%s_cfg.json' % dsn
    cfg = hutils.rConfig(cfgf)
    refimg = ctx.refimg
    refcat = ctx.refcat
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['otype'] = otype
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    
    images = hutils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    refwht = None
    extref = False
    
    if refimg:
        extref = True
    
    if not refimg:
        # For now if a reference image is not given just use one of the input images
        # TODO Need to determine best image to use for the reference image from the input list if no refimg is given
        refimg = infiles[0]
        refwht = refimg.replace('drz_sci.fits', 'drz_wht.fits')
        cfg['refimg'] = refimg 
        cfg['refcat'] = refimg.replace('.fits', '.cat')
    
    mkcat = make_catalog.MakeCat(refimg)
    if refcat:
        cfg['refcat'] = refcat
        refcat_sa = '%s_refcat_sa.cat' % dsn
        cfg['refcat_sa'] = refcat_sa
        ctx.vlog('Generating catalog from external reference catalog %s', refcat)
        mkcat.makeSACatExtRef(refcat, refcat_sa)
        
    else:
        cfg['refcat'] = refimg.replace('.fits', '.cat')
        cfg['refcat_sa'] = refimg.replace('.fits', '_sa.cat')
        instdet = hutils.getInstDet(refimg)
        if extref:
            ctx.vlog('Generating catalog for external reference image %s', refimg)
            mkcat.makeCat(refimg, instdet, weightfile=refwht)
            mkcat.makeSACat(refimg, extref=True)
        else:
            ctx.vlog('Generating catalog for internal reference image %s', refimg)
            mkcat.makeCat(refimg, instdet, weightfile=refwht)
            mkcat.makeSACat(refimg)
    
    n = len(infiles)
    with click.progressbar(infiles, label='Generating catalogs for images') as pbar:
        for i, inf in enumerate(pbar):
            ctx.vlog('\nGenerating catalogs for image %s - %s of %s', inf, i+1, n)
            whtf = inf.replace('sci', 'wht')
            instdet = hutils.getInstDet(inf)
            mkcat.makeCat(inf, instdet, weightfile=whtf)
            micat = inf.replace('.fits', '_all.cat')
            omicat = inf.replace('.fits', '.cat')
            omrcat = inf.replace('.fits', '_ref.cat')
            # create new catalogs with only maching pairs
            hutils.nn_match_radec(micat, refcat, omicat, omrcat)
            mkcat.makeSACat(inf)

    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    hutils.wConfig(cfg, cfgf)