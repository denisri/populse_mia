from PyQt5 import QtWidgets, QtCore
from PopUps.Ui_Tag_Selection import Ui_Tag_Selection


class Ui_Select_Tag_Count_Table(Ui_Tag_Selection):
    """
    Is called when the user wants to update the tags that are visualized in the data browser
    """

    def __init__(self, database, tag_name_checked=None):
        super(Ui_Select_Tag_Count_Table, self).__init__(database)
        self.retranslate_Ui(tag_name_checked)

    def retranslate_Ui(self, tag_name_checked):
        """_translate = QtCore.QCoreApplication.translate

        # The "Tag list" label
        self.label_tag_list = QtWidgets.QLabel(self)
        self.label_tag_list.setTextFormat(QtCore.Qt.AutoText)
        self.label_tag_list.setObjectName("label_tag_list")
        self.label_tag_list.setText(_translate("MainWindow", "Available tags:"))

        # The search bar to search in the list of tags
        self.search_bar = QtWidgets.QLineEdit(self)
        self.search_bar.setObjectName("lineEdit_search_bar")
        self.search_bar.setPlaceholderText("Search")
        self.search_bar.textChanged.connect(self.search_str)

        # The list of tags
        self.list_widget_tags = QtWidgets.QListWidget(self)
        self.list_widget_tags.setObjectName("listWidget_tags")
        self.list_widget_tags.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_widget_tags.itemClicked.connect(self.item_clicked)

        self.push_button_ok = QtWidgets.QPushButton(self)
        self.push_button_ok.setObjectName("pushButton_ok")
        self.push_button_ok.setText("OK")
        self.push_button_ok.clicked.connect(self.ok_clicked)

        self.push_button_cancel = QtWidgets.QPushButton(self)
        self.push_button_cancel.setObjectName("pushButton_cancel")
        self.push_button_cancel.setText("Cancel")
        self.push_button_cancel.clicked.connect(self.cancel_clicked)

        hbox_top_left = QHBoxLayout()
        hbox_top_left.addWidget(self.label_tag_list)
        hbox_top_left.addWidget(self.search_bar)

        vbox_top_left = QVBoxLayout()
        vbox_top_left.addLayout(hbox_top_left)
        vbox_top_left.addWidget(self.list_widget_tags)

        hbox_buttons = QHBoxLayout()
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(self.push_button_ok)
        hbox_buttons.addWidget(self.push_button_cancel)

        vbox_final = QVBoxLayout()
        vbox_final.addLayout(vbox_top_left)
        vbox_final.addLayout(hbox_buttons)

        self.setLayout(vbox_final)"""

        for tag in self.database.getTags():
            item = QtWidgets.QListWidgetItem()
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            if tag.tag == tag_name_checked:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
            self.list_widget_tags.addItem(item)
            item.setText(tag.tag)

    """def search_str(self, str_search):
        return_list = []
        if str_search != "":
            for tag in self.database.getTags():
                if str_search.upper() in tag.tag.upper():
                    return_list.append(tag.tag)
        else:
            for tag in self.database.getTags():
                return_list.append(tag.tag)

        for idx in range(self.list_widget_tags.count()):
            item = self.list_widget_tags.item(idx)
            if item.text() in return_list:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def item_clicked(self, item):
        for idx in range(self.list_widget_tags.count()):
            itm = self.list_widget_tags.item(idx)
            if itm == item:
                itm.setCheckState(QtCore.Qt.Checked)
            else:
                itm.setCheckState(QtCore.Qt.Unchecked)"""

    def ok_clicked(self):
        for idx in range(self.list_widget_tags.count()):
            item = self.list_widget_tags.item(idx)
            if item.checkState() == QtCore.Qt.Checked:
                self.selected_tag = item.text()
                break

        self.accept()
        self.close()

    """def cancel_clicked(self):
        self.close()"""

