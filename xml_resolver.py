"""
XML要素の名前解決・式パースを行うユーティリティモジュール。

main.py の IOEditorWindow から抽出した関数群。
IO名のプレフィックス→タグ名のマッピングを辞書で管理する。
"""
import re
import logging

logger = logging.getLogger(__name__)

# IO プレフィックス → XML タグ名のマッピング
IO_PREFIX_TO_TAG = {
    'GP_bool_out': 'GeneralPurposeBooleanRegisterOutputNames',
    'GP_bool_in': 'GeneralPurposeBooleanRegisterInputNames',
    'GP_int_out': 'GeneralPurposeIntRegisterOutputNames',
    'GP_int_in': 'GeneralPurposeIntRegisterInputNames',
    'GP_float_out': 'GeneralPurposeFloatRegisterOutputNames',
    'GP_float_in': 'GeneralPurposeFloatRegisterInputNames',
    'digital_out': 'DigitalOutputNames',
    'digital_in': 'DigitalInputNames',
    'analog_out': 'AnalogOutputNames',
    'analog_in': 'AnalogInputNames',
    'tool_out': 'ToolDigitalOutputNames',
    'tool_in': 'ToolDigitalInputNames',
}

# resolve_io_name で使う正規表現パターン（コンパイル済み）
_IO_NAME_PATTERN = re.compile(
    r'(' + '|'.join(re.escape(k) for k in IO_PREFIX_TO_TAG) + r')\[(\d+)\]'
)


def resolve_variable_name(var_elem, parent_map):
    """XML変数要素から名前を解決する。
    
    Args:
        var_elem: 変数のXML要素。
        parent_map: {子要素: 親要素} のマッピング辞書。
    
    Returns:
        解決された変数名。見つからない場合は空文字列。
    """
    if var_elem is None:
        return ''
    name = var_elem.attrib.get('name')
    if name:
        return name
    ref = var_elem.attrib.get('reference')
    if ref and parent_map:
        curr = var_elem
        for part in ref.split('/'):
            if part == '..':
                curr = parent_map.get(curr)
            elif part and curr is not None:
                curr = curr.find(part)
        if curr is not None and curr != var_elem:
            return curr.attrib.get('name', '')
    return ''


def resolve_io_name(name, io_manager):
    """IO名（例: "digital_out[3]"）をユーザー定義の名前に解決する。
    
    Args:
        name: IO識別子文字列。
        io_manager: IOManagerインスタンス。
    
    Returns:
        ユーザー定義名。未設定の場合は元のname。
    """
    m = _IO_NAME_PATTERN.match(name)
    if m:
        prefix = m.group(1)
        idx = int(m.group(2))
        tag = IO_PREFIX_TO_TAG.get(prefix, '')
        if tag and io_manager:
            names = io_manager.get_io_names(tag)
            if idx < len(names) and names[idx].strip():
                return names[idx].strip()
    return name


def resolve_pin_name(pin_elem, parent_map, io_manager):
    """ピン要素からIO名を解決する。
    
    Args:
        pin_elem: ピンのXML要素。
        parent_map: {子要素: 親要素} のマッピング辞書。
        io_manager: IOManagerインスタンス。
    
    Returns:
        解決されたピン名。
    """
    if pin_elem is None:
        return ""
    name = pin_elem.attrib.get('referencedName', '')
    if name:
        return resolve_io_name(name, io_manager)
        
    ref = pin_elem.attrib.get('reference', '')
    if ref and parent_map:
        curr = pin_elem
        for part in ref.split('/'):
            if part == '..':
                curr = parent_map.get(curr)
            elif part and curr is not None:
                curr = curr.find(part)
        if curr is not None and curr != pin_elem:
            name = curr.attrib.get('referencedName', '')
            if name:
                return resolve_io_name(name, io_manager)
    return ""


def parse_expression(expr_elem, parent_map, io_manager):
    """Expression要素をテキスト表現に変換する。
    
    Args:
        expr_elem: ExpressionのXML要素。
        parent_map: {子要素: 親要素} のマッピング辞書。
        io_manager: IOManagerインスタンス。
    
    Returns:
        式のテキスト表現。
    """
    if expr_elem is None:
        return ""
    
    parts = []
    for child in expr_elem.iter():
        if child.tag == 'ExpressionChar':
            parts.append(child.attrib.get('character', ''))
        elif child.tag == 'ExpressionToken':
            parts.append(child.attrib.get('token', ''))
        elif child.tag == 'ExpressionVariable':
            pv = child.find('ProgramVariable')
            if pv is not None:
                parts.append(resolve_variable_name(pv, parent_map))
            else:
                v = child.find('variable')
                if v is not None:
                    parts.append(resolve_variable_name(v, parent_map))
        elif child.tag == 'ExpressionIO':
            pin = child.find('pin')
            if pin is not None:
                name = pin.attrib.get('referencedName', '')
                parts.append(resolve_io_name(name, io_manager))
        elif child.tag == 'ExpressionWaypoint':
            wp = child.find('Waypoint')
            if wp is not None:
                parts.append(resolve_variable_name(wp, parent_map))
    return "".join(parts)
