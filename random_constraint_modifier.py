import random
import re
import sys
import os
import copy

def modify_type_parameter(line):
    """
    将 -type 参数随机修改为 guide, region 或 fence 中的一种
    
    参数:
        line (str): 包含 create_group 的行
    
    返回:
        str: 修改后的行
    """
    types = ["guide", "region", "fence"]
    # 使用正则表达式找到并替换 -type 后的参数
    pattern = r'(-type\s+)(\w+)'
    match = re.search(pattern, line)
    if match:
        prefix = match.group(1)
        new_type = random.choice(types)
        return re.sub(pattern, f"{prefix}{new_type}", line)
    return line

def parse_polygon_points(polygon_str):
    """
    解析多边形点序列字符串，返回点列表
    
    参数:
        polygon_str (str): 多边形字符串，格式如 {{x1 y1} {x2 y2} ...}
    
    返回:
        list: 点列表，每个点是 [x, y] 的形式
    """
    # 提取所有的点
    point_pattern = r'{([0-9.]+)\s+([0-9.]+)}'
    points = re.findall(point_pattern, polygon_str)
    # 转换为浮点数
    return [[float(x), float(y)] for x, y in points]

def points_to_polygon_str(points):
    """
    将点列表转换回多边形字符串
    
    参数:
        points (list): 点列表，每个点是 [x, y] 的形式
    
    返回:
        str: 多边形字符串，格式如 {{x1 y1} {x2 y2} ...}
    """
    point_strs = [f"{{{x} {y}}}" for x, y in points]
    return "{" + " ".join(point_strs) + "}"

def extract_rectangles(points):
    """
    从多边形点序列中提取出组成阶梯状多边形的矩形
    假设多边形是由固定高度但不同宽度的矩形堆叠而成
    
    参数:
        points (list): 点列表，每个点是 [x, y] 的形式
    
    返回:
        list: 矩形列表，每个矩形由 [[左下x, 左下y], [右上x, 右上y]] 表示
    """
    # 按y坐标排序点
    sorted_points = sorted(points, key=lambda p: p[1])
    
    # 找出所有不同的y坐标（高度级别）
    heights = sorted(set(p[1] for p in sorted_points))
    
    # 对每个高度，找出该高度对应的最左和最右的x坐标
    rectangles = []
    for i in range(len(heights) - 1):
        y_bottom = heights[i]
        y_top = heights[i+1]
        
        # 找出在底部和顶部的所有点
        bottom_points = [p[0] for p in sorted_points if p[1] == y_bottom]
        top_points = [p[0] for p in sorted_points if p[1] == y_top]
        
        # 找出矩形的左右边界
        left_x = max(min(bottom_points), min(top_points))
        right_x = min(max(bottom_points), max(top_points))
        
        # 添加矩形 [左下角, 右上角]
        rectangles.append([[left_x, y_bottom], [right_x, y_top]])
    
    return rectangles

def rectangles_to_points(rectangles):
    """
    将矩形列表转换回多边形点序列
    
    参数:
        rectangles (list): 矩形列表，每个矩形由 [[左下x, 左下y], [右上x, 右上y]] 表示
    
    返回:
        list: 点列表，以逆时针顺序排列
    """
    # 按底部y坐标排序矩形
    sorted_rects = sorted(rectangles, key=lambda r: r[0][1])
    
    points = []
    for i, rect in enumerate(sorted_rects):
        left_bottom_x, bottom_y = rect[0]
        right_bottom_x, _ = rect[1]
        
        # 添加左下角点
        if i == 0 or left_bottom_x != sorted_rects[i-1][0][0]:
            points.append([left_bottom_x, bottom_y])
        
        # 添加右下角点
        if i == 0 or right_bottom_x != sorted_rects[i-1][1][0]:
            points.append([right_bottom_x, bottom_y])
    
    # 添加右上角点（从上到下）
    for i in range(len(sorted_rects) - 1, -1, -1):
        rect = sorted_rects[i]
        right_top_x, top_y = rect[1]
        
        if i == len(sorted_rects) - 1 or right_top_x != sorted_rects[i+1][1][0]:
            points.append([right_top_x, top_y])
    
    # 添加左上角点（从上到下）
    for i in range(len(sorted_rects) - 1, -1, -1):
        rect = sorted_rects[i]
        left_top_x, top_y = rect[0][0], rect[1][1]
        
        if i == len(sorted_rects) - 1 or left_top_x != sorted_rects[i+1][0][0]:
            points.append([left_top_x, top_y])
    
    return points

