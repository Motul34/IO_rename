import sys
import re
import os
import glob
import gzip
import logging
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMenuBar, QFileDialog, QMessageBox, 
                             QStyledItemDelegate, QLineEdit, QAbstractItemView,
                             QTreeWidget, QTreeWidgetItem, QInputDialog, QSplitter, QCheckBox)
from PyQt6.QtGui import QIcon, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal

from io_manager import IOManager
from urp_manager import URPManager
from xml_resolver import resolve_variable_name
from tree_builder import build_tree, build_parent_map

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MaxLengthDelegate(QStyledItemDelegate):
    def __init__(self, max_length, parent=None):
        super().__init__(parent)
        self.max_length = max_length

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setMaxLength(self.max_length)
        return editor

class IOEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR IO & Node Editor")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1200, 700)
        self.io_manager = IOManager()
        self.urp_manager = URPManager()
        
        self.current_installation_file = None
        self.current_urp_file = None
        
        # 未保存変更の追跡フラグ
        self._dirty = False
        
        # UIステート管理用
        # NOTE: id() を使用してXML要素を追跡している。
        # id() はオブジェクトのライフタイム内でのみ一意であるため、
        # populate_urp_data() の先頭で必ずマップをクリアすること。
        self.io_tabs_indices = []
        self.urp_tabs_indices = []
        self.urp_elements_map = {} # { element_id : (tab_index, row, tag_name) }
        self.tree_item_map = {} # { element_id : QTreeWidgetItem }

        # XMLの親子マッピング（xml_resolver, tree_builder で使用）
        self._parent_map = {}

        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QTableWidget { gridline-color: #d0d0d0; alternate-background-color: #e8f4f8; }
            QHeaderView::section { background-color: #0078d7; color: white; font-weight: bold; padding: 4px; border: 1px solid #d0d0d0; }
            QTabWidget::pane { border: 1px solid #cccccc; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 16px; margin-right: 2px; }
            QTabBar::tab:selected { background: #ffffff; border-top: 2px solid #0078d7; font-weight: bold; }
            QTreeWidget { background-color: #ffffff; border: 1px solid #cccccc; }
        """)
        
        self.init_menu()
        self.init_ui()
        
    def init_menu(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("ファイル(F)")
        
        open_file_action = fileMenu.addAction("ファイルを開く(O)...")
        open_file_action.setShortcut(QKeySequence("Ctrl+O"))
        open_file_action.triggered.connect(self.open_file_dialog)
        
        open_dir_action = fileMenu.addAction("フォルダを開く(D)...")
        open_dir_action.triggered.connect(self.open_dir_dialog)
        
        self.save_action = fileMenu.addAction("上書き保存(S)")
        self.save_action.setShortcut(QKeySequence("Ctrl+S"))
        self.save_action.triggered.connect(self.save_files)
        self.save_action.setEnabled(False)
        
        save_as_action = fileMenu.addAction("名前を付けて保存(A)...")
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_as_files)
        
        fileMenu.addSeparator()
        exit_action = fileMenu.addAction("終了(X)")
        exit_action.triggered.connect(self.close)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # --- プログラムツリータブ (一番左) ---
        self.tree_tab = QWidget()
        tree_layout = QVBoxLayout(self.tree_tab)
        
        self.show_suppressed_cb = QCheckBox("非表示/抑制されたノードを表示する")
        self.show_suppressed_cb.setChecked(False)
        self.show_suppressed_cb.stateChanged.connect(lambda: self.populate_urp_data() if hasattr(self, 'urp_manager') and self.urp_manager.root is not None else None)
        tree_layout.addWidget(self.show_suppressed_cb)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QTreeWidget::item {
                padding: 2px;
            }
        """)
        self.tree_widget.setIndentation(20)
        tree_layout.addWidget(self.tree_widget)
        self.tabs.addTab(self.tree_tab, "Program Tree")
        self.tree_tab_index = 0
        
        # --- URP ノード編集タブ ---
        self.urp_tab_configs = [
            ("Folder (フォルダ)", "Folder"),
            ("Assignment (代入)", "Assignment"),
            ("Comment (コメント)", "Comment"),
            ("Timer (タイマー)", "Timer"),
            ("Waypoint (ウェイポイント)", "Waypoint")
        ]
        self.urp_tables = {} # tag_name: table_widget
        
        for tab_name, tag_name in self.urp_tab_configs:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            table = QTableWidget(0, 2)
            table.setHorizontalHeaderLabels(["Index", "Node Name"])
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.setItemDelegateForColumn(1, MaxLengthDelegate(50, table)) # ノード名は少し長めでもOKとする
            
            table.itemChanged.connect(lambda item, t=tag_name: self.on_urp_item_changed(item, t))
            
            tab_layout.addWidget(table)
            self.urp_tables[tag_name] = table
            idx = self.tabs.addTab(tab, tab_name)
            self.urp_tabs_indices.append(idx)
        
        # --- IO 編集タブ ---
        self.io_tab_configs = [
            ("Digital", [('DigitalInputNames', 'Digital Input', False), ('DigitalOutputNames', 'Digital Output', False)]),
            ("Tool", [('ToolDigitalInputNames', 'Tool Digital Input', False), ('ToolDigitalOutputNames', 'Tool Digital Output', False), ('ToolAnalogInputNames', 'Tool Analog Input', False)]),
            ("Analog", [('AnalogInputNames', 'Analog Input', False), ('AnalogOutputNames', 'Analog Output', False)]),
            ("GP Boolean", [('GeneralPurposeBooleanRegisterInputNames', 'GP Boolean Input', True), ('GeneralPurposeBooleanRegisterOutputNames', 'GP Boolean Output', True)]),
            ("GP Int", [('GeneralPurposeIntRegisterInputNames', 'GP Int Input', True), ('GeneralPurposeIntRegisterOutputNames', 'GP Int Output', True)]),
            ("GP Float", [('GeneralPurposeFloatRegisterInputNames', 'GP Float Input', True), ('GeneralPurposeFloatRegisterOutputNames', 'GP Float Output', True)])
        ]
        
        self.io_tables = {}
        self.io_tag_is_gp = {}
        
        for tab_name, tags in self.io_tab_configs:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            for tag_name, display_type, is_gp in tags:
                self.io_tag_is_gp[tag_name] = is_gp
                table = QTableWidget(0, 4 if is_gp else 3)
                if is_gp:
                    table.setHorizontalHeaderLabels(["Index", "Type", "Addr", "IO Name"])
                    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
                    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                else:
                    table.setHorizontalHeaderLabels(["Index", "Type", "IO Name"])
                    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
                
                table.verticalHeader().setVisible(False)
                table.setAlternatingRowColors(True)
                name_col = 3 if is_gp else 2
                table.setItemDelegateForColumn(name_col, MaxLengthDelegate(15, table))
                
                if is_gp:
                    table.itemChanged.connect(lambda item, t=table: self.on_io_item_changed(item, t))
                
                tab_layout.addWidget(table)
                self.io_tables[tag_name] = table
            idx = self.tabs.addTab(tab, tab_name)
            self.io_tabs_indices.append(idx)
            
        self.set_io_tabs_enabled(False)
        self.set_urp_tabs_enabled(False)
        self.tabs.setCurrentIndex(self.tree_tab_index)

    def set_io_tabs_enabled(self, enabled):
        for idx in self.io_tabs_indices:
            self.tabs.setTabEnabled(idx, enabled)

    def set_urp_tabs_enabled(self, enabled):
        self.tabs.setTabEnabled(self.tree_tab_index, enabled)
        for idx in self.urp_tabs_indices:
            self.tabs.setTabEnabled(idx, enabled)

    def _mark_dirty(self):
        """未保存変更があることをマークする"""
        self._dirty = True

    def _confirm_discard(self):
        """未保存変更がある場合、ユーザーに確認する。
        
        Returns:
            True: 続行してよい（保存済みまたは破棄）
            False: キャンセルされた
        """
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self, "確認",
            "未保存の変更があります。保存しますか？",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Save:
            self.save_files()
            return True
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:  # Cancel
            return False

    def closeEvent(self, event):
        """ウィンドウを閉じる前に未保存変更を確認する"""
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def open_file_dialog(self):
        if not self._confirm_discard():
            return
        filepath, _ = QFileDialog.getOpenFileName(self, "ファイルを開く", "", "UR Files (*.installation *.urp);;All Files (*)")
        if filepath:
            self.load_files([filepath])

    def open_dir_dialog(self):
        if not self._confirm_discard():
            return
        dirpath = QFileDialog.getExistingDirectory(self, "フォルダを開く")
        if dirpath:
            inst_files = glob.glob(os.path.join(dirpath, "*.installation"))
            urp_files = glob.glob(os.path.join(dirpath, "*.urp"))
            
            files_to_load = []
            
            # .installationファイルの選択
            if len(inst_files) == 1:
                files_to_load.append(inst_files[0])
            elif len(inst_files) > 1:
                item, ok = QInputDialog.getItem(self, "選択", ".installationファイルを選択してください:", [os.path.basename(f) for f in inst_files], 0, False)
                if ok and item:
                    files_to_load.append(os.path.join(dirpath, item))
                    
            # .urpファイルの選択
            if len(urp_files) == 1:
                files_to_load.append(urp_files[0])
            elif len(urp_files) > 1:
                item, ok = QInputDialog.getItem(self, "選択", ".urpファイルを選択してください:", [os.path.basename(f) for f in urp_files], 0, False)
                if ok and item:
                    files_to_load.append(os.path.join(dirpath, item))
                    
            if not files_to_load:
                QMessageBox.warning(self, "警告", "フォルダ内に対象ファイルが見つかりませんでした。")
                return
                
            self.load_files(files_to_load)

    def load_files(self, filepaths):
        self.current_installation_file = None
        self.current_urp_file = None
        
        self.io_manager.clear()
        self.urp_manager = URPManager() # reset
        self._parent_map = {}
        
        loaded_inst = False
        loaded_urp = False
        
        for fp in filepaths:
            ext = os.path.splitext(fp)[1].lower()
            try:
                if ext == '.installation':
                    self.io_manager.load(fp)
                    self.current_installation_file = fp
                    loaded_inst = True
                elif ext == '.urp':
                    self.urp_manager.load(fp)
                    self.current_urp_file = fp
                    loaded_urp = True
            except (IOError, OSError, ET.ParseError, gzip.BadGzipFile, ValueError) as e:
                logger.error("ファイル読み込みエラー: %s - %s", fp, e)
                QMessageBox.critical(self, "エラー", f"{os.path.basename(fp)} の読み込みエラー:\n{str(e)}")
        
        self.set_io_tabs_enabled(loaded_inst)
        self.set_urp_tabs_enabled(loaded_urp)
        
        if loaded_inst:
            self.populate_io_tables()
        if loaded_urp:
            self.populate_urp_data()
            
        self.save_action.setEnabled(loaded_inst or loaded_urp)
        self._dirty = False
        
        title = "UR IO & Node Editor"
        if loaded_inst and loaded_urp:
            title += f" - {os.path.basename(self.current_installation_file)}, {os.path.basename(self.current_urp_file)}"
        elif loaded_inst:
            title += f" - {os.path.basename(self.current_installation_file)}"
        elif loaded_urp:
            title += f" - {os.path.basename(self.current_urp_file)}"
        self.setWindowTitle(title)
        
        if loaded_urp:
            self.tabs.setCurrentIndex(self.tree_tab_index)
            
        QMessageBox.information(self, "成功", "読み込みが完了しました。")

    # --- URP 関連処理 ---
    def populate_urp_data(self):
        self.tree_widget.clear()
        self.urp_elements_map.clear()
        self.tree_item_map.clear()
        
        # 親子マッピングを構築
        root_elem = self.urp_manager.get_root_node()
        if root_elem is not None:
            self._parent_map = build_parent_map(self.urp_manager.root)
            
            # ツリーの構築（tree_builder モジュールを使用）
            build_tree(
                root_elem, self.tree_widget.invisibleRootItem(),
                self._parent_map, self.io_manager,
                self.show_suppressed_cb.isChecked(),
                self.tree_item_map
            )
            self.tree_widget.expandAll()
            
            def collapse_hidden(item):
                if "(非表示)" in item.text(0):
                    item.setExpanded(False)
                for i in range(item.childCount()):
                    collapse_hidden(item.child(i))
                    
            root_item = self.tree_widget.invisibleRootItem()
            for i in range(root_item.childCount()):
                collapse_hidden(root_item.child(i))
            
        # 編集テーブルの構築
        for tab_name, tag_name in self.urp_tab_configs:
            table = self.urp_tables[tag_name]
            table.blockSignals(True)
            nodes = self.urp_manager.get_editable_nodes(tag_name)
            table.setRowCount(len(nodes))
            
            # タブのインデックスを特定
            tab_index = -1
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == tab_name:
                    tab_index = i
                    break
                    
            for row, elem in enumerate(nodes):
                elem_id = id(elem)
                self.urp_elements_map[elem_id] = (tab_index, row, tag_name)
                
                # Index
                item_idx = QTableWidgetItem(str(row))
                item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 0, item_idx)
                
                # Name
                name = self.urp_manager.get_node_name(elem)
                is_variable_wp = (elem.tag == 'Waypoint' and elem.attrib.get('type', '') == 'Variable')
                if is_variable_wp:
                    var_elem = elem.find('variable')
                    vname = resolve_variable_name(var_elem, self._parent_map) if var_elem is not None else ""
                    name = f"{vname}(変数位置)" if vname else "変数位置"
                    
                is_empty_name = not name.strip()
                if is_empty_name:
                    name = "(未設定)"
                    
                item_name = QTableWidgetItem(name)
                
                if is_variable_wp or is_empty_name:
                    item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if is_empty_name:
                        item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                        
                table.setItem(row, 1, item_name)
                
                if is_empty_name:
                    table.setRowHidden(row, True)
                
            table.blockSignals(False)

    def on_tree_item_clicked(self, item, column):
        elem_id = item.data(0, Qt.ItemDataRole.UserRole)
        if elem_id in self.urp_elements_map:
            tab_index, row, tag_name = self.urp_elements_map[elem_id]
            self.tabs.setCurrentIndex(tab_index)
            table = self.urp_tables[tag_name]
            table.selectRow(row)

    def on_urp_item_changed(self, item, tag_name):
        if item.column() == 1:
            row = item.row()
            new_name = item.text()
            self._mark_dirty()
            
            # 対応する elem を探す
            target_elem_id = None
            for elem_id, (t_idx, r, t_name) in self.urp_elements_map.items():
                if t_name == tag_name and r == row:
                    target_elem_id = elem_id
                    break
                    
            if target_elem_id:
                # 実際のXML要素を更新
                nodes = self.urp_manager.get_editable_nodes(tag_name)
                # nodesはリストなので、idが一致するものを探す（通常は同じ順番）
                for node in nodes:
                    if id(node) == target_elem_id:
                        self.urp_manager.set_node_name(node, new_name)
                        break
                        
                # ツリー側の表示も更新
                if target_elem_id in self.tree_item_map:
                    tree_item = self.tree_item_map[target_elem_id]
                    display_name = f"{tag_name} ({new_name})" if new_name else tag_name
                    tree_item.setText(0, display_name)


    # --- IO 関連処理 ---
    def populate_io_tables(self):
        for tag_name, table in self.io_tables.items():
            table.blockSignals(True)
            names = self.io_manager.get_io_names(tag_name)
            table.setRowCount(len(names))
            
            is_gp = self.io_tag_is_gp[tag_name]
            
            display_type = ""
            for _, tags in self.io_tab_configs:
                for t_name, d_type, _ in tags:
                    if t_name == tag_name:
                        display_type = d_type
                        break
            
            for row, name in enumerate(names):
                item_idx = QTableWidgetItem(str(row))
                item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 0, item_idx)
                
                item_type = QTableWidgetItem(display_type)
                item_type.setFlags(item_type.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 1, item_type)
                
                if is_gp:
                    table.setItem(row, 2, QTableWidgetItem(""))
                    table.setItem(row, 3, QTableWidgetItem(name))
                else:
                    table.setItem(row, 2, QTableWidgetItem(name))
            
            table.blockSignals(False)

    def on_io_item_changed(self, item, table):
        self._mark_dirty()
        if item.column() == 2:
            row = item.row()
            val = item.text()
            if not val:
                return
            
            match = re.match(r'^(.*?)([0-9A-Fa-f]+)$', val)
            if match:
                prefix = match.group(1)
                hex_str = match.group(2)
                hex_len = len(hex_str)
                is_upper = hex_str.isupper()
                try:
                    base_val = int(hex_str, 16)
                except ValueError:
                    return
                
                table.blockSignals(True)
                for r in range(table.rowCount()):
                    if r == row:
                        continue
                    offset = r - row
                    new_val = base_val + offset
                    if new_val < 0:
                        table.setItem(r, 2, QTableWidgetItem(""))
                        continue
                    
                    new_hex = hex(new_val)[2:]
                    if is_upper:
                        new_hex = new_hex.upper()
                    new_hex = new_hex.zfill(hex_len)
                    table.setItem(r, 2, QTableWidgetItem(prefix + new_hex))
                table.blockSignals(False)

    # --- 保存処理 ---
    def save_files(self):
        try:
            # IOs 保存
            if self.current_installation_file:
                for tag_name, table in self.io_tables.items():
                    names = []
                    is_gp = self.io_tag_is_gp[tag_name]
                    name_col = 3 if is_gp else 2
                    for row in range(table.rowCount()):
                        item = table.item(row, name_col)
                        names.append(item.text() if item else "")
                    self.io_manager.set_io_names(tag_name, names)
                self.io_manager.save(self.current_installation_file)
                
            # URP 保存 (変更は既にurp_managerの要素に反映されているのでそのままsave)
            if self.current_urp_file:
                self.urp_manager.save(self.current_urp_file)
            
            self._dirty = False
            QMessageBox.information(self, "成功", "ファイルを保存しました。")
        except (IOError, OSError) as e:
            logger.error("保存エラー: %s", e)
            QMessageBox.critical(self, "エラー", f"保存エラー:\n{str(e)}")

    def save_as_files(self):
        # ユーザーに保存先フォルダを選ばせる
        dirpath = QFileDialog.getExistingDirectory(self, "保存先フォルダを選択")
        if dirpath:
            try:
                if self.current_installation_file:
                    new_inst = os.path.join(dirpath, os.path.basename(self.current_installation_file))
                    for tag_name, table in self.io_tables.items():
                        names = []
                        is_gp = self.io_tag_is_gp[tag_name]
                        name_col = 3 if is_gp else 2
                        for row in range(table.rowCount()):
                            item = table.item(row, name_col)
                            names.append(item.text() if item else "")
                        self.io_manager.set_io_names(tag_name, names)
                    self.io_manager.save(new_inst)
                    self.current_installation_file = new_inst
                    
                if self.current_urp_file:
                    new_urp = os.path.join(dirpath, os.path.basename(self.current_urp_file))
                    self.urp_manager.save(new_urp)
                    self.current_urp_file = new_urp
                
                self._dirty = False
                QMessageBox.information(self, "成功", "名前を付けて保存しました。")
            except (IOError, OSError) as e:
                logger.error("名前を付けて保存エラー: %s", e)
                QMessageBox.critical(self, "エラー", f"保存エラー:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setStyle("windowsvista")
    window = IOEditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
