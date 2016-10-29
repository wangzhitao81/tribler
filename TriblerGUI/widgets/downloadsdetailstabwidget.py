from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTabWidget, QTreeWidgetItem, QAction

from TriblerGUI.TriblerActionMenu import TriblerActionMenu
from TriblerGUI.defs import *
from TriblerGUI.utilities import format_size, format_speed


class DownloadsDetailsTabWidget(QTabWidget):

    def __init__(self, parent):
        super(DownloadsDetailsTabWidget, self).__init__(parent)
        self.current_download = None

    def initialize_details_widget(self):
        self.window().download_files_list.customContextMenuRequested.connect(self.on_right_click_file_item)

    def update_with_download(self, download):
        self.current_download = download
        self.update_pages()

    def update_pages(self):
        if self.current_download is None:
            return

        self.window().download_progress_bar.update_with_download(self.current_download)
        self.window().download_detail_name_label.setText(self.current_download['name'])
        self.window().download_detail_status_label.setText(DLSTATUS_STRINGS[eval(self.current_download["status"])])
        self.window().download_detail_filesize_label.setText("%s in %d files" % (format_size(float(self.current_download["size"])), len(self.current_download["files"])))
        self.window().download_detail_health_label.setText("%d seeders, %d leechers" % (self.current_download["num_seeds"], self.current_download["num_peers"]))
        self.window().download_detail_infohash_label.setText(self.current_download['infohash'])
        self.window().download_detail_availability_label.setText("%.2f" % self.current_download['availability'])

        # Populate the files list
        self.window().download_files_list.clear()
        for file in self.current_download["files"]:
            item = QTreeWidgetItem(self.window().download_files_list)
            item.setText(0, file["name"])
            item.setText(1, format_size(float(file["size"])))
            item.setText(2, '{percent:.1%}'.format(percent=file["progress"]))
            item.setText(3, "yes" if file["included"] else "no")
            item.setData(0, Qt.UserRole, file)
            self.window().download_files_list.addTopLevelItem(item)

        # Populate the trackers list
        self.window().download_trackers_list.clear()
        for tracker in self.current_download["trackers"]:
            item = QTreeWidgetItem(self.window().download_trackers_list)
            item.setText(0, tracker["url"])
            item.setText(1, tracker["status"])
            item.setText(2, str(tracker["peers"]))

        # Populate the peers list if the peer information is available
        self.window().download_peers_list.clear()
        if "peers" in self.current_download:
            for peer in self.current_download["peers"]:
                self.create_widget_with_peer_info(peer)

    def clear_data(self):
        self.setCurrentIndex(0)
        self.window().download_progress_bar.set_fraction(0.0)
        self.window().download_detail_name_label.setText("")
        self.window().download_detail_status_label.setText("")
        self.window().download_detail_filesize_label.setText("")
        self.window().download_detail_health_label.setText("")
        self.window().download_detail_infohash_label.setText("")
        self.window().download_detail_availability_label.setText("")

        self.window().download_files_list.clear()
        self.window().download_trackers_list.clear()
        self.window().download_peers_list.clear()

    def create_widget_with_peer_info(self, peer):
        item = QTreeWidgetItem(self.window().download_peers_list)

        peer_name = "%s:%s" % (peer["ip"], peer["port"])
        if peer['connection_type'] == 1:
            peer_name += ' [WebSeed]'
        elif peer['connection_type'] == 2:
            peer_name += ' [HTTP Seed]'
        elif peer['connection_type'] == 3:
            peer_name += ' [uTP]'

        state = ""
        if peer['optimistic']:
            state += "O,"
        if peer['uinterested']:
            state += "UI,"
        if peer['uchoked']:
            state += "UC,"
        if peer['uhasqueries']:
            state += "UQ,"
        if not peer['uflushed']:
            state += "UBL,"
        if peer['dinterested']:
            state += "DI,"
        if peer['dchoked']:
            state += "DC,"
        if peer['snubbed']:
            state += "S,"
        state += peer['direction']

        item.setText(0, peer_name)
        item.setText(1, '%d%%' % (peer['completed'] * 100.0))
        item.setText(2, format_speed(peer['downrate']))
        item.setText(3, format_speed(peer['uprate']))
        item.setText(4, state)
        item.setText(5, peer['extended_version'])

    def on_right_click_file_item(self, pos):
        self.selected_item = self.window().download_files_list.selectedItems()[0]
        file_data = self.selected_item.data(0, Qt.UserRole)

        menu = TriblerActionMenu(self)

        include_action = QAction('Include', self)
        exclude_action = QAction('Exclude', self)

        include_action.triggered.connect(lambda: self.on_file_included(file_data))
        include_action.setEnabled(not file_data["included"])
        exclude_action.triggered.connect(lambda: self.on_file_excluded(file_data))
        exclude_action.setEnabled(file_data["included"])

        menu.addAction(include_action)
        menu.addAction(exclude_action)

        menu.exec_(self.window().download_files_list.mapToGlobal(pos))

    def on_file_included(self, file_data):
        # TODO
        pass

    def on_file_excluded(self, file_data):
        # TODO
        pass
