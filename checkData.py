import ogr
import os
import numpy
from datetime import datetime

for dirName, subDirs, fileNames in os.walk('.'):
    for f in fileNames:
        if f.endswith('.shp'):
            print ('Filename: ' + f)
            f = os.path.join(dirName, f)
            ds = ogr.Open(f)
            for lyr in ds:
                dateStamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                print ('DateStamp: ' + dateStamp)
                fileSize = sum([sum(map(lambda fname: os.path.getsize(os.path.join(directory, fname)), files)) for directory, folders, files in os.walk(dirName)])
                fileSize = float(fileSize)
                fileSize = fileSize/1000/1000
                fileSize = numpy.around(fileSize, decimals=1)
                fileSize = str(fileSize)
                print ('Filesize: ' + fileSize + ' MB')
                (minx, maxx, miny, maxy) = lyr.GetExtent()             
                print("Geometry type: %s" % ogr.GeometryTypeToName(lyr.GetGeomType()))
                geomType = ogr.GeometryTypeToName(lyr.GetGeomType())
                srs = lyr.GetSpatialRef()
                srsAuth = srs.GetAttrValue("AUTHORITY",0)
                srsCode = srs.GetAttrValue("AUTHORITY",1)
                print ('Projection: '+ srsAuth + ' ' + srsCode)
                print ('Extent: %f, %f - %f %f' % (minx, miny, maxx, maxy)) #W-S-E-N
                print("Feature count: %d" % lyr.GetFeatureCount())
                lyr_defn = lyr.GetLayerDefn()
                for i in range(lyr_defn.GetFieldCount()):
                    field_defn = lyr_defn.GetFieldDefn(i)
                    name = field_defn.GetName()
                    ftype = ogr.GetFieldTypeName(field_defn.GetType())
                    width = field_defn.GetWidth()
                    prec = field_defn.GetPrecision()
                    print('Field: %s %s (%d.%d)' % (name, ftype, width, prec))   
            print ('\n') 
