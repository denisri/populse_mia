# -*- coding: utf-8 -*- #
"""Module that handle the projects and their database.

Contains:
    Class:
    - Project

"""

##########################################################################
# Populse_mia - Copyright (C) IRMaGe/CEA, 2018
# Distributed under the terms of the CeCILL license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL_V2.1-en.html
# for details.
##########################################################################

import os
import tempfile
from datetime import datetime, timedelta
import yaml
import json
import glob

# Populse_MIA imports
from populse_mia.software_properties import verCmp
from populse_mia.data_manager.filter import Filter
from populse_mia.software_properties import Config
from populse_mia.utils.utils import set_item_data
from populse_mia.data_manager.database_mia import (
    DatabaseMIA, TAG_ORIGIN_BUILTIN, TAG_ORIGIN_USER)

# Populse_db imports
from populse_db.database import (
    FIELD_TYPE_STRING, FIELD_TYPE_LIST_STRING,
    FIELD_TYPE_JSON, FIELD_TYPE_DATETIME,
    FIELD_TYPE_INTEGER)

from capsul.pipeline import pipeline_tools
from capsul.pipeline.pipeline_nodes import PipelineNode, ProcessNode

COLLECTION_CURRENT = "current"
COLLECTION_INITIAL = "initial"
COLLECTION_BRICK = "brick"

# MIA tags
TAG_CHECKSUM = "Checksum"
TAG_TYPE = "Type"
TAG_EXP_TYPE = "Exp Type"
TAG_FILENAME = "FileName"
TAG_BRICKS = "Bricks"
CLINICAL_TAGS = ["Site", "Spectro", "MR", "PatientRef", "Pathology", "Age",
                 "Sex", "Message"]
BRICK_ID = "ID"
BRICK_NAME = "Name"
BRICK_INPUTS = "Input(s)"
BRICK_OUTPUTS = "Output(s)"
BRICK_INIT = "Init"
BRICK_EXEC = "Exec"
BRICK_INIT_TIME = "Init Time"
BRICK_EXEC_TIME = "Exec Time"

TYPE_NII = "Scan"
TYPE_MAT = "Matrix"
TYPE_TXT = "Text"
TYPE_UNKNOWN = "Unknown"



