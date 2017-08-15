from datetime import datetime
import ogr
import xml.etree.ElementTree as ET
import csv
import os

template = 'templates/19110template.xml'

#Register and map namespaces
namespaces = {'gmd': 'http://www.isotc211.org/2005/gmd','gco': 'http://www.isotc211.org/2005/gco', 'gml': 'http://www.opengis.net/gml',
              'gfc': 'http://www.isotc211.org/2005/gfc', 'gmx':'"http://www.isotc211.org/2005/gmx'}
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

attrdict = {}
metadict = {}


reader = csv.reader(open('metadata.csv', 'rU'))
for rows in reader:
    Identifier = rows[0]
    actual_filename = rows[3]
    FINAL_TITLE = rows[7]
    Subject = rows[20]
    Issued = rows[21]
    metadict[actual_filename] = Identifier, FINAL_TITLE, Issued, Subject

reader = csv.reader(open('attributes.csv', 'rU'))
for rows in reader:
    attrlabel = rows[0]
    attrdefinition = rows[1]
    attrdict[attrlabel] = attrdefinition

        
def createMetadata():
    tree = ET.parse(template)
    root = tree.getroot()
    name = root.find('{http://www.isotc211.org/2005/gmx}name', namespaces=namespaces)
    scope = root.find('{http://www.isotc211.org/2005/gmx}scope', namespaces=namespaces)
    versionDate = root.find('{http://www.isotc211.org/2005/gmx}versionDate', namespaces=namespaces)
    producer = root.find('gfc:producer', namespaces=namespaces)
    for k, v in metadict.items():
        name[0].text = v[1]
        versionDate[0].text = v[2]
        scope[0].text = v[3]
        if '*' in scope[0].text:
            scope[0].text = scope[0].text.replace('*', '; ')
        
        
    featureType = root.find('gfc:featureType/gfc:FC_FeatureType', namespaces=namespaces)
    ds = ogr.Open(f)
    for lyr in ds:
        lyr_defn = lyr.GetLayerDefn()
        for i in range(lyr_defn.GetFieldCount()):
            field_defn = lyr_defn.GetFieldDefn(i)
            label = field_defn.GetName()
            for k,v in attrdict.items():
                if label == k:
                    featureType.insert(3,ET.Element('{http://www.isotc211.org/2005/gfc}carrierOfCharacteristics'))
                    featureAttribute = ET.SubElement(featureType[3],'{http://www.isotc211.org/2005/gfc}FC_FeatureAttribute')
                    memName = ET.SubElement(featureType[3][0],'{http://www.isotc211.org/2005/gfc}memberName')
                    locName = ET.SubElement(featureAttribute[0],'{http://www.isotc211.org/2005/gco}LocalName')
                    attr = ET.SubElement(featureType[3][0],'{http://www.isotc211.org/2005/gfc}definition')
                    definition = ET.SubElement(attr,'{http://www.isotc211.org/2005/gco}CharacterString')
                    cardinality = ET.SubElement(featureType[3][0],'{http://www.isotc211.org/2005/gfc}cardinality')
                    cardinality.set('gco:nilReason', 'unknown')
                    locName.text = k
                    definition.text = v
                    featureType[0][0].text = fname
                    new_file = f[:-4] + '_19110.xml'
                    tree.write(new_file)
                    print (new_file)         


for dirName, subDirs, fileNames in os.walk('.'):
    for f in fileNames:
        fname = f[:-4]
        if f.endswith('.shp'):
            f = os.path.join(dirName, f)
            createMetadata()
