#! /usr/bin/python3
# -*- coding: utf-8 -*- # Character encoding, recommended

import sys
import os

from PyQt5.QtCore import QDir, QLockFile
from PyQt5.QtWidgets import QApplication
from MainWindow.Main_Window import Main_Window
from Project.Project import Project
from SoftwareProperties.Config import Config

imageViewer = None

"""
@atexit.register
"""
def clean_up():
    '''
    Cleans up the software during "normal" closing
    '''

    global imageViewer

    print("clean up done")

    config = Config()
    opened_projects = config.get_opened_projects()
    opened_projects.remove(imageViewer.project.folder)
    config.set_opened_projects(opened_projects)
    imageViewer.remove_raw_files_useless()

def launch_mia():

    global imageViewer

    def my_excepthook(type, value, tback):
        # log the exception here

        print("excepthook")

        clean_up()

        # then call the default handler
        sys.__excepthook__(type, value, tback)

        sys.exit(1)

    sys.excepthook = my_excepthook

    # Working from the scripts directory
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    lock_file = QLockFile(QDir.temp().absoluteFilePath('lock_file_populse_mia.lock'))
    if not lock_file.tryLock(100):
        # Software already opened in another instance
        pass
    else:
        # No instances of the software is opened, the list of opened projects can be cleared
        config = Config()
        config.set_opened_projects([])

    app = QApplication(sys.argv)

    project = Project(None, True)

    imageViewer = Main_Window(project)
    imageViewer.show()

    app.exec()

if __name__ == '__main__':
    launch_mia()