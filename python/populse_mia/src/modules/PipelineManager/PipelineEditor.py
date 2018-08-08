#!/usr/bin/python3

import sys

from PyQt5 import QtGui, QtWidgets, QtCore
import os
import six
import yaml

from capsul.api import get_process_instance, Process
from capsul.pipeline import pipeline_tools
from .CAPSUL_Files.pipeline_developper_view import PipelineDevelopperView

from PipelineManager.NodeController import FilterWidget
from PopUps.Ui_Dialog_Close_Pipeline import Ui_Dialog_Close_Pipeline

if sys.version_info[0] >= 3:
    unicode = str
    def values(d):
        return list(d.values())
else:
    def values(d):
        return d.values()


class PipelineEditorTabs(QtWidgets.QTabWidget):
    pipeline_saved = QtCore.pyqtSignal(str)
    node_clicked = QtCore.Signal(str, Process)

    def __init__(self, project, scan_list):
        super(PipelineEditorTabs, self).__init__()

        self.project = project
        self.setStyleSheet('QTabBar{font-size:12pt;font-family:Arial;text-align: center;color:black;}')
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.scan_list = scan_list

        self.undos = {}
        self.redos = {}

        p_e = PipelineEditor(self.project)
        p_e.node_clicked.connect(self.emit_node_clicked)
        p_e.pipeline_saved.connect(self.emit_pipeline_saved)
        p_e.pipeline_modified.connect(self.update_history)
        p_e.edit_sub_pipeline.connect(self.open_sub_pipeline)
        p_e.open_filter.connect(self.open_filter)
        p_e.export_to_db_scans.connect(self.export_to_db_scans)

        self.addTab(p_e, "New Pipeline")
        self.undos["New Pipeline"] = []
        self.redos["New Pipeline"] = []
        tb = QtWidgets.QToolButton()
        tb.setText('+')
        tb.clicked.connect(self.new_tab)
        self.addTab(QtWidgets.QLabel('Add tabs by pressing "+"'), str())
        self.setTabEnabled(1, False)
        self.tabBar().setTabButton(1, QtWidgets.QTabBar.RightSide, tb)

    def new_tab(self, loaded=False):
        p_e = PipelineEditor(self.project)
        p_e.node_clicked.connect(self.emit_node_clicked)
        p_e.pipeline_saved.connect(self.emit_pipeline_saved)
        p_e.pipeline_modified.connect(self.update_history)
        p_e.edit_sub_pipeline.connect(self.open_sub_pipeline)
        p_e.open_filter.connect(self.open_filter)
        p_e.export_to_db_scans.connect(self.export_to_db_scans)

        if not loaded:
            idx = 1
            while True and idx < 20:
                name = "New Pipeline {0}".format(idx)
                if name in self.undos.keys():
                    idx += 1
                    continue
                else:
                    break
            self.undos[name] = []
            self.redos[name] = []
        else:
            name = "New pipeline"
        self.insertTab(self.count()-1, p_e, name)
        self.setCurrentIndex(self.count()-2)

    def close_tab(self, idx):

        filename = self.get_filename_by_index(idx)

        if self.tabText(idx)[-2:] == " *":
            pop_up_close = Ui_Dialog_Close_Pipeline(filename)
            pop_up_close.save_as_signal.connect(self.save_pipeline)
            pop_up_close.exec()
            can_exit = pop_up_close.can_exit()

            if pop_up_close.bool_save_as:
                if idx == self.currentIndex():
                    self.setCurrentIndex(max(0, self.currentIndex() - 1))
                self.removeTab(idx)
                return

        else:
            can_exit = True

        if not can_exit:
            return

        del self.undos[filename]
        del self.redos[filename]

        if idx == self.currentIndex():
            self.setCurrentIndex(max(0, self.currentIndex()-1))
        self.removeTab(idx)

    def set_current_editor_by_name(self, tab_name):
        self.setCurrentWidget(self.findChild(QtWidgets.QWidget, tab_name))

    def get_current_editor(self):
        return self.widget(self.currentIndex())

    def get_filename_by_index(self, idx):
        if self.tabText(idx)[-2:] == " *":
            return self.tabText(idx)[:-2]
        else:
            return self.tabText(idx)

    def get_current_filename(self):
        if self.tabText(self.currentIndex())[-2:] == " *":
            return self.tabText(self.currentIndex())[:-2]
        else:
            return self.tabText(self.currentIndex())

    def get_current_pipeline(self):
        return self.get_current_editor().scene.pipeline

    def save_pipeline(self):
        old_filename = self.get_current_filename()
        new_file_name = self.get_current_editor().save_pipeline()

        if new_file_name and old_filename != new_file_name:
            self.setTabText(self.currentIndex(), os.path.basename(new_file_name))
            undos = self.undos[old_filename]
            redos = self.redos[old_filename]

            del self.undos[old_filename]
            del self.redos[old_filename]

            self.undos[new_file_name] = undos
            self.redos[new_file_name] = redos

    def load_pipeline(self, filename=None):
        if not filename:
            # If there is only one opened PipelineEditor
            if self.count() == 2:
                # If the PipelineEditor has been edited
                if len(self.widget(0).scene.pipeline.nodes.keys()) > 1:
                    self.new_tab(loaded=True)
                    filename = self.widget(1).load_pipeline()
                    self.setCurrentIndex(1)
                else:
                    filename = self.widget(0).load_pipeline()
            else:
                self.new_tab(loaded=True)
                filename = self.widget(self.count()-2).load_pipeline()
                self.setCurrentIndex(self.count()-2)
        if filename:
            self.setTabText(self.currentIndex(), os.path.basename(filename))
            self.undos[os.path.basename(filename)] = []
            self.redos[os.path.basename(filename)] = []

    def load_pipeline_parameters(self):
        self.get_current_editor().load_pipeline_parameters()

    def save_pipeline_parameters(self):
        self.get_current_editor().save_pipeline_parameters()

    def emit_node_clicked(self, node_name, process):
        self.node_clicked.emit(node_name, process)

    def emit_pipeline_saved(self, filename):
        self.setTabText(self.currentIndex(), os.path.basename(filename))
        self.pipeline_saved.emit(filename)

    def update_history(self, developper_view):
        self.undos[self.get_current_filename()] = developper_view.undos
        self.redos[self.get_current_filename()] = developper_view.redos
        file_name = self.get_current_filename()
        if file_name[-2:] != " *":
            self.setTabText(self.currentIndex(), file_name + " *")

    def reset_pipeline(self):
        self.get_current_editor()._reset_pipeline()

    def update_scans_list(self):
        for i in range(self.count()-1):
            pipeline = self.widget(i).scene.pipeline
            if hasattr(pipeline, "nodes"):
                for node_name, node in pipeline.nodes.items():
                    if node_name == "":
                        for plug_name, plug in node.plugs.items():
                            if plug_name == "database_scans":
                                node.set_plug_value(plug_name, self.scan_list)

    def open_sub_pipeline(self, sub_pipeline):
        """
        Opens a pipeline node in a new editor tab.
        :param sub_pipeline: the pipeline to open
        :return:
        """

        def get_path(name, dictionary, prev_paths=None):
            """
            This recursive function returns the package path to the selected sub-pipeline.
            :param name: name of the sub-pipeline
            :param dictionary: package tree (read from process_config.yml)
            :param prev_paths: paths of the last call of this function
            :return: the package path of the sub-pipeline if it is found, else None
            """
            if prev_paths is None:
                prev_paths = []

            # new_paths is a list containing the packages to the desired module
            new_paths = prev_paths.copy()
            for idx, (key, value) in enumerate(dictionary.items()):
                # If the value is a string, this means that this is a "leaf" of the tree
                # so the key is a module name.
                if isinstance(value, str):
                    if key == name:
                        new_paths.append(key)
                        return new_paths
                    else:
                        continue
                # Else, this means that the value is still a dictionary, we are still in the tree
                else:
                    new_paths.append(key)
                    final_res = get_path(name, value, new_paths)
                    # final_res is None if the module name has not been found in the tree
                    if final_res:
                        return final_res
                    else:
                        new_paths = prev_paths.copy()

        def find_filename(paths_list, packages_list, file_name):
            """
            Finds the corresponding file name in the paths list of process_config.yml.
            :param paths_list: list of all the paths contained in process_config.yml
            :param packages_list: packages path
            :param file_name: name of the sub-pipeline
            :return: name of the corresponding file if it is found, else None
            """
            filenames = [file_name + '.py', file_name + '.xml']
            for filename in filenames:
                for path in paths_list:
                    new_path = path
                    for package in packages_list:
                        new_path = os.path.join(new_path, package)

                    # Making sure that the filename is found (has somme issues with case sensitivity)
                    for f in os.listdir(new_path):
                        new_file = os.path.join(new_path, f)
                        if os.path.isfile(new_file) and f.lower() == filename.lower():
                            return new_file

        # Reading the process configuration file
        with open(os.path.join('..', '..', 'properties', 'process_config.yml'), 'r') as stream:
            try:
                dic = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                dic = {}

        sub_pipeline_name = sub_pipeline.name

        # get_path returns a list that is the package path to the sub_pipeline file
        sub_pipeline_list = get_path(sub_pipeline_name, dic['Packages'])
        sub_pipeline_name = sub_pipeline_list.pop()

        # Finding the real sub-pipeline filename
        sub_pipeline_filename = find_filename(dic['Paths'], sub_pipeline_list, sub_pipeline_name)
        if sub_pipeline_filename:
            pipeline = get_process_instance(sub_pipeline_filename)
            if pipeline is not None:
                sub_pipeline_basename = os.path.basename(sub_pipeline_filename)

                # Checking if the sub-pipeline is not already opened in an editor tab
                pipeline_opened = False
                for opened_filename in self.undos.keys():
                    if opened_filename == sub_pipeline_basename:
                        pipeline_opened = True
                        break

                if pipeline_opened:
                    self.set_current_editor_by_name(sub_pipeline_basename)
                else:
                    self.new_tab(loaded=True)
                    self.setCurrentIndex(self.count() - 2)
                    self.get_current_editor().set_pipeline(pipeline)
                    self.get_current_editor()._pipeline_filename = sub_pipeline_filename
                    self.load_pipeline(sub_pipeline_basename)

    def open_filter(self, node_name):
        node = self.get_current_pipeline().nodes[node_name]
        filter_widget = FilterWidget(self.project, node_name, node, self)
        filter_widget.show()

    def export_to_db_scans(self, node_name):
        # If database_scans is already a pipeline global input, the plug cannot be
        # exported. A link as to be added between database_scans and the input of the filter.
        if 'database_scans' in self.get_current_pipeline().user_traits().keys():
            self.get_current_pipeline().add_link('database_scans->{0}.input'.format(node_name))
        else:
            self.get_current_pipeline().export_parameter(
                node_name, 'input',
                pipeline_parameter='database_scans')
        self.get_current_editor().scene.update_pipeline()


