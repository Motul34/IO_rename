import gzip
import xml.etree.ElementTree as ET

class IOManager:
    def __init__(self):
        self.clear()
        
    def clear(self):
        self.tree = None
        self.root = None
        self.ios = None
        self.file_path = None
        
    def load(self, filepath):
        self.file_path = filepath
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            content = f.read()
        self.tree = ET.ElementTree(ET.fromstring(content))
        self.root = self.tree.getroot()
        self.ios = self.root.find('IOs')
        if self.ios is None:
            raise ValueError("ファイル内に <IOs> タグが見つかりません。")
            
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
        # 元のXMLに合わせて出力
        xml_str = ET.tostring(self.root, encoding='utf-8').decode('utf-8')
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            f.write(xml_str)
