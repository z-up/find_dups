import os, platform, subprocess

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow,
    QVBoxLayout, QHBoxLayout, QStackedLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox, QScrollArea,
    QMessageBox, QDialog, QProgressBar
)

import send2trash

from search_thread import DuplicatesSearchThread
#from find_duplicates import find_duplicate_files


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Find duplicate files")
        self.setMinimumSize(800, 600)

        hbox = QHBoxLayout()

        self.dir_line_edit = QLineEdit()
        self.dir_line_edit.setReadOnly(True)
        hbox.addWidget(self.dir_line_edit)

        pick_dir_btn = QPushButton("📁")
        pick_dir_btn.setToolTip("Select folder")
        pick_dir_btn.clicked.connect(self.show_pick_dir_dlg)
        hbox.addWidget(pick_dir_btn)

        self.search_btn = QPushButton("🔍")
        self.search_btn.setToolTip("Search for duplicate files")
        self.search_btn.setDisabled(True)
        self.search_btn.clicked.connect(self.start_search_thread)
        hbox.addWidget(self.search_btn)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox)

        self.stacked_layout = QStackedLayout()
        vbox.addLayout(self.stacked_layout)

        pagination_panel = QHBoxLayout()
        self.first_group_btn = QPushButton("⏮️")
        self.first_group_btn.setToolTip("Go to first group of identical files")
        self.first_group_btn.clicked.connect(self.first_page)

        self.prev_group_btn = QPushButton("◀️")
        self.prev_group_btn.setToolTip("Go to previous group of identical files")
        self.prev_group_btn.clicked.connect(self.prev_page)

        self.next_group_btn = QPushButton("▶️")
        self.next_group_btn.setToolTip("Go to next group of identical files")
        self.next_group_btn.clicked.connect(self.next_page)

        self.last_group_btn = QPushButton("⏭️")
        self.last_group_btn.setToolTip("Go to last group of identical files")
        self.last_group_btn.clicked.connect(self.last_page)

        self.group_number = QLabel("")
        self.group_number.setFixedWidth(100)
        self.group_number.setAlignment(Qt.AlignCenter)

        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setToolTip("Delete selected files")
        self.delete_btn.clicked.connect(self.delete_duplicates)

        pagination_panel.addWidget(self.first_group_btn)
        pagination_panel.addWidget(self.prev_group_btn)
        pagination_panel.addWidget(self.group_number)
        pagination_panel.addWidget(self.next_group_btn)
        pagination_panel.addWidget(self.last_group_btn)
        pagination_panel.addStretch()
        pagination_panel.addWidget(self.delete_btn)

        vbox.addLayout(pagination_panel)

        container = QWidget()
        container.setLayout(vbox)

        self.setCentralWidget(container)
        self.update_pagination_buttons()

        # color theme
        # with open('colortheme.css', 'r') as theme_file:
        #     stylesheet = theme_file.read()
        #     self.setStyleSheet(stylesheet)


    def show_pick_dir_dlg(self):
        # dir = QFileDialog.getExistingDirectory(self, options=QFileDialog.DontUseNativeDialog)
        dir = QFileDialog.getExistingDirectory(self)

        if not dir:
            return

        self.dir = str(dir)
        self.dir_line_edit.setText(dir)
        self.search_btn.setDisabled(False)


    def start_search_thread(self):
        thread = DuplicatesSearchThread(self.dir, self.show_search_results)

        self.progress_dlg = SearchProgressDlg(thread)
        #self.progress_dlg.setWindowFlags(Qt.Dialog | Qt.Desktop)
        #self.progress_dlg.setWindowTitle("Search in progress")
        thread.start()
        self.progress_dlg.exec()



    def show_search_results(self, dups):
        # dups = find_duplicate_files(self.dir)
        self.progress_dlg.close()

        # clear previous search results
        for i in reversed(range(self.stacked_layout.count())):
            self.stacked_layout.itemAt(i).widget().setParent(None)

        for group in dups.values():
            widget = FileGroupWidget(self.dir, group)
            self.stacked_layout.addWidget(widget)

        self.stacked_layout.setCurrentIndex(0)
        self.update_pagination_buttons()

        # showing "No duplicates found" message after calling update_pagination_buttons
        # so that button states (specifically delete_btn) are set correctly
        if len(dups) == 0:
            lbl = QLabel("No duplicates found")
            lbl.setAlignment(Qt.AlignCenter)
            self.stacked_layout.addWidget(lbl)


    def update_pagination_buttons(self):
        page_count = self.stacked_layout.count()
        cur_page = self.stacked_layout.currentIndex()

        self.first_group_btn.setEnabled(page_count != 0 and cur_page != 0)
        self.prev_group_btn.setEnabled(page_count != 0 and cur_page != 0)
        self.next_group_btn.setEnabled(page_count != 0 and cur_page != page_count - 1)
        self.last_group_btn.setEnabled(page_count != 0 and cur_page != page_count - 1)
        self.delete_btn.setEnabled(page_count != 0)

        if page_count != 0:
            self.group_number.setText(f"{cur_page + 1}/{page_count}")
        else:
            self.group_number.setText("0/0")


    def first_page(self):
        self.stacked_layout.setCurrentIndex(0)
        self.update_pagination_buttons()


    def prev_page(self):
        self.stacked_layout.setCurrentIndex(self.stacked_layout.currentIndex() - 1)
        self.update_pagination_buttons()


    def next_page(self):
        self.stacked_layout.setCurrentIndex(self.stacked_layout.currentIndex() + 1)
        self.update_pagination_buttons()


    def last_page(self):
        self.stacked_layout.setCurrentIndex(self.stacked_layout.count() -1)
        self.update_pagination_buttons()


    def delete_duplicates(self):
        self.stacked_layout.currentWidget().delete_duplicates()