class PipelineEditor(PipelineDevelopperView):

    pipeline_saved = QtCore.pyqtSignal(str)
    pipeline_modified = QtCore.pyqtSignal(PipelineDevelopperView)

    def __init__(self, project):
        PipelineDevelopperView.__init__(self, pipeline=None, allow_open_controller=True,
                                        show_sub_pipelines=True, enable_edition=True)

        self.project = project

        # Undo/Redo
        self.undos = []
        self.redos = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('component/name'):
            event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('component/name'):
            event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasFormat('component/name'):
            self.click_pos = QtGui.QCursor.pos()
            path = bytes(event.mimeData().data('component/name'))
            self.find_process(path.decode('utf8'))

    def find_process(self, path):
        """
        Finds the dropped process in the system's paths.
        :param path: class's path (e.g. "nipype.interfaces.spm.Smooth") (str)
        :return:
        """
        package_name, process_name = os.path.splitext(path)
        process_name = process_name[1:]
        __import__(package_name)
        pkg = sys.modules[package_name]
        for name, instance in sorted(list(pkg.__dict__.items())):
            if name == process_name:
                try:
                    process = get_process_instance(instance)
                except Exception as e:
                    print(e)
                    return
                else:
                    self.add_process(instance)

    def update_history(self, history_maker, from_undo, from_redo):
        """
        Updates the history for undos and redos. This method is called
        after each action in the PipelineEditor.
        :param history_maker: list that contains information about what has been done
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """

        if from_undo:
            self.redos.append(history_maker)
        else:
            self.undos.append(history_maker)
            # If the action does not come from an undo or a redo,
            # the redos has to be cleared
            if not from_redo:
                self.redos.clear()

        self.pipeline_modified.emit(self)

    def add_process(self, class_process, node_name=None, from_undo=False, from_redo=False, links=[]):
        """
        Adds a process to the pipeline.
        :param class_process: process class's name (str)
        :param node_name: name of the corresponding node (using when undo/redo) (str)
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :param links: list of links (using when undo/redo)
        :return:
        """
        pipeline = self.scene.pipeline
        if not node_name:
            class_name = class_process.__name__
            i = 1

            node_name = class_name.lower() + str(i)

            while node_name in pipeline.nodes and i < 100:
                i += 1
                node_name = class_name.lower() + str(i)

            process_to_use = class_process()

        else:
            process_to_use = class_process

        try:
            process = get_process_instance(
                process_to_use)
        except Exception as e:
            print(e)
            return

        pipeline.add_process(node_name, process)

        # Capsul update
        node = pipeline.nodes[node_name]
        gnode = self.scene.add_node(node_name, node)
        gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

        # If the process is added from a undo, all the links that were connected
        # to the corresponding node has to be reset
        for link in links:
            source = link[0]
            dest = link[1]
            active = link[2]
            weak = link[3]
            self.scene.add_link(source, dest, active, weak)
            # Writing a string to represent the link
            source_parameters = ".".join(source)
            dest_parameters = ".".join(dest)
            link_to_add = "->".join((source_parameters, dest_parameters))
            self.scene.pipeline.add_link(link_to_add)
            self.scene.update_pipeline()

        # For history
        history_maker = ["add_process"]

        if from_undo:
            # Adding the arguments to make the redo correctly
            history_maker.append(node_name)
        else:
            # Adding the arguments to make the undo correctly
            history_maker.append(node_name)
            history_maker.append(class_process)

        self.update_history(history_maker, from_undo, from_redo)

    def del_node(self, node_name=None, from_undo=False, from_redo=False):
        """
        Deletes a node.
        :param node_name: name of the corresponding node (using when undo/redo) (str)
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """

        pipeline = self.scene.pipeline
        if not node_name:
            node_name = self.current_node_name
        node = pipeline.nodes[node_name]

        # Collecting the links from the node that is being deleted
        links = []
        for plug_name, plug in node.plugs.items():
            for link_to in plug.links_to:
                (dest_node_name, dest_parameter, dest_node, dest_plug,
                 weak_link) = link_to
                active = plug.activated

                # Looking for the name of dest_plug in dest_node
                dest_plug_name = None
                for plug_name_d, plug_d in dest_node.plugs.items():
                    if plug_d == dest_plug:
                        dest_plug_name = plug_name_d
                        break

                link_to_add = [(node_name, plug_name)]
                link_to_add.append((dest_node_name, dest_plug_name))
                link_to_add.append(active)
                link_to_add.append(weak_link)

                links.append(link_to_add)

            for link_from in plug.links_from:
                (source_node_name, source_parameter, source_node, source_plug,
                 weak_link) = link_from
                active = plug.activated

                # Looking for the name of source_plug in source_node
                source_plug_name = None
                for plug_name_d, plug_d in source_node.plugs.items():
                    if plug_d == source_plug:
                        source_plug_name = plug_name_d
                        break

                link_to_add = [(source_node_name, source_plug_name)]
                link_to_add.append((node_name, plug_name))
                link_to_add.append(active)
                link_to_add.append(weak_link)

                links.append(link_to_add)

        # Calling the original method
        PipelineDevelopperView.del_node(self, node_name)

        # For history
        history_maker = ["delete_process", node_name, node.process, links]

        self.update_history(history_maker, from_undo, from_redo)

    def _release_grab_link(self, event, ret=False):
        """
        Method called when a link is released.
        :param event: mouse event corresponding to the release
        :param ret: boolean that is set to True in the original method to return the link
        :return:
        """
        # Calling the original method
        link = PipelineDevelopperView._release_grab_link(self, event, ret=True)

        # For history
        history_maker = ["add_link", link]

        self.update_history(history_maker, from_undo=False, from_redo=False)

    def add_link(self, source, dest, active, weak, from_undo=False, from_redo=False):
        """
        Adds a link between two nodes.
        :param source: tuple containing the node and plug source names
        :param dest: tuple containing the node and plug destination names
        :param active: boolean that is True if the link is activated
        :param weak: boolean that is True if the link is weak
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """
        self.scene.add_link(source, dest, active, weak)

        # Writing a string to represent the link
        source_parameters = ".".join(source)
        dest_parameters = ".".join(dest)
        link = "->".join((source_parameters, dest_parameters))

        self.scene.pipeline.add_link(link)
        self.scene.update_pipeline()

        # For history
        history_maker = ["add_link", link]

        self.update_history(history_maker, from_undo, from_redo)

    def _del_link(self, link=None, from_undo=False, from_redo=False):
        """
        Deletes a link.
        :param link: string representation of a link (e.g. "process1.out->process2.in")
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """
        if not link:
            link = self._current_link
        else:
            self._current_link = link

        (source_node_name, source_plug_name, source_node,
         source_plug, dest_node_name, dest_plug_name, dest_node,
         dest_plug) = self.scene.pipeline.parse_link(link)

        (dest_node_name, dest_parameter, dest_node, dest_plug,
         weak_link) = list(source_plug.links_to)[0]

        active = source_plug.activated and dest_plug.activated

        # Calling the original method
        PipelineDevelopperView._del_link(self)

        # For history
        history_maker = ["delete_link", (source_node_name, source_plug_name),
                         (dest_node_name, dest_plug_name), active, weak_link]

        self.update_history(history_maker, from_undo, from_redo)

    def export_plugs(self, inputs=True, outputs=True, optional=False, from_undo=False, from_redo=False):
        """
        STILL IN PROGRESS.
        :param inputs:
        :param outputs:
        :param optional:
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """
        # TODO: TO IMPROVE
        # For history
        history_maker = ["export_plugs"]

        for node_name in self.scene.pipeline.nodes:
            if node_name != "":
                history_maker.append(node_name)

        self.update_history(history_maker, from_undo, from_redo)

        PipelineDevelopperView.export_plugs(self, inputs, outputs, optional)

    def update_node_name(self, old_node, old_node_name, new_node_name, from_undo=False, from_redo=False):
        """
        Updates a node name.
        :param old_node: Node object to change
        :param old_node_name: original name of the node (str)
        :param new_node_name: new name of the node (str)
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """
        pipeline = self.scene.pipeline

        # Removing links of the selected node and copy the origin/destination
        links_to_copy = []
        for source_parameter, source_plug \
                in six.iteritems(old_node.plugs):
            for (dest_node_name, dest_parameter, dest_node, dest_plug,
                 weak_link) in source_plug.links_to.copy():
                pipeline.remove_link(old_node_name + "." + source_parameter + "->"
                                     + dest_node_name + "." + dest_parameter)
                links_to_copy.append(("to", source_parameter, dest_node_name, dest_parameter))

            for (dest_node_name, dest_parameter, dest_node, dest_plug,
                 weak_link) in source_plug.links_from.copy():
                pipeline.remove_link(dest_node_name + "." + dest_parameter + "->"
                                     + old_node_name + "." + source_parameter)
                links_to_copy.append(("from", source_parameter, dest_node_name, dest_parameter))

        # Creating a new node with the new name and deleting the previous one
        pipeline.nodes[new_node_name] = pipeline.nodes[old_node_name]
        del pipeline.nodes[old_node_name]

        # Setting the same links as the original node
        for link in links_to_copy:

            if link[0] == "to":
                pipeline.add_link(new_node_name + "." + link[1] + "->"
                                  + link[2] + "." + link[3])
            elif link[0] == "from":
                pipeline.add_link(link[2] + "." + link[3] + "->"
                                  + new_node_name + "." + link[1])

        # Updating the pipeline
        pipeline.update_nodes_and_plugs_activation()

        # For history
        history_maker = ["update_node_name", pipeline.nodes[new_node_name], new_node_name, old_node_name]

        self.update_history(history_maker, from_undo, from_redo)

    def update_plug_value(self, node_name, new_value, plug_name, value_type, from_undo=False, from_redo=False):
        """
        Updates plug value.
        :param node_name: name of the node (str)
        :param new_value: new value to set to the plug
        :param plug_name: name of the plug to change (str)
        :param value_type: type of the new value
        :param from_undo: boolean that is True if the action has been made using an undo
        :param from_redo: boolean that is True if the action has been made using a redo
        :return:
        """
        old_value = self.scene.pipeline.nodes[node_name].get_plug_value(plug_name)
        self.scene.pipeline.nodes[node_name].set_plug_value(plug_name, value_type(new_value))

        # For history
        history_maker = ["update_plug_value", node_name, old_value, plug_name, value_type]

        self.update_history(history_maker, from_undo, from_redo)

    def save_pipeline(self):
        '''
                Ask for a filename using the file dialog, and save the pipeline as a
                XML or python file.
                '''
        pipeline = self.scene.pipeline
        folder = os.path.join('..', 'modules', 'PipelineManager', 'Processes', 'User_processes')
        filename = QtWidgets.QFileDialog.getSaveFileName(
            None, 'Save the pipeline', folder,
            'Compatible files (*.xml *.py);; All (*)')[0]
        if filename:
            posdict = dict([(key, (value.x(), value.y())) \
                            for key, value in six.iteritems(self.scene.pos)])
            old_pos = pipeline.node_position
            pipeline.node_position = posdict
            pipeline_tools.save_pipeline(pipeline, filename)
            self._pipeline_filename = unicode(filename)
            pipeline.node_position = old_pos

            self.pipeline_saved.emit(filename)
            return filename


