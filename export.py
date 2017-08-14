
#! /usr/bin/env python

#This script will export records from an instance of GeoNetwork.  An XSLT called iso2GBL.xsl will transform the ISO19139 records to GeoBlacklight schema JSONs.
#Type this to get an export of GeoBlacklight Metadata in CSV format: python export.py -cat "insert category name" -csv
#Type this to get an export of the files as both ISO 19139, GeoBlacklight JSON, and a GeoBlacklight CSV: python export.py -cat "select category name" -ogm newfoldername

__author__ = "Kevin Dyke, Karen Majewicz"
__maintainer__ = "Karen Majewicz"
__email__ = "majew030@umn.edu"



import os
from glob import glob
import json
import sys
from collections import OrderedDict
import argparse
import pdb
import pprint
import time
import logging
import fnmatch
import urllib

# non-standard libraries.
from lxml import etree
from owslib import csw
from owslib.etree import etree
from owslib import util
from owslib.namespaces import Namespaces
import unicodecsv as csv
# demjson provides better error messages than json
import demjson
import requests

# local imports
import config
from users import USERS_INSTITUTIONS_MAP

# logging stuff
if config.DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO
global log
log = logging.getLogger('owslib')
log.setLevel(log_level)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(log_level)
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
ch.setFormatter(log_formatter)
log.addHandler(ch)



