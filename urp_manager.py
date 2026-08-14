import gzip
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class URPManager:
    def __init__(self):
        self.tree = None
        self.root = None
        self.file_path = None
        self._xml_declaration = '<?xml version="1.0" encoding="utf-8"?>\n'
        
    def load(self, filepath):
        self.file_path = filepath
        logger.info("URP ファイルを読み込み中: %s", filepath)
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            content = f.read()
        
        # XML宣言を保存しておく
        if content.startswith('<?xml'):
            decl_end = content.index('?>') + 2
            self._xml_declaration = content[:decl_end] + '\n'
        
        self.tree = ET.ElementTree(ET.fromstring(content))
        self.root = self.tree.getroot()
        logger.info("URP ファイル読み込み完了")
        
    def get_root_node(self):
        """プログラムのルートノードを返す"""
        return self.root

    def get_editable_nodes(self, tag_name):
        """
        指定したタグ名の編集可能なノードのリストを返す。
        Folder, Assignment, Comment, Timer, Waypoint など。
        """
        nodes = []
        if self.root is None:
            return nodes
            
        for elem in self.root.iter(tag_name):
            nodes.append(elem)
        return nodes

    def get_node_name(self, elem):
        """
        要素から編集対象の名前を取得する。
        """
        tag = elem.tag
        if tag == 'Folder':
            return elem.attrib.get('name', '')
        elif tag == 'Waypoint':
            return elem.attrib.get('name', '')
        elif tag == 'Comment':
            return elem.attrib.get('comment', '')
        elif tag in ('Assignment', 'Timer'):
            var_elem = elem.find('variable')
            if var_elem is not None:
                return var_elem.attrib.get('name', '')
        return ""

    def set_node_name(self, elem, new_name):
        """
        要素の編集対象の名前を更新する。
        """
        tag = elem.tag
        if tag == 'Folder':
            elem.set('name', new_name)
        elif tag == 'Waypoint':
            elem.set('name', new_name)
        elif tag == 'Comment':
            elem.set('comment', new_name)
        elif tag in ('Assignment', 'Timer'):
            var_elem = elem.find('variable')
            if var_elem is not None:
                var_elem.set('name', new_name)

    def save(self, filepath=None):
        if filepath is None:
            filepath = self.file_path
        logger.info("URP ファイルを保存中: %s", filepath)
        # XML宣言を付与して元のフォーマットを維持する
        xml_str = self._xml_declaration + ET.tostring(self.root, encoding='unicode')
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            f.write(xml_str)
        logger.info("URP ファイル保存完了")