class Project():
    """Class that handles projects and their associated database.

    :param project_root_folder: project's path
    :param new_project: project's object

    .. Methods:
        - add_clinical_tags: add the clinical tags to the project
        - getDate: return the date of creation of the project
        - getFilter: return a Filter object
        - getFilterName: input box to get the name of the filter to save
        - getName: return the name of the project
        - getSortOrder: return the sort order of the project
        - getSortedTag: return the sorted tag of the project
        - hasUnsavedModifications: return if the project has unsaved
          modifications or not
        - init_filters: initialize the filters at project opening
        - loadProperties: load the properties file
        - redo: redo the last action made by the user on the project
        - reput_values: re-put the value objects in the database
        - save_current_filter: save the current filter
        - saveConfig: save the changes in the properties file
        - setCurrentFilter: set the current filter of the project
        - setDate: set the date of the project
        - saveModifications: save the pending operations of the project
          (actions still not saved)
        - setName: set the name of the project
        - setSortOrder: set the sort order of the project
        - setSortedTag: set the sorted tag of the project
        - undo: undo the last action made by the user on the project
        - unsavedModifications(self, value): Modify the window title
          depending of whether the project has unsaved modifications or not.
        - unsaveModifications: unsaves the pending operations of the project
    """

    def __init__(self, project_root_folder, new_project):
        """Initialization of the project class.

        :param project_root_folder: project's path
        :param new_project: project's object
        """

        if project_root_folder is None:
            self.isTempProject = True
            self.folder = os.path.relpath(tempfile.mkdtemp())
        else:
            self.isTempProject = False
            self.folder = project_root_folder

        # Checks that the project is not already opened
        config = Config()
        opened_projects = config.get_opened_projects()
        if self.folder not in opened_projects:
            opened_projects.append(self.folder)
            config.set_opened_projects(opened_projects)
        else:
            raise IOError(
                "The project at " + str(self.folder) + " is already opened "
                                                       "in another instance "
                                                       "of the software.")
        
        db_folder = os.path.join(self.folder, 'database')
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
        db = 'sqlite:///' + os.path.join(db_folder, 'mia.db')
        self.database = DatabaseMIA(db)
        self.session = self.database.__enter__()
        self.session.add_field_attributes_collection()

        if new_project:

            if not os.path.exists(self.folder):
                os.makedirs(self.folder)

            if not os.path.exists(os.path.join(self.folder, "database")):
                os.makedirs(os.path.join(self.folder, "database"))

            if not os.path.exists(os.path.join(self.folder, "filters")):
                os.makedirs(os.path.join(self.folder, "filters"))

            if not os.path.exists(os.path.join(self.folder, "data")):
                os.makedirs(os.path.join(self.folder, "data"))

            if not os.path.exists(os.path.join(self.folder, "data",
                                               "raw_data")):
                os.makedirs(os.path.join(self.folder, "data", "raw_data"))

            if not os.path.exists(os.path.join(self.folder, "data",
                                               "derived_data")):
                os.makedirs(os.path.join(self.folder, "data", "derived_data"))

            if not os.path.exists(os.path.join(self.folder, "data",
                                               "downloaded_data")):
                os.makedirs(os.path.join(self.folder, "data",
                                         "downloaded_data"))

            # Properties file created
            os.mkdir(os.path.join(self.folder, 'properties'))
            if self.isTempProject:
                name = "Unnamed project"
            else:
                name = os.path.basename(self.folder)
            properties = dict(
                name=name,
                date=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                sorted_tag=TAG_FILENAME,
                sort_order=0
            )
            with open(os.path.join(self.folder, 'properties',
                                   'properties.yml'), 'w', encoding='utf8') \
                    as propertyfile:
                yaml.dump(properties, propertyfile,
                          default_flow_style=False,
                          allow_unicode=True)

            # Adding current and initial collections
            self.session.add_collection(
                COLLECTION_CURRENT, TAG_FILENAME, True,
                TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_collection(
                COLLECTION_INITIAL, TAG_FILENAME, True,
                TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_collection(
                COLLECTION_BRICK, BRICK_ID, False,
                TAG_ORIGIN_BUILTIN, None, None)

            # Tags manually added
            self.session.add_field(
                COLLECTION_CURRENT, TAG_CHECKSUM,
                FIELD_TYPE_STRING, "Path checksum", False,
                TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_INITIAL, TAG_CHECKSUM,
                                   FIELD_TYPE_STRING, "Path checksum", False,
                                   TAG_ORIGIN_BUILTIN, None, None)
            # TODO Maybe remove checksum tag from populse_mia.itial table
            self.session.add_field(COLLECTION_CURRENT, TAG_TYPE,
                                   FIELD_TYPE_STRING, "Path type", True,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_INITIAL, TAG_TYPE,
                                   FIELD_TYPE_STRING, "Path type", True,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_CURRENT, TAG_EXP_TYPE,
                                   FIELD_TYPE_STRING, "Path exp type", True,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_INITIAL, TAG_EXP_TYPE,
                                   FIELD_TYPE_STRING, "Path exp type", True,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_CURRENT, TAG_BRICKS,
                                   FIELD_TYPE_LIST_STRING, "Path bricks", True,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_INITIAL, TAG_BRICKS,
                                   FIELD_TYPE_LIST_STRING, "Path bricks", True,
                                   TAG_ORIGIN_BUILTIN, None, None)

            self.session.add_field(COLLECTION_BRICK, BRICK_NAME,
                                   FIELD_TYPE_STRING, "Brick name", False,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_BRICK, BRICK_INPUTS,
                                   FIELD_TYPE_JSON, "Brick input(s)", False,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_BRICK, BRICK_OUTPUTS,
                                   FIELD_TYPE_JSON, "Brick output(s)", False,
                                   TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_BRICK, BRICK_INIT,
                                   FIELD_TYPE_STRING, "Brick init status",
                                   False, TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_BRICK, BRICK_INIT_TIME,
                                   FIELD_TYPE_DATETIME, "Brick init time",
                                   False, TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_BRICK, BRICK_EXEC,
                                   FIELD_TYPE_STRING, "Brick exec status",
                                   False, TAG_ORIGIN_BUILTIN, None, None)
            self.session.add_field(COLLECTION_BRICK, BRICK_EXEC_TIME,
                                   FIELD_TYPE_DATETIME, "Brick exec time",
                                   False, TAG_ORIGIN_BUILTIN, None, None)

            # Adding default tags for the user mode
            if config.get_user_mode() == True:
                for clinical_tag in CLINICAL_TAGS:
                    if clinical_tag == "Age":
                        field_type = FIELD_TYPE_INTEGER
                    else:
                        field_type = FIELD_TYPE_STRING
                    self.session.add_field(COLLECTION_CURRENT, clinical_tag,
                                           field_type, clinical_tag, True,
                                           TAG_ORIGIN_BUILTIN, None, None)
                    self.session.add_field(COLLECTION_INITIAL, clinical_tag,
                                           field_type, clinical_tag, True,
                                           TAG_ORIGIN_BUILTIN, None, None)

        self.session.commit()
        
        self.properties = self.loadProperties()

        self._unsavedModifications = False
        self.undos = []
        self.redos = []
        self.init_filters()

    def add_clinical_tags(self):
        """Add new clinical tags to the project.

        :returns: list of clinical tags that were added
        """
        return_tags = []
        for clinical_tag in CLINICAL_TAGS:
            if clinical_tag not in self.session.get_fields_names(
                    COLLECTION_CURRENT):
                if clinical_tag == "Age":
                    field_type = FIELD_TYPE_INTEGER
                else:
                    field_type = FIELD_TYPE_STRING
                self.session.add_field(
                    COLLECTION_CURRENT, clinical_tag, field_type,
                    clinical_tag, True, TAG_ORIGIN_BUILTIN, None, None)
                self.session.add_field(
                    COLLECTION_INITIAL, clinical_tag, field_type,
                    clinical_tag, True, TAG_ORIGIN_BUILTIN, None, None)
                for scan in self.session.get_documents(COLLECTION_CURRENT):
                    self.session.add_value(
                        COLLECTION_CURRENT, getattr(scan, TAG_FILENAME),
                        clinical_tag, None)
                    self.session.add_value(
                        COLLECTION_INITIAL, getattr(scan, TAG_FILENAME),
                        clinical_tag, None)
                return_tags.append(clinical_tag)
                self.session.commit()
                
        return return_tags

    def getDate(self):
        """Return the date of creation of the project.

        :returns: string of the date of creation of the project if it's not
        Unnamed project, otherwise empty string
        """

        return self.properties["date"]

    def getFilter(self, filter):
        """Return a Filter object from its name.

        :param filter: Filter name
        :returns: Filter object
        """
        for filterObject in self.filters:
            if filterObject.name == filter:
                return filterObject

    def getFilterName(self):
        """Input box to type the name of the filter to save.

        :returns: Return the name typed
        """

        from PyQt5.QtWidgets import QInputDialog, QLineEdit

        text, ok_pressed = QInputDialog.getText(
            None, "Save a filter", "Filter name: ", QLineEdit.Normal, "")
        if ok_pressed and text != '':
            return text

    def getName(self):
        """Return the name of the project.

        :returns: string of the name of the project if it's not Unnamed
        project,
        otherwise empty string
        """

        return self.properties["name"]

    def getSortedTag(self):
        """Return the sorted tag of the project.

        :returns: string of the sorted tag of the project if it's not Unnamed
        project, otherwise empty string
        """

        return self.properties["sorted_tag"]

    def getSortOrder(self):
        """Return the sort order of the project.

        :returns: string of the sort order of the project if it's not Unnamed
        project, otherwise empty string
        """

        return self.properties["sort_order"]

    def hasUnsavedModifications(self):
        """Return if the project has unsaved modifications or not.

        :returns: boolean, True if the project has pending modifications,
        False otherwise
        """

        return self.unsavedModifications;

    def init_filters(self):
        """Initialize the filters at project opening."""

        self.currentFilter = Filter(None, [], [], [], [], [], "")
        self.filters = []

        filters_folder = os.path.join(self.folder, "filters")

        for filename in glob.glob(os.path.join(filters_folder, '*')):
            filter, extension = os.path.splitext(os.path.basename(filename))
            # make sure this gets closed automatically
            # as soon as we are done reading
            with open(filename, 'r') as f:
                data = json.load(f)
            filter_object = Filter(filter, data["nots"], data["values"],
                                   data["fields"], data["links"],
                                   data["conditions"], data["search_bar_text"])
            self.filters.append(filter_object)

    def loadProperties(self):
        """Load the properties file."""
        with open(os.path.join(
                self.folder, 'properties', 'properties.yml'), 'r') as stream:
            
            try:
                if verCmp(yaml.__version__, '5.1', 'sup'):
                    return yaml.load(stream, Loader=yaml.FullLoader)
                else:    
                    return yaml.load(stream)

            except yaml.YAMLError as exc:
                print(exc)

    def redo(self, table):
        """Redo the last action made by the user on the project.

        :param table: table on which to apply the modifications
        """
        # To avoid circular imports
        from populse_mia.user_interface.data_browser.data_browser import (
            not_defined_value)

        # We can redo if we have an action to make again
        if len(self.redos) > 0:
            to_redo = self.redos.pop()
            self.undos.append(to_redo)
            self.unsavedModifications = True
            # We pop the redo action in the undo stack
            # The first element of the list is the type of action made by
            # the user (add_tag, remove_tags, add_scans, remove_scans,
            # or modified_values)
            action = to_redo[0]

            if action == "add_tag":
                # For adding the tag, we need the tag name,
                # and all its attributes
                tag_to_add = to_redo[1]
                tag_type = to_redo[2]
                tag_unit = to_redo[3]
                tag_default_value = to_redo[4]
                tag_description = to_redo[5]
                values = to_redo[6]  # List of values stored
                # Adding the tag
                self.session.add_field(
                    COLLECTION_CURRENT, tag_to_add, tag_type,
                    tag_description, True, TAG_ORIGIN_USER, tag_unit,
                    tag_default_value)
                self.session.add_field(
                    COLLECTION_INITIAL, tag_to_add, tag_type,
                    tag_description, True, TAG_ORIGIN_USER, tag_unit,
                    tag_default_value)
                # Adding all the values associated
                for value in values:
                    self.session.add_value(
                        COLLECTION_CURRENT, value[0], value[1], value[2])
                    self.session.add_value(
                        COLLECTION_INITIAL, value[0], value[1], value[3])
                column = table.get_index_insertion(tag_to_add)
                table.add_column(column, tag_to_add)

            if action == "remove_tags":
                # To remove the tags, we need the names
                # The second element is a list of the removed tags (Tag class)
                tags_removed = to_redo[1]
                for i in range(0, len(tags_removed)):
                    # We reput each tag in the tag list, keeping
                    # all the tags params
                    tag_to_remove = tags_removed[i][0].field_name
                    self.session.remove_field(
                        COLLECTION_CURRENT, tag_to_remove)
                    self.session.remove_field(
                        COLLECTION_INITIAL, tag_to_remove)
                    column_to_remove = table.get_tag_column(tag_to_remove)
                    table.removeColumn(column_to_remove)

            if action == "add_scans":
                # To add the scans, we need the FileNames and the values
                # associated to the scans
                # The second element is a list of the scans to add
                scans_added = to_redo[1]
                # We add all the scans
                for i in range(0, len(scans_added)):
                    # We remove each scan added
                    scan_to_add = scans_added[i]
                    self.session.add_document(COLLECTION_CURRENT, scan_to_add)
                    self.session.add_document(COLLECTION_INITIAL, scan_to_add)
                    table.scans_to_visualize.append(scan_to_add)
                # We add all the values
                # The third element is a list of the values to add
                values_added = to_redo[2]
                for i in range(0, len(values_added)):
                    value_to_add = values_added[i]
                    self.session.add_value(
                        COLLECTION_CURRENT, value_to_add[0],
                        value_to_add[1], value_to_add[2])
                    self.session.add_value(
                        COLLECTION_INITIAL, value_to_add[0],
                        value_to_add[1], value_to_add[3])
                table.add_rows(self.session.get_documents_names(
                    COLLECTION_CURRENT))

            if action == "remove_scans":
                # To remove a scan, we only need the FileName of the scan
                # The second element is the list of removed scans (Path class)
                scans_removed = to_redo[1]
                for i in range(0, len(scans_removed)):
                    # We reput each scan, keeping the same values
                    scan_to_remove = getattr(
                        scans_removed[i], TAG_FILENAME)
                    self.session.remove_document(
                        COLLECTION_CURRENT, scan_to_remove)
                    self.session.remove_document(
                        COLLECTION_INITIAL, scan_to_remove)
                    table.scans_to_visualize.remove(scan_to_remove)
                    table.removeRow(table.get_scan_row(scan_to_remove))
                    table.itemChanged.disconnect()
                    table.update_colors()
                    table.itemChanged.connect(table.change_cell_color)

            if action == "modified_values":  # Not working
                # To modify the values, we need the cells,
                # and the updated values

                # The second element is a list of modified values
                # (reset or value changed)
                modified_values = to_redo[1]
                table.itemChanged.disconnect()
                for i in range(0, len(modified_values)):
                    # Each modified value is a list of 3 elements:
                    # scan, tag, and old_value
                    value_to_restore = modified_values[i]
                    scan = value_to_restore[0]
                    tag = value_to_restore[1]
                    old_value = value_to_restore[2]
                    new_value = value_to_restore[3]

                    item = table.item(
                        table.get_scan_row(scan), table.get_tag_column(tag))
                    if old_value is None:
                        # Font reput to normal in case it was a not
                        # defined cell
                        font = item.font()
                        font.setItalic(False)
                        font.setBold(False)
                        item.setFont(font)
                    self.session.set_value(
                        COLLECTION_CURRENT, scan, tag, new_value)
                    if new_value is None:
                        font = item.font()
                        font.setItalic(True)
                        font.setBold(True)
                        item.setFont(font)
                        set_item_data(
                            item, not_defined_value, FIELD_TYPE_STRING)
                    else:
                        set_item_data(
                            item, new_value, self.session.get_field(
                                COLLECTION_CURRENT, tag).field_type)
                table.update_colors()
                table.itemChanged.connect(table.change_cell_color)

            if action == "modified_visibilities":
                # To revert the modifications of the visualized tags
                # Old list of columns
                old_tags = self.session.get_shown_tags()
                # List of the tags shown before the modification (Tag objects)
                showed_tags = to_redo[2]
                self.session.set_shown_tags(showed_tags)
                # Columns updated
                table.update_visualized_columns(
                    old_tags, self.session.get_shown_tags())
            
    def reput_values(self, values):
        """Re-put the value objects in the database.

        :param values: List of Value objects
        """

        for i in range(0, len(values)):
            # We reput each value, exactly the same as it was before
            valueToReput = values[i]
            self.session.add_value(
                COLLECTION_CURRENT, valueToReput[0], valueToReput[1],
                valueToReput[2])
            self.session.add_value(
                COLLECTION_INITIAL, valueToReput[0], valueToReput[1],
                valueToReput[3])

    def save_current_filter(self, custom_filters):
        """Save the current filter.

        :param custom_filters: The customized filter
        """

        from PyQt5.QtWidgets import QMessageBox

        (fields, conditions, values, links, nots) = custom_filters
        self.currentFilter.fields = fields
        self.currentFilter.conditions = conditions
        self.currentFilter.values = values
        self.currentFilter.links = links
        self.currentFilter.nots = nots

        # Getting the path
        filters_path = os.path.join(self.folder, "filters")

        # Filters folder created if it does not already exists
        if not os.path.exists(filters_path):
            os.mkdir(filters_path)

        filter_name = self.getFilterName()

        # We save the filter only if we have a filter name from
        # populse_mia.e popup
        if filter_name != None:
            file_path = os.path.join(filters_path, filter_name + ".json")

            if os.path.exists(file_path):
                # Filter already exists
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("The filter already exists in the project")
                msg.setInformativeText(
                    "The project already has a filter named " + filter_name)
                msg.setWindowTitle("Warning")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.buttonClicked.connect(msg.close)
                msg.exec()

            else:
                # Json filter file written
                with open(file_path, 'w') as outfile:

                    new_filter = Filter(
                        filter_name,
                        self.currentFilter.nots,
                        self.currentFilter.values,
                        self.currentFilter.fields,
                        self.currentFilter.links,
                        self.currentFilter.conditions,
                        self.currentFilter.search_bar)

                    json.dump(new_filter.json_format(), outfile)
                    self.filters.append(new_filter)

    def saveConfig(self):
        """Save the changes in the properties file."""

        with open(os.path.join(self.folder, 'properties', 'properties.yml'),
                  'w', encoding='utf8') as configfile:
            yaml.dump(self.properties, configfile,
                      default_flow_style=False, allow_unicode=True)

    def saveModifications(self):
        """Save the pending operations of the project (actions
        still not saved).
        """

        self.saveConfig()
        self.unsavedModifications = False

    def setCurrentFilter(self, filter):
        """Set the current filter of the project.

        :param filter: new Filter object
        """

        self.currentFilter = filter

    def setDate(self, date):
        """Set the date of the project.

        :param date: new date of the project
        """

        self.properties["date"] = date

    def setName(self, name):
        """Set the name of the project if it's not Unnamed project,
        otherwise does nothing.

        :param name: new name of the project
        """

        self.properties["name"] = name

    def setSortedTag(self, tag):
        """Set the sorted tag of the project.

        :param tag: new sorted tag of the project
        """

        old_tag = self.properties["sorted_tag"]
        self.properties["sorted_tag"] = tag
        if old_tag != tag:
            self.unsavedModifications = True

    def setSortOrder(self, order):
        """Set the sort order of the project.

        :param order: new sort order of the project (ascending or descending)
        """

        old_order = self.properties["sort_order"]
        self.properties["sort_order"] = order
        if old_order != order:
            self.unsavedModifications = True

    def undo(self, table):
        """Undo the last action made by the user on the project.

        :param table: table on which to apply the modifications
        """

        # To avoid circular imports
        from populse_mia.user_interface.data_browser.data_browser import (
            not_defined_value)

        # We can undo if we have an action to revert
        if len(self.undos) > 0:
            to_undo = self.undos.pop()
            # We pop the undo action in the redo stack
            self.redos.append(to_undo)
            # The first element of the list is the type of action
            # made by the user (add_tag,
            # remove_tags, add_scans, remove_scans, or modified_values)
            action = to_undo[0]
            self.unsavedModifications = True
            if action == "add_tag":
                # For removing the tag added, we just have to memorize
                # the tag name, and remove it
                tag_to_remove = to_undo[1]
                self.session.remove_field(COLLECTION_CURRENT, tag_to_remove)
                self.session.remove_field(COLLECTION_INITIAL, tag_to_remove)
                column_to_remove = table.get_tag_column(tag_to_remove)
                table.removeColumn(column_to_remove)
            if action == "remove_tags":
                # To reput the removed tags, we need to reput the
                # tag in the tag list,
                # and all the tags values associated to this tag
                # The second element is a list of the removed tags
                # ([Tag row, origin, unit, default_value])
                tags_removed = to_undo[1]

                for i in range(0, len(tags_removed)):
                    # We reput each tag in the tag list, keeping
                    # all the tags params
                    tag_to_reput = tags_removed[i][0]
                    self.session.add_field(
                        COLLECTION_CURRENT, tag_to_reput.field_name,
                        tag_to_reput.field_type, tag_to_reput.description,
                        tag_to_reput.visibility, tag_to_reput.origin,
                        tag_to_reput.unit, tag_to_reput.default_value)
                    self.session.add_field(
                        COLLECTION_INITIAL, tag_to_reput.field_name,
                        tag_to_reput.field_type, tag_to_reput.description,
                        tag_to_reput.visibility, tag_to_reput.origin,
                        tag_to_reput.unit, tag_to_reput.default_value)
                # The third element is a list of tags values (Value class)
                values_removed = to_undo[2]
                self.reput_values(values_removed)
                for i in range(0, len(tags_removed)):
                    # We reput each tag in the tag list,
                    # keeping all the tags params
                    tag_to_reput = tags_removed[i][0]
                    column = table.get_index_insertion(tag_to_reput.field_name)
                    table.add_column(column, tag_to_reput.field_name)
            if action == "add_scans":
                # To remove added scans, we just need their file name
                # The second element is a list of added scans to remove
                scans_added = to_undo[1]
                for i in range(0, len(scans_added)):
                    # We remove each scan added
                    scan_to_remove = scans_added[i]
                    self.session.remove_document(
                        COLLECTION_CURRENT, scan_to_remove)
                    self.session.remove_document(
                        COLLECTION_INITIAL, scan_to_remove)
                    table.removeRow(table.get_scan_row(scan_to_remove))
                    table.scans_to_visualize.remove(scan_to_remove)
                table.itemChanged.disconnect()
                table.update_colors()
                table.itemChanged.connect(table.change_cell_color)
            if action == "remove_scans":
                # To reput a removed scan, we need the scans names,
                # and all the values associated
                # The second element is the list of removed scans (Scan class)
                scans_removed = to_undo[1]
                for i in range(0, len(scans_removed)):
                    # We reput each scan, keeping the same values
                    scan_to_reput = scans_removed[i]
                    self.session.add_document(
                        COLLECTION_CURRENT, getattr(
                            scan_to_reput, TAG_FILENAME))
                    self.session.add_document(
                        COLLECTION_INITIAL, getattr(
                            scan_to_reput, TAG_FILENAME))
                    table.scans_to_visualize.append(getattr(
                        scan_to_reput, TAG_FILENAME))

                # The third element is the list of removed values
                values_removed = to_undo[2]
                self.reput_values(values_removed)
                table.add_rows(self.session.get_documents_names(
                    COLLECTION_CURRENT))
            if action == "modified_values":
                # To revert a value changed in the databrowser,
                # we need two things:
                # the cell (scan and tag, and the old value)
                # The second element is a list of modified values (reset,
                modified_values = to_undo[1]
                # or value changed)
                table.itemChanged.disconnect()
                for i in range(0, len(modified_values)):
                    # Each modified value is a list of 3 elements:
                    # scan, tag, and old_value
                    value_to_restore = modified_values[i]
                    scan = value_to_restore[0]
                    tag = value_to_restore[1]
                    old_value = value_to_restore[2]
                    new_value = value_to_restore[3]
                    item = table.item(
                        table.get_scan_row(scan), table.get_tag_column(tag))
                    if old_value is None:
                        # If the cell was not defined before, we reput it
                        self.session.remove_value(
                            COLLECTION_CURRENT, scan, tag)
                        self.session.remove_value(
                            COLLECTION_INITIAL, scan, tag)
                        set_item_data(
                            item, not_defined_value, FIELD_TYPE_STRING)
                        font = item.font()
                        font.setItalic(True)
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        # If the cell was there before,
                        # we just set it to the old value
                        self.session.set_value(
                            COLLECTION_CURRENT, scan, tag, old_value)
                        set_item_data(
                            item, old_value, self.session.get_field(
                                COLLECTION_CURRENT, tag).field_type)
                        # If the new value is None,
                        # the not defined font must be removed
                        if new_value is None:
                            font = item.font()
                            font.setItalic(False)
                            font.setBold(False)
                            item.setFont(font)
                table.update_colors()
                table.itemChanged.connect(table.change_cell_color)
            if action == "modified_visibilities":
                # To revert the modifications of the visualized tags
                # Old list of columns
                old_tags = self.session.get_shown_tags()
                # List of the tags visibles before the modification
                # (Tag objects)
                visibles = to_undo[1]
                self.session.set_shown_tags(visibles)
                # Columns updated
                table.update_visualized_columns(
                    old_tags, self.session.get_shown_tags())


    @property
    def unsavedModifications(self):
        """Setter for _unsavedModifications."""
        return self._unsavedModifications

    @unsavedModifications.setter
    def unsavedModifications(self, value):
        """ Modify the window title depending of whether the project has
           unsaved modifications or not.

        :param value: boolean
        """
        self._unsavedModifications = value

        try:
            from PyQt5.QtCore import QCoreApplication

            app = QCoreApplication.instance()
            if self._unsavedModifications :
                if app.title()[-1] != "*":
                    app.set_title(app.title()+"*")
            else:
                if app.title()[-1] == "*":
                    app.set_title(app.title()[:-1])
        except ImportError:
            # PyQt is not here ? never mind for what we are doing here.
            pass

    def unsaveModifications(self):
        """Unsave the pending operations of the project."""

        self.unsavedModifications = False

    def files_in_project(self, files):
        """
        Return values in files that are file / directory names within the
        project folder.

        `files` are walked recursively and can be, or contain, lists, tuples,
        sets, dicts (only dict `values()` are considered). Dict keys are
        dropped and all filenames are merged into a single set.

        The returned value is a set of filenames (str).
        """
        proj_dir = os.path.join(os.path.abspath(
            os.path.normpath(self.folder)), '')
        pl = len(proj_dir)

        values = set()
        tval = [files]
        while tval:
            value = tval.pop(0)
            if isinstance(value, (list, tuple, set)):
                tval += value
                continue
            if isinstance(value, dict):
                tval += value.values()
                continue
            if not isinstance(value, str):
                continue
            aval = os.path.abspath(os.path.normpath(value))
            if not aval.startswith(proj_dir):
                continue

            values.add(aval[pl:])

        return values

    def get_data_history(self, path, timepoint=None):
        """
        Get the processing history for the given data file.

        the history dict contains several elements:

        - 'parent_files': set of other data used (directy or indirectly) to
        produce the data.
        - 'processes': processing bricks set from each ancestor data which
        lead to the given one. Elements are process (brick) UUIDs.

        Returns
        -------
        history: dict
        """

        def latest_before(datetimes, timepoint):
            dbest = None
            ibest = None
            for i, d in enumerate(datetimes):
                if d is not None:
                    delta = timepoint - d
                    if (delta >= timedelta(0)
                        and (dbest is None or delta < dbest)):
                        dbest = delta
                        ibest = i
            return ibest

        def latest_brick_before(bricks, timepoint):
            dates = [b[BRICK_EXEC_TIME] for b in bricks]
            return latest_before(dates, timepoint)

        parents = set()
        procs = set()
        proj_dir = os.path.join(os.path.abspath(
            os.path.normpath(self.folder)), '')
        pl = len(proj_dir)

        if timepoint is None:
            timepoint = datetime.now()

        my_path = path
        todo = [(path, timepoint)]
        obsolete = set()

        while todo:
            path, timepoint = todo.pop(0)
            bricks = self.session.get_document(
                COLLECTION_CURRENT, path, fields=[TAG_BRICKS], as_list=True)
            if not bricks or not bricks[0]:
                continue

            bricks = bricks[0]
            # print('bricks:', bricks)
            brick_docs = list(self.session.get_documents(
                COLLECTION_BRICK, document_ids=bricks))
            best = latest_brick_before(brick_docs, timepoint)
            if best is None:
                continue

            brick = brick_docs[best]
            brid = brick[BRICK_ID]

            if path == my_path:
                obsolete = set(b.ID for b in brick_docs
                               if b is not None and b.Exec == 'Done')
            bid = set(b.ID for b in brick_docs)
            dropped = [b for b in bricks if b not in bid]
            obsolete.update(dropped)

            #for brid in reversed(bricks):  # process from newer to older

            if brid in procs:
                continue
            procs.add(brid)
            #brick = self.session.get_document(COLLECTION_BRICK, brid)
            if brick.Exec != 'Done':
                # not run, this brick has not produced outputs
                continue
            brick_timepoint = brick[BRICK_EXEC_TIME]

            inputs = brick[BRICK_INPUTS]
            values = []
            tval = list(inputs.values())
            while tval:
                value = tval.pop(0)
                if isinstance(value, list):
                    tval += value
                    continue
                if not isinstance(value, str):
                    continue
                aval = os.path.abspath(os.path.normpath(value))
                if not aval.startswith(proj_dir):
                    continue

                values.append(aval[pl:])

            values = [value for value in values
                      if value not in parents]
            parents.update(values)
            todo += [(v, brick_timepoint) for v in values]

        obsolete = obsolete.difference(procs)

        return {'parent_files': parents,
                'processes': procs,
                'obsolete': obsolete}

    def update_data_history(self, data):
        """
        Cleanup earlier history of given data by removing in their bricks list
        those which correspond to obsolete runs (data has been re-written by
        more recent runs). This function only updates data status (bricks
        list), it does not remove obsolete bricks from the database.

        Returns
        -------
        obsolete: set
            set of obsolete bricks thay may become orphan.
        """
        #
        scan_bricks = list(self.session.get_documents(
            COLLECTION_CURRENT, document_ids=list(data),
            fields=[TAG_FILENAME, TAG_BRICKS], as_list=True))
        scan_bricks = {brick[0]: brick[1] for brick in scan_bricks
                       if brick and brick[0] is not None}

        obsolete = set()
        for output in data:
            old_bricks = scan_bricks.get(output)
            o_hist = self.get_data_history(output)
            obsolete.update(o_hist['obsolete'])
            if old_bricks:
                new_bricks = [brid for brid in old_bricks
                              if brid in o_hist['processes']]
                if len(new_bricks) != len(old_bricks):
                    print('update file history for:', output, ':', old_bricks,
                          '->', new_bricks)
                    self.session.set_value(
                        COLLECTION_CURRENT, output, TAG_BRICKS, new_bricks)

        return obsolete


    def finished_bricks(self, engine, pipeline=None, include_done=False):
        """
        """
        bricks = self.get_finished_bricks_in_workflows(engine)
        if pipeline:
            pbricks = self.get_finished_bricks_in_pipeline(engine, pipeline)
            pbricks.update(bricks)
            bricks = pbricks

        # filter jobs actually in MIA database
        docs = self.session.get_documents(
            COLLECTION_BRICK, document_ids=list(bricks.keys()),
            fields=[BRICK_ID, BRICK_EXEC, BRICK_OUTPUTS], as_list=True)
        docs = {brid: {'brick_exec': brick_exec, 'outputs': outputs}
                for brid, brick_exec, outputs in docs
                if include_done or brick_exec == 'Not Done'}

        def updated(d1, d2):
            d1.update(d2)
            return d1

        bricks = {brid: updated(value, docs[brid])
                  for brid, value in bricks.items() if brid in docs}

        # get complete list of outputs to be updated in the database
        outputs = set()
        proj_dir = os.path.join(os.path.abspath(os.path.normpath(
            self.folder)), '')
        lp = len(proj_dir)

        def _update_set(outputs, output):
            ''' update the outputs set with file/dir names in output, relative
            to the project directory '''
            todo = [output]
            while todo:
                output = todo.pop(0)
                if isinstance(output, (list, set, tuple)):
                    todo += output
                elif isinstance(output, str):
                    path = os.path.abspath(os.path.normpath(output))
                    if path.startswith(proj_dir): # and os.path.exists(path):
                        # record only existing files
                        output = path[lp:]
                        outputs.add(output)

        procs = {}

        for brid, brdesc in bricks.items():
            out_data = brdesc['outputs']
            for param, output in out_data.items():
                _update_set(outputs, output)

        return {'bricks': bricks, 'outputs': outputs}

    def get_finished_bricks_in_workflows(self, engine):
        """
        """
        import soma_workflow.client as swclient
        from soma_workflow import constants

        swm = engine.study_config.modules['SomaWorkflowConfig']
        swm.connect_resource(engine.connected_to())
        controller = swm.get_workflow_controller()

        jobs = {}

        for wf_id in controller.workflows():
            wf_st = controller.workflow_elements_status(wf_id)

            finished_jobs = {}
            for job_st in wf_st[0]:
                job_id = job_st[0]
                if job_st[1] != 'done' or job_st[3][0] != 'finished_regularly':
                    continue
                finished_jobs[job_id] = job_st

            if not finished_jobs:
                continue

            wf = controller.workflow(wf_id)
            for job in wf.jobs:
                brid = getattr(job, 'uuid', None)
                if not brid:
                    continue
                # get engine job
                ejob = wf.job_mapping[job]
                job_id = ejob.job_id
                status = finished_jobs.get(job_id, None)
                if not status:
                    continue

                jobs[brid] = {'workflow': wf_id,
                              'job': job,
                              'job_id': job_id,
                              'swf_status': status}

        return jobs

    def get_finished_bricks_in_pipeline(self, engine, pipeline):
        """
        """
        nodes_list = [n for n in pipeline.nodes.items()
                      if n[0] != ''
                          and pipeline_tools.is_node_enabled(
                              pipeline, n[0], n[1])]

        all_nodes = list(nodes_list)
        while nodes_list:
            node_name, node = nodes_list.pop(0)
            if hasattr(node, 'process'):
                process = node.process

                if isinstance(node, PipelineNode):
                    new_nodes = [
                        n for n in process.nodes.items()
                        if n[0] != ''
                            and pipeline_tools.is_node_enabled(
                                process, n[0], n[1])]
                    nodes_list += new_nodes
                    all_nodes += new_nodes

        procs = {}

        for node_name, node in all_nodes:
            if isinstance(node, ProcessNode):
                process = node.process
                brid = getattr(process, 'uuid', None)
                if brid is not None:
                    procs[brid] = {'process': process}

        return procs

    def get_orphan_bricks(self, bricks=None):
        """
        """
        orphan = set()
        orphan_weak_files = set()
        used_bricks = set()
        if not isinstance(bricks, list):
            bricks = list(bricks)

        brick_docs = self.session.get_documents(
            COLLECTION_BRICK, document_ids=bricks,
            fields=[BRICK_ID, BRICK_OUTPUTS], as_list=True)

        proj_dir = os.path.join(os.path.abspath(os.path.normpath(
            self.folder)), '')
        lp = len(proj_dir)

        for brick in brick_docs:
            brid = brick[0]
            if brid is None:
                continue
            if brick[1] is None:
                orphan.add(brid)
                continue

            todo = list(brick[1].values())
            values = set()
            while todo:
                value = todo.pop(0)
                if isinstance(value, (list, set, tuple)):
                    todo += value
                elif isinstance(value, str):
                    path = os.path.abspath(os.path.normpath(value))
                    if path.startswith(proj_dir):
                        value = path[lp:]
                        values.add(value)
            docs = self.session.get_documents(
                COLLECTION_CURRENT, document_ids=list(values),
                fields=[TAG_FILENAME, TAG_BRICKS], as_list=True)
            used = False
            orphan_files = set()
            for doc in docs:
                if doc[1] and brid in doc[1]:
                    if doc[0].startswith('scripts/'):
                        # script files are "weak" and should not prevent
                        # brick deletion.
                        orphan_files.add(doc[0])
                        continue
                    used = True
                    used_bricks.add(brid)
                    break
            if not used:
                orphan.add(brid)
                orphan_weak_files.update(orphan_files)
        if bricks:
            orphan.update(brid for brid in bricks if brid not in used_bricks)

        return (orphan, orphan_weak_files)

    def cleanup_orphan_bricks(self, bricks=None):
        """
        Remove orphan bricks frol the database
        """
        obsolete, orphan_files = self.get_orphan_bricks(bricks)
        print('really orphan:', obsolete)
        for brick in obsolete:
            print('remove obsolete brick:', brick)
            try:
                self.session.remove_document(COLLECTION_BRICK, brick)
            except ValueError:
                pass  # malformed database, the brick doesn't exist
        for doc in orphan_files:
            print('remove orphan file:', doc)
            try:
                self.session.remove_document(COLLECTION_CURRENT, doc)
                self.session.remove_document(COLLECTION_INITIAL, doc)
            except ValueError:
                pass  # malformed database, the file doesn't exist
            if os.path.exists(os.path.join(self.folder, doc)):
                os.unlink(os.path.join(self.folder, doc))

