
import numpy as np
from itertools import product
from scipy.spatial import cKDTree
from pymc import deterministic, Uniform, Cauchy
from pymc.MCMC import MCMC

"""
This code was lifted directly from Mira Mechtley HIPPIES Data Reduction Pipeline
https://github.com/mmechtley/HIPPIES_Pipeline/blob/master/pipeline/CatalogTools.py
"""

def findOffsetMCMC(coords1, coords2, maxShift=(20, 20, 0), rotOrigin=(0, 0),
                   precision=0.01, visualize=False, **kwargs):
    """
    Find offset between two sets of coordinates using MCMC. Assumes error in
    the determination of individual points is normally distributed (and
    estimates this error).
    The nearest-neighbor determination employed has the benefit of being
    symmetric, i.e., findOffsetMCMC(c1,c2) = -findOffsetMCMC(c2,c1)
    Additional kwargs are passed to pymc's MCMC.sample, so arguments like iter,
    burn, thin, and tune_interval may also be supplied.

    :param coords1: First (reference) set of coordinates (Nx2)
    :param coords2: Second (transformed) set of coordinates (Mx2)
    :param maxShift: Maximum offsets in x,y,theta. Theta is specified in
                     degrees. If theta is 0 or omitted, no rotation is
                     calculated or returned.
    :param rotOrigin: Origin for rotations (usually center of image).
    :param precision: Estimated precision of x,y
    :param visualize: Show plots when finished
    :return: 2-tuple of shift, xyError.
             shift is an ndarray of x,y,[theta], the amount coords2 is shifted
             with respect to coords1. xyError is a floating point scalar, the
             estimated sum of the measurement errors in coords1 and coords2,
             ie. sqrt( err(coords1)**2 + err(coords2)**2 )
    """
    ## Set some default values for MCMC sampler, if not provided
    kwargs.setdefault('iter', 30000)
    kwargs.setdefault('burn', 5000)

    coords1Over, coords2Over = _overlappedCoords(coords1, coords2, maxShift)

    ## Create kd trees for fast coordinate matching
    kd1 = cKDTree(coords1Over)
    kd2 = cKDTree(coords2Over)

    ## Set up MCMC sampler, sample
    sampler = MCMC(_offsetModel(kd1, kd2, maxShift, rotOrigin,
                                precision))
    sampler.sample(**kwargs)
    sampler.db.close()

    ## Get output statistics
    stats = sampler.stats()
    shift = -stats['shift']['mean']
    shiftErr = stats['shift']['standard deviation']
    xyError = stats['xyerror']['mean']

    ## Show plots
    if visualize:
        c1Xform, c2Xform = _transformCoords(kd1.data, kd2.data,
                                            -shift, rotOrigin)
        d12, ind12 = kd1.query(c2Xform)
        d21, ind21 = kd2.query(c1Xform)

        xresid, yresid = np.hsplit((c2Xform - kd1.data[ind12]), 2)

        _plotPoints(kd1.data, c2Xform, ind12, ind21)

        if xresid.size > 1:
            _plotResidual(xresid, yresid, xyError)
            _plotChain(sampler.db.trace('shift')[:][:, 0],
                       sampler.db.trace('shift')[:][:, 1])

    return shift, xyError


def _offsetModel(kd1, kd2, maxShift, rotOrigin, precision):
    """
    Factory function to return MCMC model for coordinate offset calculation

    :param kd1:
    :param kd2:
    :param maxShift:
    :param rotOrigin:
    :param precision:
    :return:
    """
    rotOrigin = np.array(rotOrigin)
    maxShift = np.array(maxShift)

    shift = Uniform('shift', lower=-maxShift, upper=maxShift)
    xyError = Uniform('xyerror', lower=precision / 1000, upper=precision * 1000)

    @deterministic(plot=False)
    def coordResiduals(kd1=kd1, kd2=kd2, shift=shift):
        c1Xform, c2Xform = _transformCoords(kd1.data, kd2.data,
                                            shift, rotOrigin)
        d12, ind1near2 = kd1.query(c2Xform)
        d21, ind2near1 = kd2.query(c1Xform)

        msk1 = ind1near2[ind2near1] == np.arange(ind2near1.size)

        resid = c1Xform - kd2.data[ind2near1]
        resid[~msk1] = 0
        return resid

    opt = Cauchy('data', value=np.zeros_like(kd1.data),
                 alpha=coordResiduals, beta=xyError, observed=True)

    return [shift, xyError, coordResiduals, opt]


