import Polygon as P
import numpy as np
import os, sys, glob
import pyfits


class RegionFile:
    def __init__(self,filename):
        self.filename = filename

    def read(self):
        fin = open(self.filename)
        L = fin.readlines()  
        # implement space filling polygon
        cumPolygon = P.Polygon()
        for l in L:
            if 'polygon' in l:
                coordlist = [int(round(float(i))) for i in l[l.find('(')+1:l.find(')')].split(',')]
                # coordlist = [i-1 for i in coordlist]
                print coordlist
                nCoordlist = np.reshape(np.asarray(coordlist), (len(coordlist)/2, 2))
                singlePolygon = P.Polygon(nCoordlist) 
                newPolygon = singlePolygon + cumPolygon
                cumPolygon = newPolygon
        self.polyRegions = cumPolygon
        return

def updateDQArray(fitsimg, ext, poly_object):
    fin = pyfits.open(fitsimg, 'update')
    data = fin['dq', ext].data
    for i in range(data.shape[1]):
      for j in range(data.shape[0]):
        if poly_object.isInside(i+1, j+1):
            try:
                data[j][i] |= 8192
            except:
                pass
    fin.flush()
    fin.close()
    print 'Updated DQ array complete!'
    return

def applymask(fitsimg, regionfile, dq_ext):
    region = RegionFile(regionfile)
    print 'Reading region file'
    region.read()
    print 'Applying %s to DQ ext %s' % (fitsimg, dq_ext)
    updateDQArray(fitsimg, dq_ext, region.polyRegions)
    return