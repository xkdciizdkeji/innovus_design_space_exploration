"""
DEF文件参数提取模块
用于从DEF文件中提取特定参数
"""

import re


def extract_units(def_content):
    """提取版图长度单位"""
    match = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;', def_content)
    if match:
        return int(match.group(1))
    return None


def extract_dimensions(def_content):
    """提取版图尺寸"""
    # 匹配X和Y的上限坐标值
    ur_x_match = re.search(r'DESIGN\s+FE_CORE_BOX_UR_X\s+REAL\s+([0-9.]+)\s*;', def_content)
    ur_y_match = re.search(r'DESIGN\s+FE_CORE_BOX_UR_Y\s+REAL\s+([0-9.]+)\s*;', def_content)
    
    if ur_x_match and ur_y_match:
        width = float(ur_x_match.group(1))
        height = float(ur_y_match.group(1))
        return width, height
    return None


def extract_row_height(def_content, units):
    """提取row高度"""
    # 匹配前两行ROW定义
    rows = re.findall(r'ROW\s+\S+\s+\S+\s+\d+\s+(\d+)', def_content, re.MULTILINE)
    if len(rows) >= 2:
        # 计算实际高度 = (第二行Y坐标 - 第一行Y坐标) / 单位
        row_height = (int(rows[1]) - int(rows[0])) / units
        return row_height
    return None


def extract_instance_groups(def_content):
    """提取instance_group列表"""
    # 匹配REGIONS部分
    regions_match = re.search(r'REGIONS\s+\d+\s*;(.*?)END\s+REGIONS', def_content, re.DOTALL)
    if not regions_match:
        return []
    
    regions_content = regions_match.group(1)
    # 提取每个instance_group的名称
    groups = re.findall(r'-\s+(\S+)\s+\(', regions_content)
    return groups


def parse_def_file(def_file_path):
    """解析DEF文件并提取所需参数"""
    try:
        with open(def_file_path, 'r') as file:
            def_content = file.read()
        
        # 提取各参数
        units = extract_units(def_content)
        dimensions = extract_dimensions(def_content)
        row_height = extract_row_height(def_content, units)
        instance_groups = extract_instance_groups(def_content)
        
        # 构建结果字典
        results = {
            'units': units,
            'dimensions': f"{dimensions[0]}*{dimensions[1]}" if dimensions else None,
            'row_height': row_height,
            'instance_groups': instance_groups
        }
        
        return results
    except Exception as e:
        print(f"解析DEF文件时出错: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python def_parser.py <def_file_path>")
        sys.exit(1)
    
    results = parse_def_file(sys.argv[1])
    if results:
        print(f"版图长度单位: {results['units']}")
        print(f"版图尺寸: {results['dimensions']}")
        print(f"Row高度: {results['row_height']}")
        print(f"Instance groups数量: {len(results['instance_groups'])}")
        print("Instance groups列表:")
        for group in results['instance_groups']:
            print(f"  - {group}")
