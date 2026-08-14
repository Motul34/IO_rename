"""
URPプログラムツリーの構築を行うモジュール。

main.py の build_tree メソッドから抽出。
各XMLタグの表示名生成をディスパッチテーブル方式で管理する。
"""
import logging

from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

from xml_resolver import resolve_variable_name, resolve_pin_name, parse_expression

logger = logging.getLogger(__name__)

# ツリーに表示するプログラムノードのタグ集合
PROGRAM_NODES = {
    'Folder', 'Waypoint', 'Comment', 'Assignment', 'Timer', 'Move', 'Wait', 'Set',
    'Popup', 'Halt', 'Loop', 'SubProg', 'Script', 'Force', 'Pallet', 'Seek', 'Suppress',
    'MainProgram', 'RobotProgram', 'URProgram', 'If', 'ElseIf', 'Else', 'SafeHome',
    'InitVariablesNode', 'SpecialSequence', 'gui.program.direction.MoveDirectionNode',
    'SetPayload', 'SuppressedNode', 'suppressedNode', 'ExpressionWaypoint', 'Until'
}

# 方向ノードの日本語マッピング
_DIRECTION_MAP = {
    'XPlus': 'ベース X+', 'XMinus': 'ベース X-',
    'YPlus': 'ベース Y+', 'YMinus': 'ベース Y-',
    'ZPlus': 'ベース Z+', 'ZMinus': 'ベース Z-',
}

# Until タイプのマッピング
_UNTIL_TYPE_MAP = {
    'DISTANCE': 'distance', 'IO': 'IO',
    'EXPRESSION': 'expression', 'TOOL_CONTACT': 'tool contact',
    'CUSTOM': 'custom',
}

# タイマーアクションの日本語マッピング
_TIMER_ACTION_MAP = {'Start': '開始', 'Stop': '停止', 'Reset': 'リセット'}

# 単純なタグ→日本語名のマッピング（個別ハンドラが不要なもの）
_SIMPLE_TAG_MAP = {
    'SafeHome': 'ホーム (安全)',
    'SetPayload': '荷重の設定',
    'Loop': 'ループ',
    'SubProg': 'サブプログラム',
    'Force': 'フォース',
    'Pallet': 'パレット',
    'Seek': 'シーク',
    'Suppress': '抑制',
    'Halt': '停止',
}


def _display_folder(elem, parent_map, io_manager):
    return elem.attrib.get('name', 'Folder')


def _display_waypoint(elem, parent_map, io_manager):
    name = elem.attrib.get('name', 'Waypoint')
    wp_type = elem.attrib.get('type', '')
    if wp_type == 'Variable':
        var_elem = elem.find('variable')
        vname = resolve_variable_name(var_elem, parent_map) if var_elem is not None else ""
        return f"{vname}(変数位置)" if vname else "変数位置"
    elif wp_type == 'Fixed':
        return f"{name} (固定位置)"
    elif wp_type == 'Relative':
        return f"{name} (相対位置)"
    elif wp_type:
        return f"{name} ({wp_type})"
    return name


def _display_comment(elem, parent_map, io_manager):
    comment = elem.attrib.get('comment', '')
    return f"'{comment}'" if comment else "'コメント'"


def _display_move(elem, parent_map, io_manager):
    return elem.attrib.get('motionType', 'Move')


def _display_assignment(elem, parent_map, io_manager):
    var_elem = elem.find('variable')
    vname = resolve_variable_name(var_elem, parent_map)
    expr = parse_expression(elem.find('expression'), parent_map, io_manager)
    return f"{vname}:={expr}" if vname else f"代入:={expr}"


def _display_timer(elem, parent_map, io_manager):
    var_elem = elem.find('variable')
    vname = resolve_variable_name(var_elem, parent_map)
    action = elem.attrib.get('action', '')
    action_ja = _TIMER_ACTION_MAP.get(action, action)
    if vname:
        return f"{vname}: {action_ja}" if action_ja else f"{vname}:"
    return f"タイマー: {action_ja}" if action_ja else "タイマー:"


def _display_set(elem, parent_map, io_manager):
    pin = elem.find('pin')
    if pin is not None:
        pname = resolve_pin_name(pin, parent_map, io_manager)
        dval = elem.find('digitalValue')
        if dval is not None:
            state = "オン" if dval.text == '1' else "オフ"
            return f"設定 {pname}={state}"
        aval = elem.find('analogValue')
        if aval is not None:
            return f"設定 {pname}={aval.text}"
        expr = parse_expression(elem.find('expression'), parent_map, io_manager)
        return f"設定 {pname}={expr}" if expr else f"設定 {pname}"
    return "設定"


