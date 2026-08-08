import sys
import re
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMenuBar, QFileDialog, QMessageBox, 
                             QStyledItemDelegate, QLineEdit, QAbstractItemView)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from io_manager import IOManager

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 15文字制限用のデリゲート
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
        self.setWindowTitle("UR .installation IO Editor")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1000, 700)
        self.io_manager = IOManager()
        self.current_file = None
        
        # モダン・ライトのスタイル適用
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QTableWidget { gridline-color: #d0d0d0; alternate-background-color: #e8f4f8; }
            QHeaderView::section { background-color: #0078d7; color: white; font-weight: bold; padding: 4px; border: 1px solid #d0d0d0; }
            QTabWidget::pane { border: 1px solid #cccccc; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 16px; margin-right: 2px; }
            QTabBar::tab:selected { background: #ffffff; border-top: 2px solid #0078d7; font-weight: bold; }
        """)
        
        self.init_menu()
        self.init_ui()
        
    def init_menu(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("ファイル(F)")
        
        open_action = fileMenu.addAction("開く(O)...")
        open_action.triggered.connect(self.open_file)
        
        self.save_action = fileMenu.addAction("上書き保存(S)")
        self.save_action.triggered.connect(self.save_file)
        self.save_action.setEnabled(False)
        
        save_as_action = fileMenu.addAction("名前を付けて保存(A)...")
        save_as_action.triggered.connect(self.save_as_file)
        
        fileMenu.addSeparator()
        exit_action = fileMenu.addAction("終了(X)")
        exit_action.triggered.connect(self.close)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # タブ構成の定義
        # (タブ名, 項目リスト: (XMLタグ名, 表示用Type名, is_gp))
        self.tab_configs = [
            ("Digital", [
                ('DigitalInputNames', 'Digital Input', False),
                ('DigitalOutputNames', 'Digital Output', False)
            ]),
            ("Tool", [
                ('ToolDigitalInputNames', 'Tool Digital Input', False),
                ('ToolDigitalOutputNames', 'Tool Digital Output', False),
                ('ToolAnalogInputNames', 'Tool Analog Input', False)
            ]),
            ("Analog", [
                ('AnalogInputNames', 'Analog Input', False),
                ('AnalogOutputNames', 'Analog Output', False)
            ]),
            ("GP Boolean", [
                ('GeneralPurposeBooleanRegisterInputNames', 'GP Boolean Input', True),
                ('GeneralPurposeBooleanRegisterOutputNames', 'GP Boolean Output', True)
            ]),
            ("GP Int", [
                ('GeneralPurposeIntRegisterInputNames', 'GP Int Input', True),
                ('GeneralPurposeIntRegisterOutputNames', 'GP Int Output', True)
            ]),
            ("GP Float", [
                ('GeneralPurposeFloatRegisterInputNames', 'GP Float Input', True),
                ('GeneralPurposeFloatRegisterOutputNames', 'GP Float Output', True)
            ])
        ]
        
        self.tables = {} # tag_name: table_widget
        self.tag_is_gp = {}
        
        for tab_name, tags in self.tab_configs:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            for tag_name, display_type, is_gp in tags:
                self.tag_is_gp[tag_name] = is_gp
                table = QTableWidget(0, 4 if is_gp else 3)
                
                if is_gp:
                    table.setHorizontalHeaderLabels(["Index", "Type", "Addr", "IO Name"])
                    # IO Name を一番伸ばす
                    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
                    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
                else:
                    table.setHorizontalHeaderLabels(["Index", "Type", "IO Name"])
                    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
                
                table.verticalHeader().setVisible(False)
                table.setAlternatingRowColors(True)
                
                # IO Nameの列に15文字制限デリゲートをセット
                name_col = 3 if is_gp else 2
                table.setItemDelegateForColumn(name_col, MaxLengthDelegate(15, table))
                
                # GPのAddr編集イベントを捉える
                if is_gp:
                    table.itemChanged.connect(lambda item, t=table: self.on_item_changed(item, t))
                
                tab_layout.addWidget(table)
                self.tables[tag_name] = table
                
            self.tabs.addTab(tab, tab_name)

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "開く", "", "Installation Files (*.installation);;All Files (*)")
        if filepath:
            try:
                self.io_manager.load(filepath)
                self.current_file = filepath
                self.populate_tables()
                self.save_action.setEnabled(True)
                self.setWindowTitle(f"UR .installation IO Editor - {os.path.basename(filepath)}")
                QMessageBox.information(self, "成功", "ファイルを読み込みました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"読み込みエラー:\n{str(e)}")

    def populate_tables(self):
        for tag_name, table in self.tables.items():
            table.blockSignals(True) # 値セット中のイベント発火を防ぐ
            names = self.io_manager.get_io_names(tag_name)
            table.setRowCount(len(names))
            
            is_gp = self.tag_is_gp[tag_name]
            
            # Type名を探す
            display_type = ""
            for _, tags in self.tab_configs:
                for t_name, d_type, _ in tags:
                    if t_name == tag_name:
                        display_type = d_type
                        break
            
            for row, name in enumerate(names):
                # Index
                item_idx = QTableWidgetItem(str(row))
                item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 0, item_idx)
                
                # Type
                item_type = QTableWidgetItem(display_type)
                item_type.setFlags(item_type.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 1, item_type)
                
                if is_gp:
                    # Addr (空)
                    table.setItem(row, 2, QTableWidgetItem(""))
                    # IO Name
                    table.setItem(row, 3, QTableWidgetItem(name))
                else:
                    table.setItem(row, 2, QTableWidgetItem(name))
            
            table.blockSignals(False)

    def on_item_changed(self, item, table):
        # GPタブでのみ発火し、Addr列（2列目）が変更された場合のみ処理
        if item.column() == 2:
            row = item.row()
            val = item.text()
            if not val:
                return
            
            # 正規表現でプレフィックスと16進数部分を分離
            # 例: "EX000F" -> prefix="EX", hex_str="000F"
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
                
                # イベント再帰を防ぐ
                table.blockSignals(True)
                
                for r in range(table.rowCount()):
                    if r == row:
                        continue
                    offset = r - row
                    new_val = base_val + offset
                    if new_val < 0:
                        table.setItem(r, 2, QTableWidgetItem(""))
                        continue
                    
                    # フォーマット（ゼロ埋め、大文字小文字維持）
                    new_hex = hex(new_val)[2:]
                    if is_upper:
                        new_hex = new_hex.upper()
                    new_hex = new_hex.zfill(hex_len)
                    
                    table.setItem(r, 2, QTableWidgetItem(prefix + new_hex))
                
                table.blockSignals(False)

    def collect_data_and_save(self, filepath):
        try:
            for tag_name, table in self.tables.items():
                names = []
                is_gp = self.tag_is_gp[tag_name]
                name_col = 3 if is_gp else 2
                
                for row in range(table.rowCount()):
                    item = table.item(row, name_col)
                    name = item.text() if item else ""
                    # "空欄だったものはそのまま空欄" は空文字として取得し、
                    # IOManager側でフォーマット維持するように処理済み
                    names.append(name)
                
                self.io_manager.set_io_names(tag_name, names)
                
            self.io_manager.save(filepath)
            self.current_file = filepath
            self.setWindowTitle(f"UR .installation IO Editor - {os.path.basename(filepath)}")
            QMessageBox.information(self, "成功", "ファイルを保存しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存エラー:\n{str(e)}")

    def save_file(self):
        if self.current_file:
            self.collect_data_and_save(self.current_file)

    def save_as_file(self):
        if not self.io_manager.tree:
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "名前を付けて保存", "", "Installation Files (*.installation);;All Files (*)")
        if filepath:
            self.collect_data_and_save(filepath)

def main():
    app = QApplication(sys.argv)
    # モダンUIにあわせてWindows標準スタイルを適用
    app.setStyle("windowsvista")
    window = IOEditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
