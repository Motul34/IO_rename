import gzip
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class IOManager:
    def __init__(self):
        self.clear()
        
    def clear(self):
        self.tree = None
        self.root = None
        self.ios = None
        self.file_path = None
        self._xml_declaration = '<?xml version="1.0" encoding="utf-8"?>\n'
        
    def load(self, filepath):
        self.file_path = filepath
        logger.info("installation ファイルを読み込み中: %s", filepath)
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            content = f.read()
        
        # XML宣言を保存しておく
        if content.startswith('<?xml'):
            decl_end = content.index('?>') + 2
            self._xml_declaration = content[:decl_end] + '\n'
        
        self.tree = ET.ElementTree(ET.fromstring(content))
        self.root = self.tree.getroot()
        self.ios = self.root.find('IOs')
        if self.ios is None:
            raise ValueError("ファイル内に <IOs> タグが見つかりません。")
        logger.info("installation ファイル読み込み完了")
            
    def get_io_names(self, tag_name):
        """指定したタグの value 属性からカンマ区切りのリストを取得する"""
        if self.ios is None:
            return []
        elem = self.ios.find(tag_name)
        if elem is not None:
            val = elem.attrib.get('value', '')
            # 元々空欄のものは空文字として扱う
            return [x.strip() for x in val.split(',')]
        return []
        
    def set_io_names(self, tag_name, names):
        """カンマ区切りのリストを value 属性にセットする"""
        elem = self.ios.find(tag_name)
        if elem is None:
            elem = ET.SubElement(self.ios, tag_name)
        
        # 元々のフォーマットは ", , , " のようになっている。
        # 単に ", ".join(names) とすれば完全に一致する。
        elem.set('value', ', '.join(names))
        
    def save(self, filepath=None):
        if filepath is None:
            filepath = self.file_path
        logger.info("installation ファイルを保存中: %s", filepath)
        # XML宣言を付与して元のフォーマットを維持する
        xml_str = self._xml_declaration + ET.tostring(self.root, encoding='unicode')
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            f.write(xml_str)
        logger.info("installation ファイル保存完了")