class CSWToGeoBlacklight(object):

    def __init__(self, CSW_URL,
                 CSW_USER, CSW_PASSWORD, USERS_INSTITUTIONS_MAP, INST=None,
                 TO_CSV=True, TO_JSON=False, TO_XML=False, TO_XMLs=False, TO_OGM=False,
                 max_records=None, RECURSIVE=False):

        self.XSLT_PATH = os.path.join(".", "iso2geoBL.xsl")
        self.transform = etree.XSLT(etree.parse(self.XSLT_PATH))
        self.namespaces = self.get_namespaces()
        self.to_csv = TO_CSV
        self.to_json = TO_JSON
        self.to_xml = TO_XML
        self.to_xmls = TO_XMLs
        self.to_opengeometadata = TO_OGM
        self.inst = INST
        self.records = OrderedDict()
        self.record_dicts = OrderedDict()
        self.max_records = max_records
        self.gn_session = None


        self.CSW_USER = CSW_USER
        self.CSW_PASSWORD = CSW_PASSWORD
        self.CSW_URL = CSW_URL
        self.RECURSIVE = RECURSIVE
        self.PREFIX = "urn-"
        self.LANG = "eng"
        self.GEONETWORK_BASE = CSW_URL[:CSW_URL.find("/geonetwork/")]
        self.GEONETWORK_SEARCH_BASE = self.GEONETWORK_BASE \
            + "/geonetwork/srv/{l}/q?_content_type=json".format(l=self.LANG)
        self.GEONETWORK_BY_CAT = self.GEONETWORK_SEARCH_BASE \
            + "&fast=index&_cat={category}"
        self.GET_INST_URL = self.GEONETWORK_SEARCH_BASE \
            + "&fast=index&_uuid={uuid}"
        self.CSV_FIELDNAMES = [
            "uuid",
            "dc_title_s",
            "dc_identifier_s",
            "dc_rights_s",
            "dct_provenance_s",
            "dc_subject_sm",
            "dc_description_s",
            "dct_issued_s",
            "dct_temporal_sm",
            "dc_creator_sm",
            "solr_year_i",
            "dc_publisher_sm",
            "layer_id_s",
            "dc_format_s",
            "dc_spatial_sm",
            "dct_isPartOf_sm",
            "layer_slug_s",
            "dc_type_s",
            "layer_geom_type_s",
            "layer_modified_dt",
            "solr_geom",
            "dct_references_s",
            "geoblacklight_version",

        ]

        self.USERS_INSTITUTIONS_MAP = USERS_INSTITUTIONS_MAP

    @staticmethod
    def get_namespaces():
        """
        Returns specified namespaces using owslib Namespaces function.
        """

        n = Namespaces()
        ns = n.get_namespaces(["gco", "gmd", "gml", "gml32", "gmx", "gts",
                               "srv", "xlink", "dc"])

        return ns

    def get_files_from_path(self, start_path, criteria="*"):
        files = []

        if self.RECURSIVE:
            for path, folder, ffiles in os.walk(start_path):
                for i in fnmatch.filter(ffiles, criteria):
                    files.append(os.path.join(path, i))
        else:
            files = glob(os.path.join(start_path, criteria))
        return files


    def to_spreadsheet(self, records):
        """
        Transforms CSW XMLs into GeoBlacklight JSON, then writes to a CSV.
        """
        with open("gbl-metadata.csv", "wb") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=self.CSV_FIELDNAMES)
            writer.writeheader()
            for r in records:
                writer.writerow(records[r])

    def get_records_by_ids(self, ids):
        recordcount = 0
        for group in self.chunker(ids, 100):
            log.info("Requested {n} records from CSW so far".format(
                n=str(recordcount)
            ))
            recordcount = recordcount + 100
            self.csw_i.getrecordbyid(
                id=group,
                outputschema="http://www.isotc211.org/2005/gmd")
            self.records.update(self.csw_i.records)

    def get_records(self, start_pos=0, ids=None):

        if ids:
            self.get_records_by_ids(ids)
            return

        self.csw_i.getrecords2(
            esn="full",
            startposition=start_pos,
            maxrecords=100,
            outputschema="http://www.isotc211.org/2005/gmd"
        )

        log.debug(self.csw_i.results)
        self.records.update(self.csw_i.records)

        max_records = self.max_records or self.csw_i.results['matches']

        if self.csw_i.results['matches'] != 0 and \
                self.csw_i.results['nextrecord'] <= max_records:
            start_pos = self.csw_i.results['nextrecord']
            self.get_records(start_pos=start_pos)

    def connect_to_csw(self, url):
        """
        Connect to a CSW using configuration options from config.py.
        """
        if self.CSW_USER and self.CSW_PASSWORD:
            self.csw_i = csw.CatalogueServiceWeb(
                url,
                username=self.CSW_USER,
                password=self.CSW_PASSWORD)
        else:
            self.csw_i = csw.CatalogueServiceWeb(url)

    def create_geonetwork_session(self):
        """
        Log into GeoNetwork. Used for non-CSW actions, like searching by
        category or fetching the owner of a record.
        """
        BASE_URL = self.GEONETWORK_BASE+"/srv/eng/"
        LOGIN = self.GEONETWORK_BASE+"/j_spring_security_check"

        self.gn_session = requests.Session()
        self.gn_session.auth = (self.CSW_USER, self.CSW_PASSWORD)
        login_r = self.gn_session.post(LOGIN)

    def destroy_geonetwork_session(self):
        LOGOUT = self.GEONETWORK_BASE+"/j_spring_security_logout"
        self.gn_session.post(LOGOUT)

    def get_inst_for_record(self, record_uuid):
        if not self.gn_session:
            self.create_geonetwork_session()

        url = self.GET_INST_URL.format(uuid=record_uuid)
        re = self.gn_session.get(url)
        time.sleep(1)
        js = re.json()


    @staticmethod
    def get_uuid_path(uuid):
        uuid_r = uuid.replace("-","")
        # return uuid_r[0:2] + "/" + uuid_r[2:4] + "/" + uuid_r[4:6] + "/" + uuid_r[6:]
        return uuid_r
    def transform_records(self, uuids_and_insts=None):
        """
        Transforms a set of ISO19139 records into GeoBlacklight JSON.
        Uses iso2geoBL.xsl to perform the transformation.
        """
        inst = self.inst
        for r in self.records:
            if not inst and not uuids_and_insts:
                inst = self.get_inst_for_record(r)
            elif uuids_and_insts:
                inst = uuids_and_insts[r]
            rec = self.records[r].xml
            rec = rec.replace("\n", "")
            root = etree.fromstring(rec)
            record_etree = etree.ElementTree(root)

            result = self.transform(record_etree)


            result_u = unicode(result)


            try:
                result_json = demjson.decode(result_u)

                result_dict = OrderedDict({r: result_json})
                log.debug(result_dict)
                self.record_dicts.update(result_dict)
            except demjson.JSONDecodeError as e:
                log.error("ERROR: {e}".format(e=e))
                log.error(result_u)

    def records_by_csw(self, csw_name):
        url = self.CSW_URL.format(virtual_csw_name=csw_name)
        self.connect_to_csw(url)
        self.get_records()
        self.transform_records()
        self.handle_transformed_records()

    def update_one_record(self, uuid):
        url = self.CSW_URL.format(virtual_csw_name="publication")
        self.connect_to_csw(url)
        self.csw_i.getrecordbyid(
            id=[uuid],
            outputschema="http://www.isotc211.org/2005/gmd"
        )
        self.records.update(self.csw_i.records)
        rec = self.records[uuid].xml
        rec = rec.replace("\n", "")
        root = etree.fromstring(rec)
        record_etree = etree.ElementTree(root)
        inst = self.get_inst_for_record(uuid)
        result = self.transform(
            record_etree,
            institution=self.institutions[inst]
        )
        result_u = unicode(result)
        log.debug(result_u)
        try:
            self.record_dicts = OrderedDict({uuid: demjson.decode(result_u)})
            log.debug(self.record_dicts)
        except demjson.JSONDecodeError as e:
            log.error("ERROR: {e}".format(e=e))
            log.error(result_u)

        self.handle_transformed_records()

    @staticmethod
    def chunker(seq, size):
        if sys.version_info.major == 3:
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))
        elif sys.version_info.major == 2:
            return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))

    def records_by_category(self, category):
        if not self.gn_session:
            self.create_geonetwork_session()
        csw_url = self.CSW_URL.format(virtual_csw_name="publication")
        self.connect_to_csw(csw_url)

        if sys.version_info.major == 3:
            url = self.GEONETWORK_BY_CAT.format(
                category=urllib.parse.quote_plus(category)
            )
        elif sys.version_info.major == 2:
            url = self.GEONETWORK_BY_CAT.format(
                category=urllib.quote_plus(category)
            )
        log.debug(url)
        uuids_and_insts = {}
        r = self.gn_session.get(url)
        j = r.json()
        if "metadata" in j:
            results = j["metadata"]
            log.info("{n} records found for category '{cat}'".format(
                n=str(len(results)),
                cat=category))

            for r in results:
                ownerId = r["geonet:info"]["ownerId"]
                uuid = r["geonet:info"]["uuid"]
                if ownerId in self.USERS_INSTITUTIONS_MAP:
                    uuids_and_insts[uuid] = self.USERS_INSTITUTIONS_MAP[ownerId]
                else:
                    log.warn("Owner id '{id}', which maps to user name \
                        '{name}' not found in user map. Make sure users.py \
                        is up-to-date.".format(id=ownerId, name=r["userinfo"]))

            self.get_records_by_ids(uuids_and_insts.keys())
            self.transform_records(uuids_and_insts=uuids_and_insts)
            self.handle_transformed_records()

        else:
            log.warn(r.text)

    def make_output_folder_path(self, output_path, uuid):
        uuid_r = uuid.replace("-", "")
        p = os.path.join(output_path, uuid_r[0:8], uuid_r[8:])
        if not os.path.exists(p):
            os.makedirs(p)
        return p

    def output_json(self, output_path="./output"):
        for uuid in self.record_dicts:
            folder_path = self.make_output_folder_path(output_path, uuid)
            fn = os.path.join(folder_path,
                              "geoblacklight.json")
            with open(fn, "wb") as json_file:
                try:
                    json.dump(self.record_dicts[uuid], json_file, indent=0)
                except TypeError as e:
                    log.error(e)
                    log.error("UUID with error: {uuid}".format(uuid=uuid))

    def output_xml(self, output_path="./output"):
        for uuid in self.records:
            folder_path = self.make_output_folder_path(output_path, uuid)
            fn = os.path.join(folder_path,
                              "iso19139.xml")
            with open(fn, "wb") as xml_file:
                xml_file.write(self.records[uuid].xml)


    def single_xml(self, output_path="./output"):
        for uuid in self.records:
            folder_path = self.make_output_folder_path(output_path)
            fn = os.path.join(folder_path,[uuid].xml)
            with open(fn, "wb") as xml_file:
                xml_file.write(self.records[uuid].xml)

    def output_layers_json(self, output_path="./output"):
        fname = os.path.join(output_path, "layers.json")

        with open(fname, "wb") as layers_json_file:
            layers_json = {}

            for uuid in self.record_dicts:
                layers_json[self.PREFIX + uuid] = self.get_uuid_path(uuid)
            json.dump(
                layers_json,
                layers_json_file,
                indent=0,
                separators=(',', ': ')
            )

    def handle_transformed_records(self, output_path="./output"):
        log.debug("Handling {n} records.".format(n=len(self.record_dicts)))

        if self.to_csv:
            self.to_spreadsheet(self.record_dicts)

        elif self.to_json:
            self.output_json(output_path)

        elif self.to_xml:
            self.output_xml(output_path)

        elif self.to_xmls:
            self.single_xml(output_path)

        elif self.to_opengeometadata:
            self.output_json(self.to_opengeometadata)
            self.output_xml(self.to_opengeometadata)
            self.output_layers_json(self.to_opengeometadata)




    def records_by_csv(self, path_to_csv, inst=None):
        with open(path_to_csv, "rU") as f:
            reader = csv.DictReader(f)
            fns = reader.fieldnames
            uuids_and_insts = {}
            url = self.CSW_URL.format(virtual_csw_name="publication")
            self.connect_to_csw(url)

            for row in reader:
                uuids_and_insts[row["uuid"]] = self.get_inst_for_record(row["uuid"])


            self.get_records_by_ids(uuids_and_insts.keys())
            self.transform_records(uuids_and_insts=uuids_and_insts)
            self.handle_transformed_records()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--recursive",
        action='store_true',
        help="If input involves a folder, recurse into subfolders.")
    output_group = parser.add_mutually_exclusive_group(required=False)
    output_group.add_argument(
        "-csv",
        "--to-csv",
        action='store_true',
        help="Output to CSV.")
    output_group.add_argument(
        "-j",
        "--to-json",
        action='store_true',
        help="Outputs GeoBlacklight JSON files.")

    output_group.add_argument(
        "-x",
        "--to-xml",
        action='store_true',
        help="Outputs ISO19139 XML files.")

    output_group.add_argument(
        "-xs",
        "--to-xmls",
        action='store_true',
        help="Outputs ISO19139 XML files.")

    output_group.add_argument(
        "-ogm",
        "--to-opengeometadata",
        help="Outputs ISO19139 XMLs and GeoBlacklight JSON files to \
            a folder name specified.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-cat",
        "--by-category",
        help="Indicate GeoNetwork Category \
              to pull records from.")


    args = parser.parse_args()
    interface = CSWToGeoBlacklight(
        config.CSW_URL, config.CSW_USER, config.CSW_PASSWORD,
        USERS_INSTITUTIONS_MAP,
        TO_CSV=args.to_csv, TO_JSON=args.to_json, TO_XML=args.to_xml,
        TO_OGM=args.to_opengeometadata, RECURSIVE=args.recursive)


    if args.by_category:
        interface.records_by_category(args.by_category)

    else:
        sys.exit(parser.print_help())

    if interface.gn_session:
        interface.destroy_geonetwork_session()


if __name__ == "__main__":
    sys.exit(main())