def _display_wait(elem, parent_map, io_manager):
    wait_type = elem.attrib.get('type', '')
    if wait_type == 'Sleep':
        wt = elem.find('waitTime')
        return f"待機: {wt.text}" if wt is not None else "待機"
    pin = elem.find('pin')
    if pin is not None:
        pname = resolve_pin_name(pin, parent_map, io_manager)
        dval = elem.find('digitalValue')
        if dval is not None:
            state = "HI" if dval.text == '1' else "LO"
            return f"待機 {pname}={state}"
        return f"待機 {pname}"
    expr = parse_expression(elem.find('expression'), parent_map, io_manager)
    return f"待機 {expr}" if expr else "待機"


def _display_direction(elem, parent_map, io_manager):
    d = elem.attrib.get('selectedDirection', '')
    d_str = _DIRECTION_MAP.get(d, d)
    return f"方向: {d_str}" if d_str else "方向"


def _display_until(elem, parent_map, io_manager):
    utype = elem.attrib.get('type', '')
    return f"Until ({_UNTIL_TYPE_MAP.get(utype, utype.lower())})" if utype else "Until"


def _display_if(elem, parent_map, io_manager):
    expr = parse_expression(elem.find('expression'), parent_map, io_manager)
    return f"If文  {expr}"


def _display_elseif(elem, parent_map, io_manager):
    expr = parse_expression(elem.find('expression'), parent_map, io_manager)
    return f"ElseIf  {expr}"


def _display_script(elem, parent_map, io_manager):
    file_elem = elem.find('file')
    if file_elem is not None:
        return f"スクリプト: {file_elem.attrib.get('name', '')}"
    return "スクリプト"


# ディスパッチテーブル: tag → 表示名生成関数
NODE_DISPLAY_HANDLERS = {
    'Folder': _display_folder,
    'Waypoint': _display_waypoint,
    'Comment': _display_comment,
    'Move': _display_move,
    'Assignment': _display_assignment,
    'Timer': _display_timer,
    'Set': _display_set,
    'Wait': _display_wait,
    'gui.program.direction.MoveDirectionNode': _display_direction,
    'Until': _display_until,
    'If': _display_if,
    'ElseIf': _display_elseif,
    'Else': lambda e, pm, io: "Else",
    'SpecialSequence': lambda e, pm, io: "開始前シーケンス",
    'InitVariablesNode': lambda e, pm, io: "変数設定",
    'MainProgram': lambda e, pm, io: "ロボットプログラム",
    'URProgram': lambda e, pm, io: "プログラム",
    'Script': _display_script,
    'Popup': lambda e, pm, io: "ポップアップ",
}


def build_parent_map(root):
    """XMLツリー全体の {子要素: 親要素} マッピングを構築する。
    
    Args:
        root: XMLルート要素。
    
    Returns:
        parent_map 辞書。
    """
    return {c: p for p in root.iter() for c in p}


def build_tree(xml_elem, parent_item, parent_map, io_manager, 
               show_suppressed, tree_item_map):
    """XML要素からQTreeWidgetのツリーを再帰的に構築する。
    
    Args:
        xml_elem: 現在のXML要素。
        parent_item: 親のQTreeWidgetItem。
        parent_map: {子要素: 親要素} のマッピング辞書。
        io_manager: IOManagerインスタンス。
        show_suppressed: 非表示/抑制ノードを表示するかのフラグ。
        tree_item_map: {element_id: QTreeWidgetItem} の出力用辞書。
    """
    tag = xml_elem.tag
    if tag not in PROGRAM_NODES:
        for child in xml_elem:
            build_tree(child, parent_item, parent_map, io_manager,
                       show_suppressed, tree_item_map)
        return

    if tag == 'ExpressionWaypoint':
        return

    is_hidden = xml_elem.attrib.get('keepHidden') == 'true'
    is_suppressed = tag in ('suppressedNode', 'SuppressedNode')
    
    if is_suppressed:
        if not show_suppressed:
            return
        is_hidden = True
        tag = xml_elem.attrib.get('class', tag)

    # ディスパッチテーブルで表示名を生成
    handler = NODE_DISPLAY_HANDLERS.get(tag)
    if handler:
        name = handler(xml_elem, parent_map, io_manager)
    else:
        name = _SIMPLE_TAG_MAP.get(tag, tag)
            
    if is_suppressed:
        name = f"'{name}' (非表示)"
    elif is_hidden:
        name = f"{name} (非表示)"
            
    item = QTreeWidgetItem(parent_item, [name])
    item.setData(0, Qt.ItemDataRole.UserRole, id(xml_elem))
    tree_item_map[id(xml_elem)] = item
    
    for child in xml_elem:
        build_tree(child, item, parent_map, io_manager,
                   show_suppressed, tree_item_map)
