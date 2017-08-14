#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

__author__ = "Kevin Dyke, Karen Majewicz"
__maintainer__ = "Karen Majewicz"
__email__ = "majew030@umn.edu"

#Script that uses CSW Transactions for updating titles and abstracts in ISO 19139 XML files residing in an instance of GeoNetwork.
#Modified for FOSS4g Workshop, 2017


from __future__ import unicode_literals

# Python standard libs
import logging
import os
import sys
import json
from datetime import datetime
import argparse
import time
import pdb

# non standard dependencies
from owslib import csw
from owslib.etree import etree
from owslib import util
from owslib.namespaces import Namespaces
import unicodecsv as csv
from dateutil import parser
# from xml.etree import ElementTree as etree

# config options - see config.py.sample for how to structure
from config import CSW_URL_PUB, CSW_USER, CSW_PASSWORD, DEBUG

# logging
if DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO
log = logging.getLogger('owslib')
log.setLevel(log_level)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(log_level)
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(log_formatter)
log.addHandler(ch)


class UpdateCSW(object):

    def __init__(self, url, username, password, input_csv_path):
        self.INNER_DELIMITER = "###"
        self.csw = csw.CatalogueServiceWeb(
            url, username=username, password=password)
        self.records = {}

        if not os.path.isabs(input_csv_path):
            input_csv_path = os.path.abspath(
                os.path.relpath(input_csv_path, os.getcwd()))

        self.csvfile = open(input_csv_path, "rU")

        self.reader = csv.DictReader(self.csvfile)
        self.fieldnames = self.reader.fieldnames

        self.namespaces = self.get_namespaces()

        # these are the column names that will trigger a change
        self.field_handlers = {"iso19139": {
            "NEW_title": self.NEW_title,
            "NEW_abstract": self.NEW_abstract,

        },


		#the xpaths to all of the elements accessible for changes.
		#Root is gmd:MD_Metadata
        }

        self.XPATHS = {"iso19139": {
            "citation": "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation",
            "title": "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString",
            "md_data_identification": "gmd:identificationInfo/gmd:MD_DataIdentification",
            "abstract": "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString",

        },
        }


    @staticmethod
    def get_namespaces():
        """
        Returns specified namespaces using owslib Namespaces function.
        """
        n = Namespaces()
        ns = n.get_namespaces(
            ["gco", "gmd", "gml", "gml32", "gmx", "gts", "srv", "xlink", "dc"])
        return ns



#PRIMARY FUNCTIONS FOR UPDATING AND CREATING ELEMENTS
    def _simple_element_update(self, uuid, new_value, xpath=None, element=None):
        """
        Primary function for most records.
        Updates single element of record. Nothing fancy.
        Elements like abstract and title.
        Positional arguments:
        uuid -- the unique id of the record to be updated
        new_value -- the new value supplied from the csv
        Keyword arguments (need one and only one):
        xpath -- must follow straight from the root element
        element -- match a name in self.XPATHS for the current schema
        """

        if xpath:
            path = xpath
        elif element:
            path = self.XPATHS[self.schema][element]
        else:
            log.error("_simple_element_update: No xpath or element provided")
            return

        tree = self.record_etree

        original_path = path
        elem = []

		#looks for existence of path, if not there, moves up a level until an element node is present.
		#sets path based upon what exists.
		#will not work for missing base level elements that are not contained in another parent element beyond the root.

        while len(elem) == 0:
            elem = tree.xpath(path, namespaces=self.namespaces)
            if len(elem) == 0:
                log.debug(
                    "Did not find \n {p} \n trying next level up.".format(
                        p=path
                    )
                )
                path = "/".join(path.split("/")[:-1])

		#if there is an element ? and if the path exists
        if len(elem) > 0 and path == original_path:
            log.debug("Found the path: \n {p}".format(p=path))

			#checks to see if the text is the same as the new value, if not, changes
            if elem[0].text != new_value:
                elem[0].text = new_value
                self.tree_changed = True

			#if it is the same, just reports that
            else:
                log.info("Value for \n {p} \n already set to: {v}".format(
                    p=path.split("/")[-2], v=new_value))

		#if there is an element to be created but the path isn't there
        elif len(elem) > 0 and path != original_path:
            elements_to_create = [
                e for e in original_path.split("/") if e not in path]
            self._create_elements(elem[0], elements_to_create)
            log.debug(
                "Recursing to _simple_element_update now that the \
                element should be there.")
            self._simple_element_update(uuid, new_value, xpath=original_path)

	#called at the end of _simple_element_update if needed.
    def _create_elements(self, start_element, list_of_element_names):
        tree = self.record_etree
        base_element = start_element
        for elem_name in list_of_element_names:
            elem_name_split = elem_name.split(":")
            ns = "{" + self.namespaces[elem_name_split[0]] + "}"
            base_element = etree.SubElement(
                base_element,
                "{ns}".format(ns=ns) + elem_name_split[1],
                nsmap=self.namespaces
            )
            log.debug("Created {n}".format(n=elem_name))
            self.tree_changed = True



