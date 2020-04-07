import os, math
from numpy import where, resize, less_equal, arange
from astropy.io import fits
from hlfred.hutils import hutils

# Code basically lifted from the ACS GTO Apsis pipeline module amputil.py

def getsideMed(colist,sky,thresh):
    " return clipped median of colist"
    N = len(colist)
    newList = []
    for i in range(N):
        if okcheck(colist[i],sky,thresh):
            newList.append(colist[i])

    nn = len(newList)
    if nn < 1:
        print("Bug in amputil: amputil.getsideMed found zero-length list!")
        raise Exception("amputil: getsideMed found zero-length list!")
    
    newList.sort()
    med = (newList[int(nn/2)] + newList[int((nn-1)/2)])/2.0
    return med

def okcheck(x,mean,thresh):
    if math.fabs(x-mean) < thresh:
        return 1
    else:
        return 0

def getstep(ff, sky, sig, A1maxcol=-1, ext=0, nsig=3.5, verb=1):
    """find size of step across amplifier boundary.
    Returns a tuple:  (stepsize,error,Nr),
    where error is uncertainty and Nr tells how many values went
    into median estimate.  This one uses 3 cols on each side.
    """
    retnull = (0,-1,0)
    dat = ff[ext].data
    if len(dat.shape) != 2:
        print("amp.getstep: data array not 2-d!")
        return retnull

    if A1maxcol <= 0:
        A1maxcol = dat.shape[1]/2 - 1
        if verb:
            print("Taking amp boundary at %d/%d." %(A1maxcol,A1maxcol+1))

    ny = dat.shape[0]
    thresh = nsig*sig

    steplist=[]
    for j in range(ny):
        a1q = dat[j,int(A1maxcol-5)]   # 2042
        a1p = dat[j,int(A1maxcol-4)]   # 2043
        a1o = dat[j,int(A1maxcol-3)]   # 2044
        a1m = dat[j,int(A1maxcol-1)]   # 2046
        a2m = dat[j,int(A1maxcol+2)]   # 2049
        a2n = dat[j,int(A1maxcol+3)]   # 2050
        a2o = dat[j,int(A1maxcol+4)]   # 2051
        a2p = dat[j,int(A1maxcol+5)]   # 2052
        a2q = dat[j,int(A1maxcol+6)]   # 2053

        okLeft  = okcheck(a1m,sky,thresh) + okcheck(a1o,sky,thresh) + okcheck(a1p,sky,thresh)
        okRight = okcheck(a2m,sky,thresh) + okcheck(a2n,sky,thresh) + okcheck(a2o,sky,thresh) + okcheck(a2p,sky,thresh)
        if okLeft < 2 or okRight < 2:
            continue

        leftamp  = getsideMed([a1m,a1o,a1p,a1q],sky,thresh)
        rightamp = getsideMed([a2m,a2n,a2o,a2p,a2q],sky,thresh)
        
        step = rightamp - leftamp
        steplist.append(step)
        del step,rightamp,leftamp,a1m,a1o,a1p,a1q,a2m,a2n,a2o,a2p,a2q

    Ns = len(steplist)
    if verb:  print("Ns = "+str(Ns)+" used in median step estimate.")

    if Ns < min(500,ny/4):
        return retnull

    steplist.sort()
    medstep = (steplist[int((Ns-1)/2)] + steplist[int(Ns/2)])/2.0

    err=0.0
    for i in range(Ns):
        err += (steplist[i]-medstep)**2
    err = math.sqrt(err)/(Ns-1.0)

    return (medstep,err,Ns)

def ampcorr(flt):
    """Correct for ACSWFC/WFC3UVIS amplifier discontinuity"""
    ff = fits.open(flt, mode='update')
    for ext in [1,4]:
        sky,sig,med,msk = hutils.iterstat(ff[ext].data)
        step, err, ns = getstep(ff, sky, sig, ext=ext)
        ny, nx = ff[ext].data.shape
        colvals = resize(arange(nx),(ny,nx))
        # colvals array handy for step subtraction
        ff[ext].data = where(less_equal(colvals,(nx/2-1)), ff[ext].data+0.5*step, ff[ext].data-0.5*step)
    ff.flush()
    