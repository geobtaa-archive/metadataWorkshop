import ogr
import xml.etree.ElementTree as ET
import os
import numpy
from datetime import datetime

template = 'templates/template.xml'

#Map and register namespaces

namespaces = {'gmd': 'http://www.isotc211.org/2005/gmd','gco': 'http://www.isotc211.org/2005/gco', 'gml': 'http://www.opengis.net/gml', 'gfc': 'http://www.isotc211.org/2005/gfc'}
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
ET.register_namespace('gmd', 'http://www.isotc211.org/2005/gmd')
ET.register_namespace('gco', 'http://www.isotc211.org/2005/gco')
ET.register_namespace('gts', 'http://www.isotc211.org/2005/gts')
ET.register_namespace('gss', 'http://www.isotc211.org/2005/gss')
ET.register_namespace('gsr', 'http://www.isotc211.org/2005/gsr')
ET.register_namespace('gfc', 'http://www.isotc211.org/2005/gfc')
ET.register_namespace('gmx', 'http://www.isotc211.org/2005/gmx')
ET.register_namespace('gmi', 'http://www.isotc211.org/2005/gmi')
ET.register_namespace('gml', 'http://www.opengis.net/gml')

#Find elements by XPath and write new values from the data layer


def createMetadata():
    minxx = str(minx)
    minyy = str(miny)
    maxxx = str(maxx)
    maxyy = str(maxy)
    tree = ET.parse(template)
    root = tree.getroot()
    mdDateStamp = root.find("gmd:dateStamp/gco:DateTime", namespaces=namespaces)
    auth = root.find('gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString', namespaces=namespaces)
    code = root.find('gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', namespaces=namespaces)
    west = root.find('gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal', namespaces=namespaces)
    east = root.find('gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal', namespaces=namespaces)
    south = root.find('gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal', namespaces=namespaces)
    north = root.find('gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal', namespaces=namespaces)
    fSize = root.find('gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:transferSize/gco:Real', namespaces=namespaces)
    geomTypeCode = root.find('gmd:spatialRepresentationInfo/gmd:MD_VectorSpatialRepresentation/gmd:geometricObjects/gmd:MD_GeometricObjects/gmd:geometricObjectType/gmd:MD_GeometricObjectTypeCode', namespaces=namespaces)
    if geomType == 'Line String':
        geomTypeCode.attrib['codeListValue'] = 'curve'
    if geomType == 'Point':
        geomTypeCode.attrib['codeListValue'] = 'point'
    if geomType == 'Polygon':
        geomTypeCode.attrib['codeListValue'] = 'surface'    
    west.text = minxx
    east.text = maxxx
    north.text = maxyy
    south.text = minyy
    auth.text = srsAuth
    code.text = srsCode
    fSize.text = fileSize
    mdDateStamp.text = dateStamp
    if f.endswith ('.shp'):
        geomObjects =  root.find('gmd:spatialRepresentationInfo/gmd:MD_VectorSpatialRepresentation/gmd:geometricObjects/gmd:MD_GeometricObjects/gmd:geometricObjectCount/gco:Integer', namespaces=namespaces)
        geomObjects.text =  str(lyr.GetFeatureCount())
    new_file = f[:-4] + '.xml'
    tree.write(new_file)
    
#walk through the directory and locate shapefile layers -decimals=1) get the Geometry Type, Projection, Geographic Extent, Feature Count, Attribute Info (Fields), and current date/time
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
                createMetadata()    
            print ('\n') 
                                

        if f.endswith ('.tif'):
            print (f)
            f = os.path.join(dirName, f)
            ds = gdal.Open(f)
            width = ds.RasterXSize
            height = ds.RasterYSize
            gt = ds.GetGeoTransform()
            minx = gt[0]
            miny = gt[3] + width*gt[4] + height*gt[5]
            maxx = gt[0] + width*gt[1] + height*gt[2]
            maxy = gt[3]
            prj = ds.GetProjection()
            srs=osr.SpatialReference(wkt=prj)
            if srs.IsProjected:
                srs = srs.GetAttrValue('authority', 0) + '::' + srs.GetAttrValue('authority', 1)
                srsAuth =srs[4:]
                srsCode =srs[:4]
                readWriteMD()
            writeMD()    
            
            print ('Raster Type: ', ds.GetDriver().ShortName,'/', \
                  ds.GetDriver().LongName)
            print ('Size is ',ds.RasterXSize,'x',ds.RasterYSize, \
                  'x',ds.RasterCount)
            print ('Projection is: ' + srs)
                  
            print ('Extent : %f, %f - %f %f' % (minx, miny, maxx, maxy))

            print ('\n')
