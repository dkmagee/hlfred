import click
from hlfred.cli import pass_context
from hlfred.utils import utils
from hlfred.tasks import super_align
from stwcs.wcsutil import HSTWCS
from astropy.io import fits
import sys, os, shutil, glob

task = os.path.basename(__name__).split('.')[-1][4:]

def find_executable(executable):
    path = os.environ['PATH']
    paths = path.split(os.pathsep)
    for p in paths:
        f = os.path.join(p, executable)
        if os.path.isfile(f):
            return f

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
    tcfg = cfg['tasks'][task] = {}
    tcfg['ptask'] = ptask
    tcfg['itype'] = itype
    tcfg['ofile'] = cfg['sfile'] = ofile
    tcfg['stime'] = ctx.dt()
    tcfg['completed'] = False
    
    images = utils.imgList(cfg['images'])
    infiles = [str('%s%s' % (i, itype)) for i in images]
    refimg = cfg['refimg']
    refcat = cfg['refcat']
    refcat_sa = cfg['refcat_sa']
    refwcs = HSTWCS(fits.open(refimg))
    
    sa_hlf = find_executable('superalign_hlfred')
    if not sa_hlf:
        ctx.elog('Unable to find "superalign_hlfred" executable. Make sure it is in your PATH.')
        sys.exit(1)
    
    ctx.vlog('Grouping images by visit for alignment')
    visits = set([i[:6] for i in infiles])
    vdata = {}
    for v in visits:
        vdata[v] = []
        for e in infiles:
            if e[:6] == v:
                vdata[v].append(e)
    
    # Run superalign on all visits
    ctx.vlog('Generating the superalign input')
    with open('superalign_failed_visits.txt', 'w') as sfv:
        for visit, inf in vdata.iteritems():
            super_align.makeSAin(visit, inf, refwcs, refcat_sa)
            try:
                sa_cmd = '%s %s_superalign.in %s_sources.cat %s_offsets.cat' % (sa_hlf, visit, visit, visit)
                ctx.vlog('Running: %s', sa_cmd)
                ecode = super_align.runSuperAlign(sa_cmd)
                if ecode > 0:
                    print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
                    print 'Superalign FAILED on %s' % visit
                    print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
                    sfv.write('%s\n' % visit)
                else:
                    print '----------------------------------'
                    print 'Completed superalign on %s' % visit
                    print '----------------------------------'
                super_align.makeSourceCat(visit, refwcs)
                ctx.vlog('Running simplematch')
                super_align.runSimpleMatch(visit)
                ctx.vlog('Running applyshifts')
                super_align.applyShiftsSA(visit)

            except Exception, e:
                sfv.close()
                utils.wConfig(cfg, cfgf)
                print e
                raise
    
    # Refine the shifts with MCMC
    ctx.vlog('Refining shifts...')
    with open('mcmc_shifts.txt', 'a') as ms:
        for drz in infiles:
            super_align.stars2cat(drz, refwcs)
        for visit, inf in vdata.iteritems():
            ctx.vlog('Generating matched catalogs for visit %s', visit)
            for c1 in glob.glob('%s???_drz_sci_sa.cat.stars.cat' % visit):
                c2 = refcat
                c1m = c1.replace('.cat.stars.cat', '_match.cat')
                c2m = c1.replace('.cat.stars.cat', '_ref_match.cat')
                super_align.nn_match(c1, c2, refwcs, c1m, c2m)
        for drz in infiles:
            with fits.open(drz) as hdu:
                wn = hdu[0].header['wcsname']
            if wn == 'DRZWCS_1':
                ctx.vlog('Refining shifts for %s' % drz)
                offset = super_align.refineShiftMCMC(drz)
                dxp, dyp, dtp = offset
                ms.write('%s %.3f %.3f %.3f\n' % (drz, dxp, dyp, dtp))
                
    tcfg['etime'] = ctx.dt()
    tcfg['completed'] = True
    ctx.vlog('Writing configuration file %s for %s task', cfgf, task)
    utils.wConfig(cfg, cfgf)