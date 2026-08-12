import gzip
import xml.etree.ElementTree as ET

class URPManager:
    def __init__(self):
        self.tree = None
        self.root = None
        self.file_path = None
        
    def load(self, filepath):
        self.file_path = filepath
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            content = f.read()
        self.tree = ET.ElementTree(ET.fromstring(content))
        self.root = self.tree.getroot()
        
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
        xml_str = ET.tostring(self.root, encoding='utf-8').decode('utf-8')
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            f.write(xml_str)
