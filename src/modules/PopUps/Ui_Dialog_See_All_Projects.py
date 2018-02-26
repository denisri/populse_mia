from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QDialog, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, \
    QVBoxLayout, QMessageBox, QHeaderView
from PyQt5.QtGui import QIcon
import os
from ProjectManager import controller
from DataBase.DataBase import DataBase

class Ui_Dialog_See_All_Projects(QDialog):
    """
    Is called when the user wants to create a new project
    """

    # Signal that will be emitted at the end to tell that a new project has been opened
    signal_create_project = pyqtSignal()

    def __init__(self, savedProjects, mainWindow):
        super().__init__()

        self.mainWindow = mainWindow

        self.setWindowTitle('See all saved projects')
        self.setMinimumWidth(500)

        ############################### TREE WIDGET ###############################

        self.label = QLabel()
        self.label.setText('List of saved projects')

        self.treeWidget = QTreeWidget()
        self.treeWidget.setColumnCount(3)
        self.treeWidget.setHeaderLabels(['Name', 'Path', 'State'])
        #self.treeWidget.setSelectionModel(QItemSelectionModel.ClearAndSelect)

        i = -1
        for path in savedProjects.pathsList:
            i += 1
            text = os.path.basename(path)
            wdg = QTreeWidgetItem()
            wdg.setText(0, text)
            wdg.setText(1, os.path.abspath(path))
            wdg.setIcon(2, self.checkState(path, text))

            self.treeWidget.addTopLevelItem(wdg)

            #self.treeWidget.resizeColumnsToContents(i)


        hd = self.treeWidget.header()
        hd.setSectionResizeMode(QHeaderView.ResizeToContents)

        ############################### BUTTONS ###############################

        # The 'Open project' push button
        self.pushButtonOpenProject = QPushButton("Open project")
        self.pushButtonOpenProject.setObjectName("pushButton_ok")
        self.pushButtonOpenProject.clicked.connect(lambda: self.retranslateUi(self.itemToPath()))

        # The 'Cancel' push button
        self.pushButtonCancel = QPushButton("Cancel")
        self.pushButtonCancel.setObjectName("pushButton_cancel")
        self.pushButtonCancel.clicked.connect(self.close)

        ############################### LAYOUTS ###############################

        self.hBoxButtons = QHBoxLayout()
        self.hBoxButtons.addStretch(1)
        self.hBoxButtons.addWidget(self.pushButtonOpenProject)
        self.hBoxButtons.addWidget(self.pushButtonCancel)

        self.vBox = QVBoxLayout()
        self.vBox.addWidget(self.label)
        self.vBox.addWidget(self.treeWidget)
        self.vBox.addLayout(self.hBoxButtons)

        self.setLayout(self.vBox)

    def checkState(self, path, text):
        """ Checks if the project still exists and returns the corresponding icon """
        if os.path.isfile(os.path.join(path, text, text + ".json")):
            icon = QIcon(os.path.join('..', 'sources_images', 'green_v.png'))
        else:
            icon = QIcon(os.path.join('..', 'sources_images', 'red_cross.png'))
        return icon

    def itemToPath(self):
        nb_items = len(self.treeWidget.selectedItems())
        if nb_items == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Please select a project to open")
            msg.setWindowTitle("Warning")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.buttonClicked.connect(msg.close)
            msg.exec()
            return ""
        else:
            item = self.treeWidget.selectedItems()[0]
            text = item.text(1)
            return text

    def retranslateUi(self, file_name):
        if file_name != "":
            entire_path = os.path.abspath(file_name)
            self.path, self.name = os.path.split(entire_path)
            #self.path = entire_path
            self.relative_path = os.path.relpath(file_name)

            # If the file exists
            if os.path.exists(os.path.join(self.relative_path, self.name, self.name + '.json')):
                controller.open_project(self.name, self.relative_path)
                # DATABASE
                self.mainWindow.database = DataBase(self.relative_path)
                self.mainWindow.data_browser.update_database(self.mainWindow.database)

                self.accept()
                self.close()
                # A signal is emitted to tell that the project has been created
                self.signal_create_project.emit()