class FileGroupWidget(QScrollArea):
    def __init__(self, root_dir, file_group):
        super().__init__()

        self.root_dir = root_dir

        self.setWidgetResizable(True)

        self.check_boxes = []
        self.labels = []
        self.open_btns = []
        #self.file_names = []

        container = QWidget()
        container.setFont(QFont('Arial', 14))
        # sp = container.sizePolicy()
        # sp.setHorizontalPolicy(QSizePolicy.MinimumExpanding)
        # container.setSizePolicy(sp)

        # p = container.palette()
        # p.setColor(container.backgroundRole(), Qt.red)
        # container.setPalette(p)

        vbox = QVBoxLayout()
        #for i in range(0, 2): # test scroll area
        for n, file in enumerate(file_group):
            hbox = QHBoxLayout()

            check_box = QCheckBox()
            check_box_state = Qt.CheckState.Unchecked if n == 0 else Qt.CheckState.Checked
            check_box.setCheckState(check_box_state)
            check_box.setToolTip("Mark for deletion")
            hbox.addWidget(check_box)
            self.check_boxes.append(check_box)

            rel_path = os.path.relpath(file, self.root_dir)
            label = QLabel(rel_path)
            hbox.addWidget(label)
            self.labels.append(label)
            #self.file_names.append(file)

            hbox.addStretch()

            open_file_btn = QPushButton("🔗")
            open_file_btn.clicked.connect((lambda f: lambda: self.open_file(f))(file))
            hbox.addWidget(open_file_btn)
            self.open_btns.append(open_file_btn)

            vbox.addLayout(hbox)

        vbox.addStretch()
        container.setLayout(vbox)
        self.setWidget(container)


    def open_file(self, fname):
        # print(f"Openning {fname}")
        if platform.system() == 'Darwin':
            subprocess.call(('open', fname))
        elif platform.system() == 'Windows':
            os.startfile(fname)
        else: # Linux variants
            subprocess.call(('xdg-open', fname))


    def delete_duplicates(self):
        selection = []
        for cb in self.check_boxes:
            if cb.isEnabled():
                selection.append(cb.checkState() == Qt.CheckState.Checked)

        if len(selection) != 0 and all(selection): # all([]) == True for some reason
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Everything selected")
            msgBox.setText("Are you sure you want to delete ALL files?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            msgBox.setDefaultButton(QMessageBox.Cancel)
            msgBox.setIcon(QMessageBox.Question)
            if msgBox.exec() == QMessageBox.Cancel:
                return

        # TODO: handle the case when all files have been already deleted
        # (disable delete button?)
        if not any(selection):
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Nothing selected")
            msgBox.setText("You haven't selected any files")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setDefaultButton(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.exec()
            return

        for cb, lbl, open_btn in zip(self.check_boxes, self.labels, self.open_btns):
            if cb.checkState() != Qt.CheckState.Checked or not cb.isEnabled():
                continue

            cb.setDisabled(True)

            font = lbl.font()
            font.setStrikeOut(True)
            lbl.setFont(font)

            open_btn.setDisabled(True)

            fname = lbl.text()
            full_path = os.path.abspath(os.path.join(self.root_dir, fname))
            # print(f"root_dir == {self.root_dir}")
            # print(f"deleting {full_path}")
            send2trash.send2trash(full_path)


class SearchProgressDlg(QDialog):
    def __init__(self, search_thread):
        super().__init__()

        self.search_thread = search_thread

        search_thread.progress_update.connect(self.on_progress_update)
        search_thread.search_aborted.connect(self.on_search_abortion)

        self.setWindowFlags(Qt.Dialog | Qt.Desktop)
        self.setWindowTitle("Search in progress")

        vbox = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        vbox.addWidget(self.progress_bar)

        abort_btn = QPushButton("Abort")
        abort_btn.clicked.connect(self.abort_search)
        vbox.addWidget(abort_btn, alignment=Qt.AlignHCenter)

        self.setLayout(vbox)
        self.setMinimumWidth(350)


    def abort_search(self):
        print(f"abort button clicked")
        self.search_thread.should_abort = True


    def on_progress_update(self, percent):
        self.progress_bar.setValue(percent)


    def on_search_abortion(self):
        self.close()


app = QApplication([])

window = MainWindow()
window.show()

app.exec()