#CITATION ELEMENTS

    def NEW_title(self, uuid, new_title):
        """
        Updates title of record
        """
        if new_title != "" and new_title != "SKIP":
            update = self._simple_element_update(
                uuid, new_title, element="title")
            log.info("updated title")



    def NEW_abstract(self, uuid, new_abstract):
        """
        Updates abstract of record
        """
        if new_abstract != "" and new_abstract != "SKIP":
            update = self._simple_element_update(
                uuid, new_abstract, element="abstract")
            log.info("updated abstract")



#PROCESS


    def _get_etree_for_record(self, uuid):
        """
        Set self.record_etree to etree ElementTree
        of record with inputted uuid.
        """

        xml = self.records[uuid].xml
        root = etree.fromstring(xml)
        return etree.ElementTree(root)

    def get_record_by_id(self, uuid):
        """
        Requests a record via the provided uuid.
        Sets self.records[uuid] to the result. Returns nothing.
        """

        if self.schema == "iso19139":
            outschema = "http://www.isotc211.org/2005/gmd"
            log.debug("get_record_by_id: requesting fresh XML.")
            self.csw.getrecordbyid(id=[str(uuid)], outputschema=outschema)
            time.sleep(1)
            if uuid in self.csw.records:
                log.debug("get_record_by_id: got the xml")
                self.records[uuid] = self.csw.records[uuid]

        else:
            # unused Dublin Core hack for dc:identifiers that are URIs
            outschema = "http://www.opengis.net/cat/csw/2.0.2"
            xml_text = """<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" service="CSW" version="2.0.2" resultType="results" startPosition="1" maxRecords="10" outputFormat="application/xml" outputSchema="http://www.opengis.net/cat/csw/2.0.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0">
              <csw:Query typeNames="csw:Record">
                <csw:ElementSetName>full</csw:ElementSetName>
                <csw:Constraint version="1.1.0">
                  <ogc:Filter>
                    <ogc:PropertyIsLike matchCase="false" wildCard="%" singleChar="_" escapeChar="\">
                      <ogc:PropertyName>dc:identifier</ogc:PropertyName>
                      <ogc:Literal>{id}</ogc:Literal>
                    </ogc:PropertyIsLike>
                  </ogc:Filter>
                </csw:Constraint>
              </csw:Query>
            </csw:GetRecords>""".format(id=uuid)
            self.csw.getrecords2(xml=xml_text)
            self.records[uuid] = self.csw.records.items()[0][1]

    def process_spreadsheet(self):
        """
        Iterates through the inputted CSV, detects NEW_ fields, and executes
        update functions as needed.
        """
        for row in self.reader:
            log.debug(row)
            self.row_changed = False
            self.tree_changed = False
            self.record_etree = False

            self.row = row
            if "uuid" in row:
                self.uuid = row["uuid"]
            elif "UUID" in row:
                self.uuid = row["UUID"]
            else:
                sys.exit("No uuid column found. Must be named uuid or UUID.")

            if self.uuid == "DELETED" or self.uuid == "SKIP":
                continue

            log.debug(self.uuid)

            if "schema" in row:
                self.schema = row["schema"]
            else:
                log.info("No 'schema' column. Defaulting to iso19139.")
                self.schema = "iso19139"

            self.get_record_by_id(self.uuid)
            self.record_etree = self._get_etree_for_record(self.uuid)

            for field in self.fieldnames:
                if field.lower() == "uuid":
                    continue

                if field in self.field_handlers[self.schema] and field in row:
                    self.field_handlers[self.schema][field].__call__(
                        self.uuid,
                        row[field]
                    )

            if self.uuid in self.records and self.tree_changed:
                log.debug("replacing entire XML")
                new_xml = etree.tostring(self.record_etree)
                self.row_changed = True
                self.csw.transaction(
                    ttype="update",
                    typename='csw:Record',
                    record=new_xml,
                    identifier=self.uuid)
                time.sleep(2)
               #  self.update_timestamp(self.uuid)
                log.info("Updated: {uuid}\n\n".format(uuid=self.uuid))
            else:
                log.info("No change: {uuid}\n\n".format(uuid=self.uuid))


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "input_csv",
        help="indicate path to the csv containing the updates")
    args = parser.parse_args()
    f = UpdateCSW(CSW_URL_PUB, CSW_USER, CSW_PASSWORD, args.input_csv)
    f.process_spreadsheet()

if __name__ == "__main__":
    sys.exit(main())