def _rotMatrix(theta=0.0, unit='radians'):
    if unit == 'degrees':
        theta = np.deg2rad(theta)
    st, ct = np.sin(theta), np.cos(theta)
    return np.array([[ct, -st], [st, ct]])


def _transformCoords(coords1, coords2, shift, rotOrigin=(0, 0)):
    """
    Transform two sets of coordinates using the given shift and origin.
    coords1 is transformed by subtracting translation and then appyling inverse
    rotation. coords2 is transformed by applying forward rotation and then
    adding the translation.

    :param coords1: First set of coordinates (Nx2)
    :param coords2: Second set of coordinates (Mx2)
    :param shift: Array-like, first two components are x,y shifts, third
                  (optional) is rotation in degrees.
    :param rotOrigin: Origin around which to rotate
    :return: c1Xform, c2Xform, transformed versions of coords1 and coords2
    """
    c1Xform = coords1 - shift[0:2] - rotOrigin
    c2Xform = coords2 - rotOrigin
    if len(shift) > 2:
        rotMat = _rotMatrix(shift[2], unit='degrees')
        c2Xform = np.dot(c2Xform, rotMat.T) ## Right multiply, so use inv
        c1Xform = np.dot(c1Xform, rotMat)
    c1Xform += rotOrigin
    c2Xform += shift[0:2] + rotOrigin
    return c1Xform, c2Xform


def _overlappedCoords(coords1, coords2, maxShift):
    minx = max(np.min(coords1[:, 0]), np.min(coords2[:, 0])) - maxShift[0]
    maxx = min(np.max(coords1[:, 0]), np.max(coords2[:, 0])) + maxShift[0]
    miny = max(np.min(coords1[:, 1]), np.min(coords2[:, 1])) - maxShift[1]
    maxy = min(np.max(coords1[:, 1]), np.max(coords2[:, 1])) + maxShift[1]

    def bboxClip(coo):
        return coo[(coo[:, 0] > minx) & (coo[:, 0] < maxx) &
                   (coo[:, 1] > miny) & (coo[:, 1] < maxy)]

    return bboxClip(coords1), bboxClip(coords2)

## Minimize the distance between two data sets
## TODO: Make it work correctly for any number of coordinate dimensions
def findOffset(coords1, coords2, rotation=False, rotOrigin=(0, 0),
               iterations=200,
               precision=0.01, maxOffset=100.0, maxRot=5.0):
    """
    Calculate the offset required to match coords2 with coords1

    :param coords1: numpy 2d array, 1st set of coordinate tuples
    :param coords2: numpy 2d array, 2nd set of coordinate tuples
    :param iterations: Maximum number of steps for algorithm
    :param maxOffset: Maximum offset we expect for the two coordinate sets
    :return: n-dimensional coordinate offset of coords2 with respect to coords1
    """
    bestDist = gridLim = maxOffset
    rotLim = maxRot
    if rotation:
        bestOffset = np.zeros((3, 1))
    else:
        bestOffset = np.zeros((2, 1))

    ## Create KD tree for first set of coordinates, since they don't change
    kd1 = cKDTree(coords1)

    for step in range(0, iterations):
        ## Make grid
        ## TODO: Make faster using only numpy? Especially with rotation, this is SLOW
        gridx = np.linspace(bestOffset[0] - gridLim, bestOffset[0] + gridLim,
                            10)
        gridy = np.linspace(bestOffset[1] - gridLim, bestOffset[1] + gridLim,
                            10)
        if rotation:
            gridt = np.linspace(bestOffset[2] - rotLim, bestOffset[2] + rotLim,
                                10)
            grid = product(gridx, gridy, gridt)
        else:
            grid = product(gridx, gridy)

        ## Iterate through grid
        gridBestOffset = bestOffset
        gridBestDist = bestDist

        for offset in grid:
            coords2Off = coords2 - rotOrigin
            if rotation:
                rotMat = _rotMatrix(offset[2], unit='degrees')
                coords2Off = np.dot(rotMat, coords2Off.T)
                coords2Off = coords2Off.T + rotOrigin
                coords2Off += offset[0:2]
            else:
                coords2Off += offset

            ## Create KD Tree for second coordinate set, cross-check closest points
            ## I guess this is faster than calculating the whole distance matrix?
            kd2 = cKDTree(coords2Off)
            dists12, inds12 = kd1.query(coords2Off)
            dists21, inds21 = kd2.query(coords1)

            common = np.intersect1d(dists12, dists21)


            ## TODO: Can we do this without median? Requires sorting
            m = np.median(common)
            s = np.std(common)

            dist = np.median(common[
                common < m + s])    ## Clip values > 1 sigma on the right side

            if dist < gridBestDist:
                gridBestOffset = offset
                gridBestDist = dist
        ## If this grid failed to provide a better offset, re-run with a finer grid
        if gridBestDist == bestDist:
            gridLim *= 0.5
            rotLim *= 0.5

        ## Early out for convergence when required precision is reached
        if gridLim * 0.2 < precision: ## width of a grid cell. same as gridLim*2/10 cells
            break

        if gridBestDist < bestDist:
            bestDist = gridBestDist
            gridLim = 2 * gridBestDist
            bestOffset = gridBestOffset

    return -np.array(bestOffset)


