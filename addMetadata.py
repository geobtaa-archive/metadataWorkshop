import csv
import os
from datetime import datetime
import xml.etree.ElementTree as ET

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
idinfo = 'gmd:identificationInfo/gmd:MD_DataIdentification/'
citeinfo = 'gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/'
distinfo = 'gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/'


##Create a dictionary of metadata values ('metadict') from metadata.csv

metadict = {}
reader = csv.reader(open('metadata.csv', 'rU'))
for rows in reader:
    Identifier = rows[0]
    UUID = rows[1]
    actual_filename = rows[3]
    FINAL_TITLE = rows[7]
    Description = rows[10]
    Temporal = rows[12]
    Provenance = rows[13]
    Spatial = rows[14].split('*')
    layer = rows[15]
    Format = rows[16]
    Language = rows[17].split('*')
    Publisher = rows[19]
    Subject = rows[20].split('*')
    Issued = rows[21]
    Series = rows[22]
    Version = rows[23]
  # Description = rows[10].decode('latin-1')
    metadict[actual_filename] = Identifier, UUID, FINAL_TITLE, Temporal, Provenance, Spatial, layer, Format, Language, Issued, Publisher, Subject, Issued, Series, Description, Version
def deleteElements():
    for index, tkw in enumerate(themeKeywords):
        if index > 0:
            del_key = md_themeKeywords[0].find('{http://www.isotc211.org/2005/gmd}keyword')
            md_themeKeywords[0].remove(del_key)
    for index, pkw in enumerate(placeKeywords):
        if index > 0:
            del_key = md_placeKeywords[0].find('{http://www.isotc211.org/2005/gmd}keyword')
            md_placeKeywords[0].remove(del_key)
    for index, langs in enumerate(language):
        if index > 0:
            del_key = root[12][0].find('{http://www.isotc211.org/2005/gmd}language[0]')
            root[12][0].remove(del_key)           
    
def createMetadata():
    for k, v in metadict.items():
        if k[:-4] == f[:-4]:
            print v[14]
            metadataID.text = 'edu.nyu.hdl:' + v[1]
            URL.text = v[0]
            URI.text = v[0]
            distURL.text = v[0]
            distName.text = k
            title.text = v[2]
            tempInstant.text = v[3] + tempInstant.text[4:]
            mdDateStamp.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            deleteElements()
            date.text = v[9] + '-01-01'
            collection.text = v[13]
            for name in publisher:
                name.text = v[10]
                name = name.text
            topicCategory.text = v[11][0].lower()
            themeKeywords[0][0].text = v[11][0]
            placeKeywords[0][0].text = v[5][0]
            abstract.text = v[14]
            root[12][0][8][0].set('codeListValue',v[8][0])
            for theme in v[11][1:]:
                md_themeKeywords[0].insert(0,ET.Element('{http://www.isotc211.org/2005/gmd}keyword'))
                new_themeKeyword = ET.SubElement(md_themeKeywords[0][0],'{http://www.isotc211.org/2005/gco}CharacterString')
                new_themeKeyword.text = theme
            for place in v[5][1:]:
                md_placeKeywords[0].insert(0,ET.Element('{http://www.isotc211.org/2005/gmd}keyword'))
                new_placeKeyword = ET.SubElement(md_placeKeywords[0][0],'{http://www.isotc211.org/2005/gco}CharacterString')
                new_placeKeyword.text = place
            for lang in v[8][1:]:
                root[12][0].insert(9,ET.Element('{http://www.isotc211.org/2005/gmd}language'))
                new_lang = root[12][0][9]
                new_langCode = ET.SubElement(new_lang,'{http://www.isotc211.org/2005/gmd}LanguageCode')
                new_langCode.set('codeList','http://www.loc.gov/standards/iso639-2/')
                new_langCode.set('codeSpace','ISO639-2')
                new_langCode.set('codeListValue',lang)
            distFormat.text = v[7]
            distributor.text = v[4]
            credit.text = name + '. (' + v[9]+ '). ' + title.text + '. Available at: ' + URL.text + '.'
            edition.clear()
            new_edition = ET.SubElement(citation[2],'{http://www.isotc211.org/2005/gco}CharacterString')
            print new_edition.tag
            new_edition.text = v[15]
            tree.write(file)

####Walk through a directory of files, find XML documents. Find target metadata elements.
                
for dirName, subDirs, fileNames in os.walk('.'):
    for f in fileNames:
        if f.endswith('.xml'):
            file = os.path.join(dirName, f)
            tree = ET.parse(file)
            root = tree.getroot()
            if root.tag == '{http://www.isotc211.org/2005/gmd}MD_Metadata':
                #print (f)
                citation = root.find('gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation', namespaces=namespaces)
                title = root.find(citeinfo + 'gmd:title/gco:CharacterString', namespaces=namespaces)
                date = root.find(citeinfo + 'gmd:date/gmd:CI_Date/gmd:date/gco:Date', namespaces=namespaces)
                URL = root.find(citeinfo + 'gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString', namespaces=namespaces)
                edition = root.find(citeinfo + 'gmd:edition', namespaces=namespaces)
                credit = root.find(idinfo + 'gmd:credit/gco:CharacterString', namespaces=namespaces)
                metadataID = root.find('gmd:fileIdentifier/gco:CharacterString', namespaces=namespaces)
                URI = root.find('gmd:dataSetURI/gco:CharacterString', namespaces=namespaces)
                mdDateStamp = root.find('gmd:dateStamp/gco:DateTime', namespaces=namespaces)
                topicCategory = root.find(idinfo + 'gmd:topicCategory/gmd:MD_TopicCategoryCode', namespaces=namespaces)
                publisher = root.findall(citeinfo + 'gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString', namespaces=namespaces)
                md_keywords = root.findall(idinfo + 'gmd:descriptiveKeywords/gmd:MD_Keywords', namespaces=namespaces)
                all_keywords = root.findall(idinfo + 'gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString', namespaces=namespaces)
                placeKeywords = root.findall(idinfo + 'gmd:descriptiveKeywords[1]/gmd:MD_Keywords[1]/gmd:keyword', namespaces=namespaces)
                md_placeKeywords = root.findall(idinfo + 'gmd:descriptiveKeywords[1]/gmd:MD_Keywords[1]', namespaces=namespaces)
                themeKeywords = root.findall(idinfo + 'gmd:descriptiveKeywords[2]/gmd:MD_Keywords[1]/gmd:keyword', namespaces=namespaces)
                md_themeKeywords = root.findall(idinfo + 'gmd:descriptiveKeywords[2]/gmd:MD_Keywords[1]', namespaces=namespaces)
                language = root.findall(idinfo + 'gmd:language', namespaces=namespaces)
                collection = root.find(idinfo + 'gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:aggregateDataSetName/gmd:CI_Citation/gmd:title/gco:CharacterString', namespaces=namespaces)
                distFormat = root.find('gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format/gmd:name/gco:CharacterString', namespaces=namespaces)
                distributor = root.find('gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString', namespaces=namespaces)
                abstract = root.find(idinfo + 'gmd:abstract/gco:CharacterString', namespaces=namespaces)
                distURL = root.find(distinfo + 'gmd:linkage/gmd:URL', namespaces=namespaces)
                distName = root.find(distinfo +'gmd:name/gco:CharacterString',namespaces=namespaces)
                tempInstant = root.find(idinfo + 'gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition', namespaces=namespaces)
                tempEnd = (idinfo + 'gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition')
                createMetadata()
##                
##                    