def perform_edge_shift(polygon_str, shift_distance=1.0):
    """
    对多边形执行edge_shift操作，随机选择一个矩形，修改其宽度
    
    参数:
        polygon_str (str): 多边形字符串
        shift_distance (float): 移动距离
    
    返回:
        str: 修改后的多边形字符串
    """
    # 解析多边形点
    points = parse_polygon_points(polygon_str)
    
    # 提取矩形
    rectangles = extract_rectangles(points)
    if not rectangles:
        return polygon_str
    
    # 随机选择一个矩形
    rect_idx = random.randint(0, len(rectangles) - 1)
    rect = rectangles[rect_idx]
    
    # 随机选择左边或右边进行移动
    edge_to_move = random.choice(["left", "right"])
    # 随机选择向内或向外移动
    direction = random.choice([-1, 1])  # -1表示向内，1表示向外
    
    # 计算实际移动距离
    actual_shift = direction * shift_distance
    
    # 应用移动
    if edge_to_move == "left":
        # 确保移动后矩形宽度仍为正数
        if rect[0][0] + actual_shift < rect[1][0]:
            rect[0][0] += actual_shift
    else:  # right
        # 确保移动后矩形宽度仍为正数
        if rect[1][0] + actual_shift > rect[0][0]:
            rect[1][0] += actual_shift
    
    # 转换回点序列
    modified_points = rectangles_to_points(rectangles)
    
    # 转换回字符串
    return points_to_polygon_str(modified_points)

def add_boundary_rectangle(polygon_str):
    """
    在多边形的上方或下方增加一个边界矩形
    
    参数:
        polygon_str (str): 多边形字符串
    
    返回:
        str: 修改后的多边形字符串
    """
    # 解析多边形点
    points = parse_polygon_points(polygon_str)
    
    # 提取矩形
    rectangles = extract_rectangles(points)
    if not rectangles:
        return polygon_str
    
    # 随机选择在上方或下方添加
    position = random.choice(["top", "bottom"])
    
    if position == "top":
        # 获取最上面的矩形
        top_rect = max(rectangles, key=lambda r: r[1][1])
        # 创建新矩形，与最上面矩形宽度相同，高度相同
        top_y = top_rect[1][1]
        height = top_rect[1][1] - top_rect[0][1]
        new_rect = [
            [top_rect[0][0], top_y],
            [top_rect[1][0], top_y + height]
        ]
        rectangles.append(new_rect)
    else:  # bottom
        # 获取最下面的矩形
        bottom_rect = min(rectangles, key=lambda r: r[0][1])
        # 创建新矩形，与最下面矩形宽度相同，高度相同
        bottom_y = bottom_rect[0][1]
        height = bottom_rect[1][1] - bottom_rect[0][1]
        new_rect = [
            [bottom_rect[0][0], bottom_y - height],
            [bottom_rect[1][0], bottom_y]
        ]
        rectangles.append(new_rect)
    
    # 转换回点序列
    modified_points = rectangles_to_points(rectangles)
    
    # 转换回字符串
    return points_to_polygon_str(modified_points)

def remove_boundary_rectangle(polygon_str):
    """
    从多边形的上方或下方移除一个边界矩形
    
    参数:
        polygon_str (str): 多边形字符串
    
    返回:
        str: 修改后的多边形字符串，如果只剩一个矩形则返回原字符串
    """
    # 解析多边形点
    points = parse_polygon_points(polygon_str)
    
    # 提取矩形
    rectangles = extract_rectangles(points)
    
    # 如果只剩一个或没有矩形，则不做修改
    if len(rectangles) <= 1:
        return polygon_str
    
    # 随机选择移除上方或下方的矩形
    position = random.choice(["top", "bottom"])
    
    if position == "top":
        # 移除最上面的矩形
        top_rect = max(rectangles, key=lambda r: r[1][1])
        rectangles.remove(top_rect)
    else:  # bottom
        # 移除最下面的矩形
        bottom_rect = min(rectangles, key=lambda r: r[0][1])
        rectangles.remove(bottom_rect)
    
    # 转换回点序列
    modified_points = rectangles_to_points(rectangles)
    
    # 转换回字符串
    return points_to_polygon_str(modified_points)

def move_entire_polygon(polygon_str, move_distance=1.0):
    """
    整体移动多边形
    
    参数:
        polygon_str (str): 多边形字符串
        move_distance (float): 移动距离
    
    返回:
        str: 修改后的多边形字符串
    """
    # 解析多边形点
    points = parse_polygon_points(polygon_str)
    
    # 随机选择移动方向
    direction = random.choice(["up", "down", "left", "right"])
    
    # 根据方向移动所有点
    for i in range(len(points)):
        if direction == "up":
            points[i][1] += move_distance
        elif direction == "down":
            points[i][1] -= move_distance
        elif direction == "left":
            points[i][0] -= move_distance
        elif direction == "right":
            points[i][0] += move_distance
    
    # 转换回字符串
    return points_to_polygon_str(points)