def _plotPoints(coords1, c2Xform, indexes2in1, indexes1in2):
    from matplotlib import pyplot
    from matplotlib.collections import LineCollection

    msk = indexes1in2[indexes2in1] == np.arange(indexes2in1.size)
    pyplot.figure()
    pyplot.scatter(coords1[:, 0], coords1[:, 1], c='SeaGreen', alpha=0.5)
    pyplot.scatter(c2Xform[:, 0], c2Xform[:, 1], c='Tomato', alpha=0.5)
    lc = LineCollection(list(zip(coords1[indexes2in1[msk]], c2Xform[msk])),
                        colors='black')
    pyplot.gca().add_collection(lc)
    pyplot.show()


def _plotResidual(xResid, yResid, xyError, nbins=50, color='RoyalBlue'):
    from matplotlib import pyplot
    from matplotlib.patches import Ellipse
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    from matplotlib.patheffects import withStroke

    medianxy = np.median(xResid), np.median(yResid)

    ## Scatter plot of residuals, and circle showing dispersion
    pyplot.figure()
    axScatter = pyplot.subplot(111)
    pyplot.scatter(xResid, yResid, c=color)
    ell = Ellipse((0, 0), 2 * xyError, 2 * xyError, 0,
                  fc=color, alpha=0.2, zorder=-1)
    axScatter.add_patch(ell)

    ## Set up histogram axes, prettify labels and such
    axScatter.set_aspect(1.)
    divider = make_axes_locatable(axScatter)
    axHistx = divider.append_axes("top", 1.2, pad=0.2, sharex=axScatter)
    axHisty = divider.append_axes("right", 1.2, pad=0.2, sharey=axScatter)
    axScatter.ticklabel_format(style='sci', scilimits=(-2, 2), axis='both')
    for tl in axHistx.get_xticklabels(): tl.set_visible(False)
    for tl in axHisty.get_yticklabels(): tl.set_visible(False)

    histRange = (-5 * xyError, 5 * xyError)
    axHistx.hist(xResid, bins=nbins, range=histRange, color=color)
    axHisty.hist(yResid, bins=nbins, range=histRange, color=color,
                 orientation='horizontal')
    axScatter.axis(histRange * 2)
    axScatter.annotate('medians: {:.1e},{:.1e}'.format(*medianxy),
                       xy=(0.5, 0.05), xycoords='axes fraction',
                       ha='center', va='bottom',
                       bbox={'boxstyle': 'round', 'fc': 'w', 'alpha': 0.8})
    pyplot.show()


def _plotChain(tracex, tracey):
    from matplotlib import pyplot
    from matplotlib.patches import Ellipse

    pyplot.figure()
    ell = Ellipse((np.mean(tracex), np.mean(tracey)),
                  2 * np.std(tracex), 2 * np.std(tracey), 0,
                  fc='RoyalBlue', alpha=0.2, zorder=-1)
    pyplot.gca().add_patch(ell)
    pyplot.plot(tracex, tracey, color='black', alpha=0.2, zorder=0)
    pyplot.scatter(tracex, tracey, c=np.arange(tracex.size), zorder=1)
    pyplot.gca().ticklabel_format(style='sci', scilimits=(-2, 2), axis='both')
    cbar = pyplot.colorbar()
    cbar.set_label('Chain Iteration')
    pyplot.show()