def modify_constraint_file(input_file, output_file, modification_type=None, shift_distance=1.0):
    """
    修改约束文件中的create_group行
    
    参数:
        input_file (str): 输入文件路径
        output_file (str): 输出文件路径
        modification_type (str, optional): 修改类型，如果为None则随机选择
        shift_distance (float): 移动距离
    
    返回:
        None
    """
    # 可用的修改类型
    mod_types = [
        "type_parameter",    # 修改-type参数
        "edge_shift",        # 边缘移动
        "add_boundary",      # 添加边界矩形
        "remove_boundary",   # 移除边界矩形
        "move_entire"        # 整体移动
    ]
    
    # 如果未指定修改类型，随机选择一种
    if modification_type is None:
        modification_type = random.choice(mod_types)
    
    # 读取文件内容
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # 找出所有包含create_group的行的索引
    create_group_lines = [i for i, line in enumerate(lines) if "create_group" in line]
    
    if not create_group_lines:
        print("未找到create_group行，保持文件不变。")
        with open(output_file, 'w') as f:
            f.writelines(lines)
        return
    
    # 随机选择一行进行修改
    line_index = random.choice(create_group_lines)
    line = lines[line_index]
    
    # 提取-polygon部分
    polygon_pattern = r'(-polygon\s+)({.*})'
    polygon_match = re.search(polygon_pattern, line)
    
    if polygon_match and modification_type != "type_parameter":
        prefix = polygon_match.group(1)
        polygon_str = polygon_match.group(2)
        
        # 根据选择的修改类型进行修改
        if modification_type == "edge_shift":
            modified_polygon = perform_edge_shift(polygon_str, shift_distance)
        elif modification_type == "add_boundary":
            modified_polygon = add_boundary_rectangle(polygon_str)
        elif modification_type == "remove_boundary":
            modified_polygon = remove_boundary_rectangle(polygon_str)
        elif modification_type == "move_entire":
            modified_polygon = move_entire_polygon(polygon_str, shift_distance)
        
        # 替换原来的多边形部分
        modified_line = re.sub(polygon_pattern, f"{prefix}{modified_polygon}", line)
        lines[line_index] = modified_line
    elif modification_type == "type_parameter":
        # 修改-type参数
        modified_line = modify_type_parameter(line)
        lines[line_index] = modified_line
    
    # 写入修改后的内容到输出文件
    with open(output_file, 'w') as f:
        f.writelines(lines)

def main():
    """主函数，处理命令行参数并调用相应的函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='随机修改约束文件的工具')
    parser.add_argument('input_file', help='输入约束文件的路径')
    parser.add_argument('--output_file', help='输出文件的路径（默认为原文件名加_modified后缀）')
    parser.add_argument('--modification_type', choices=['type_parameter', 'edge_shift', 'add_boundary', 'remove_boundary', 'move_entire'],
                       help='指定修改类型，如果不指定则随机选择')
    parser.add_argument('--shift_distance', type=float, default=1.0,
                       help='移动距离（用于edge_shift和move_entire操作，默认为1.0）')
    
    args = parser.parse_args()
    
    # 如果未指定输出文件，生成默认名称
    if not args.output_file:
        base_name, ext = os.path.splitext(args.input_file)
        args.output_file = f"{base_name}_modified{ext}"
    
    # 执行修改
    modify_constraint_file(args.input_file, args.output_file, args.modification_type, args.shift_distance)
    print(f"修改已完成，结果保存到 {args.output_file}")

if __name__ == "__main__":
    main() 



'''

使用示例:
python random_constraint_modifier.py 输入文件 [--output_file 输出文件] [--modification_type 修改类型] [--shift_distance 移动距离]

edge_shift: 边缘移动
python random_constraint_modifier.py input.txt --modification_type edge_shift [--shift_distance 移动距离]
add_boundary: 添加边界矩形
python random_constraint_modifier.py input.txt --modification_type add_boundary
remove_boundary: 移除边界矩形
python random_constraint_modifier.py input.txt --modification_type remove_boundary
move_entire: 整体移动
python random_constraint_modifier.py input.txt --modification_type move_entire [--shift_distance 移动距离]








其他文件调用:
from random_constraint_modifier import modify_constraint_file

# 随机选择一种修改方式
modify_constraint_file("input.txt", "output.txt")

# 指定修改类型
modify_constraint_file("input.txt", "output.txt", "edge_shift", 2.0)
'''