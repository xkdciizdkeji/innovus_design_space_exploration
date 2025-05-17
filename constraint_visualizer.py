#!/usr/bin/env python
# coding: utf-8

import os
import re
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import colorsys
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec
from shapely.geometry import Polygon
import difflib

class ConstraintParser:
    """约束文件解析器，用于解析create_group命令及多边形数据"""
    
    def __init__(self, constraint_file):
        """初始化约束文件解析器
        
        Args:
            constraint_file: 约束文件路径
        """
        self.constraint_file = constraint_file
        self.groups = []  # 存储所有group信息 [(name, type, polygon_points), ...]
    
    def parse(self):
        """解析约束文件
        
        Returns:
            bool: 是否成功解析
        """
        try:
            with open(self.constraint_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 采用更可靠的方法处理 create_group 命令
            # 首先分割文件为单独的行
            lines = content.split('\n')
            
            # 找到所有 create_group 行的起始索引
            create_group_indices = [i for i, line in enumerate(lines) if 'create_group' in line]
            
            for idx in create_group_indices:
                line = lines[idx]
                
                # 提取 name 和 type
                name_match = re.search(r'-name\s+([^\s]+)', line)
                type_match = re.search(r'-type\s+(\w+)', line)
                
                if not name_match or not type_match:
                    print(f"警告: 行 {idx+1} 缺少name或type参数")
                    continue
                
                name = name_match.group(1)
                group_type = type_match.group(1)
                
                # 查找 polygon 部分，可能跨多行
                polygon_str = ""
                polygon_started = False
                open_braces = 0
                
                # 从当前行开始搜索 polygon
                for j in range(idx, len(lines)):
                    curr_line = lines[j]
                    
                    # 如果尚未开始找到 polygon 标记
                    if not polygon_started:
                        if '-polygon' in curr_line:
                            polygon_started = True
                            # 提取 -polygon 后面的部分
                            polygon_part = curr_line.split('-polygon')[1].strip()
                            polygon_str += polygon_part
                            
                            # 计算花括号
                            open_braces += polygon_part.count('{')
                            open_braces -= polygon_part.count('}')
                            
                            # 如果花括号已平衡，则polygon部分结束
                            if open_braces == 0 and '{' in polygon_part:
                                break
                    else:
                        # 继续拼接多行polygon
                        polygon_str += " " + curr_line
                        
                        # 计算花括号
                        open_braces += curr_line.count('{')
                        open_braces -= curr_line.count('}')
                        
                        # 如果花括号已平衡，则polygon部分结束
                        if open_braces == 0:
                            break
                
                # 如果找到完整的 polygon
                if polygon_str:
                    # 提取花括号之间的内容
                    brace_match = re.search(r'({.*})', polygon_str)
                    if brace_match:
                        polygon_data = brace_match.group(1)
                        points = self._parse_polygon_points(polygon_data)
                        if points:
                            self.groups.append((name, group_type, points))
                        else:
                            print(f"警告: 无法解析group '{name}' 的多边形坐标")
                    else:
                        print(f"警告: 无法在行 {idx+1} 找到有效的polygon数据")
                else:
                    print(f"警告: 行 {idx+1} 找不到polygon参数")
            
            print(f"从约束文件 {self.constraint_file} 解析了 {len(self.groups)} 个group")
            return True
            
        except Exception as e:
            print(f"解析约束文件时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_polygon_points(self, polygon_str):
        """解析多边形点坐标
        
        Args:
            polygon_str: 多边形字符串，格式如 {{x1 y1} {x2 y2} ...}
            
        Returns:
            list: 点列表 [(x1, y1), (x2, y2), ...]
        """
        try:
            # 处理双层嵌套的花括号格式 {{x1 y1} {x2 y2} ...}
            polygon_str = polygon_str.strip()
            
            # 如果是双层嵌套，去掉最外层的花括号
            if polygon_str.startswith('{') and polygon_str.endswith('}'):
                # 检查是否真的是双层格式
                inner_content = polygon_str[1:-1].strip()
                if inner_content.startswith('{') and '{' in inner_content[1:]:
                    # 使用专门针对Innovus多边形格式的正则表达式
                    point_pattern = r'{([0-9.-]+)\s+([0-9.-]+)}'
                    points = []
                    
                    for x_str, y_str in re.findall(point_pattern, polygon_str):
                        x = float(x_str)
                        y = float(y_str)
                        points.append((x, y))
                        
                    # 调试信息
                    print(f"解析到 {len(points)} 个点")
                    if not points:
                        print(f"未能从多边形字符串中解析出点，尝试另一种格式")
                        # 尝试其他可能的格式
                        try:
                            # 假设格式可能是简单的 "x1 y1 x2 y2 ..."
                            coords = re.findall(r'([0-9.-]+)\s+([0-9.-]+)', polygon_str)
                            if coords:
                                points = [(float(x), float(y)) for x, y in coords]
                                print(f"使用备选方法解析到 {len(points)} 个点")
                        except Exception as e:
                            print(f"备选解析方法也失败: {str(e)}")
                    
                    # 确保多边形闭合
                    if points and len(points) > 2 and points[0] != points[-1]:
                        points.append(points[0])
                    
                    return points
            
            # 如果不是双层格式，打印警告并继续尝试解析
            print(f"警告: 多边形字符串格式不是预期的 {{{{x1 y1}} {{x2 y2}} ...}}")
            print(f"实际字符串: {polygon_str[:100]}...")
            
            # 尝试从任意格式中提取坐标对
            coords = re.findall(r'([0-9.-]+)\s+([0-9.-]+)', polygon_str)
            if coords:
                points = [(float(x), float(y)) for x, y in coords]
                print(f"成功从非标准格式中解析出 {len(points)} 个点")
                
                # 确保多边形闭合
                if points and len(points) > 2 and points[0] != points[-1]:
                    points.append(points[0])
                
                return points
            else:
                print("无法从非标准格式中提取点坐标")
                return []
                
        except Exception as e:
            print(f"解析多边形坐标时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []


class ConstraintVisualizer:
    """约束文件可视化工具"""
    
    def __init__(self):
        """初始化可视化器"""
        self.group_colors = {}  # 存储group颜色 {group_name: color}
    
    def visualize_single_file(self, constraint_file, output_file=None):
        """可视化单个约束文件
        
        Args:
            constraint_file: 约束文件路径
            output_file: 输出图像路径，为None时显示而不保存
            
        Returns:
            bool: 是否成功可视化
        """
        # 解析约束文件
        parser = ConstraintParser(constraint_file)
        if not parser.parse():
            return False
        
        # 创建图形
        plt.figure(figsize=(15, 12))
        ax = plt.gca()
        
        # 为每个group生成颜色
        self._generate_group_colors(parser.groups)
        
        # 绘制所有group
        self._draw_groups(ax, parser.groups)
        
        # Set figure properties
        plt.title(f"Constraint File Visualization: {os.path.basename(constraint_file)}")
        plt.xlabel("X Coordinate")
        plt.ylabel("Y Coordinate")
        
        # 添加图例
        self._add_legend(ax)
        
        # 保存或显示图形
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"可视化结果已保存到: {output_file}")
        else:
            plt.tight_layout()
            plt.show()
        
        plt.close()
        return True
    
    def visualize_comparison(self, file1, file2, output_file=None):
        """可视化两个约束文件并对比差异
        
        Args:
            file1: 第一个约束文件路径
            file2: 第二个约束文件路径
            output_file: 输出图像路径，为None时显示而不保存
            
        Returns:
            bool: 是否成功可视化
        """
        # 解析两个约束文件
        parser1 = ConstraintParser(file1)
        parser2 = ConstraintParser(file2)
        
        if not parser1.parse() or not parser2.parse():
            return False
        
        # 检测差异
        diff_info = self._detect_differences(parser1.groups, parser2.groups)
        
        # 创建网格布局图形
        fig = plt.figure(figsize=(20, 12))
        gs = GridSpec(1, 2, figure=fig)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        
        # 为所有group生成颜色（合并两个文件的group）
        all_groups = parser1.groups + [g for g in parser2.groups if g[0] not in [g1[0] for g1 in parser1.groups]]
        self._generate_group_colors(all_groups)
        
        # 绘制第一个文件的groups
        self._draw_groups(ax1, parser1.groups, diff_info['file1'])
        ax1.set_title(f"File 1: {os.path.basename(file1)}")
        ax1.set_xlabel("X Coordinate")
        ax1.set_ylabel("Y Coordinate")
        
        # 绘制第二个文件的groups
        self._draw_groups(ax2, parser2.groups, diff_info['file2'])
        ax2.set_title(f"File 2: {os.path.basename(file2)}")
        ax2.set_xlabel("X Coordinate")
        ax2.set_ylabel("Y Coordinate")
        
        # 添加图例
        self._add_legend(ax1, diff_mode=True)
        self._add_legend(ax2, diff_mode=True)
        
        # Add difference summary
        diff_text = f"Difference Summary:\n"
        diff_text += f"- Only in file 1: {len(diff_info['only_in_file1'])} groups\n"
        diff_text += f"- Only in file 2: {len(diff_info['only_in_file2'])} groups\n"
        diff_text += f"- Type changed: {len(diff_info['type_changed'])} groups\n"
        diff_text += f"- Polygon changed: {len(diff_info['polygon_changed'])} groups"
        
        fig.text(0.5, 0.01, diff_text, ha='center', fontsize=12, bbox=dict(facecolor='lightgray', alpha=0.5))
        
        # 调整布局
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        
        # 保存或显示图形
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"对比可视化结果已保存到: {output_file}")
        else:
            plt.show()
        
        plt.close()
        return True
    
    def _generate_group_colors(self, groups):
        """为groups生成不同的颜色
        
        Args:
            groups: group列表 [(name, type, points), ...]
        """
        # 清空现有颜色
        self.group_colors = {}
        
        # 为每个group生成唯一颜色
        for i, (name, _, _) in enumerate(groups):
            # 使用HSV颜色空间以获得视觉上区分明显的颜色
            hue = i / max(len(groups), 1)
            saturation = 0.7 + 0.3 * (i % 2)
            value = 0.8 + 0.2 * ((i // 2) % 2)
            self.group_colors[name] = colorsys.hsv_to_rgb(hue, saturation, value)
    
    def _draw_groups(self, ax, groups, diff_markers=None):
        """在指定轴上绘制groups
        
        Args:
            ax: matplotlib轴对象
            groups: group列表 [(name, type, points), ...]
            diff_markers: 差异标记字典 {group_name: diff_type}
        """
        # 如果未提供差异标记，创建空字典
        if diff_markers is None:
            diff_markers = {}
        
        for name, group_type, points in groups:
            # 确保有足够的点来绘制多边形
            if len(points) < 3:
                print(f"警告: group '{name}' 的点数不足以构成多边形，跳过绘制")
                continue
                
            color = self.group_colors.get(name, (0.5, 0.5, 0.5))
            
            # 根据group类型设置线型
            if group_type.lower() == 'fence':
                # 使用加粗实线
                linestyle = 'solid'
                linewidth = 8.0
            elif group_type.lower() == 'guide':
                # 使用虚线
                linestyle = 'dashed'
                linewidth = 4.0
            else:  # region或其他
                # 使用普通实线
                linestyle = 'solid'
                linewidth = 4.0
            
            # 创建多边形
            poly = patches.Polygon(np.array(points), closed=True,
                                  fill=True, edgecolor=color, linewidth=linewidth,
                                  linestyle=linestyle, alpha=0.2, facecolor=color,
                                  label=f"{name} ({group_type})")
            ax.add_patch(poly)
            
            # 在多边形中心添加标签
            centroid = np.mean(points, axis=0)
            
            # 截短过长的名称
            display_name = name
            if len(display_name) > 30:
                parts = display_name.split('/')
                if len(parts) > 2:
                    display_name = '/'.join(parts[-2:])
            
            # 添加标签
            ax.text(centroid[0], centroid[1], display_name,
                    fontsize=8, ha='center', va='center',
                    bbox=dict(facecolor='white', alpha=0.7, boxstyle='round'))
            
            # 标记差异（如果有）
            diff_type = diff_markers.get(name)
            if diff_type:
                if diff_type == 'only_in_file1':
                    # Only in file 1
                    ax.text(centroid[0], centroid[1] - 0.5, "Only in file 1",
                           color='red', fontsize=8, ha='center', va='center',
                           bbox=dict(facecolor='lightyellow', alpha=0.9))
                elif diff_type == 'only_in_file2':
                    # Only in file 2
                    ax.text(centroid[0], centroid[1] - 0.5, "Only in file 2",
                           color='blue', fontsize=8, ha='center', va='center',
                           bbox=dict(facecolor='lightyellow', alpha=0.9))
                elif diff_type == 'type_changed':
                    # Type changed
                    ax.text(centroid[0], centroid[1] - 0.5, "Type changed",
                           color='purple', fontsize=8, ha='center', va='center',
                           bbox=dict(facecolor='lightyellow', alpha=0.9))
                elif diff_type == 'polygon_changed':
                    # Polygon changed
                    ax.text(centroid[0], centroid[1] - 0.5, "Polygon changed",
                           color='green', fontsize=8, ha='center', va='center',
                           bbox=dict(facecolor='lightyellow', alpha=0.9))
        
        # 设置坐标轴范围
        self._set_axis_limits(ax, groups)
        
        # 显示网格
        ax.grid(True, linestyle='--', alpha=0.7)
    
    def _set_axis_limits(self, ax, groups):
        """设置坐标轴范围
        
        Args:
            ax: matplotlib轴对象
            groups: group列表 [(name, type, points), ...]
        """
        # 收集所有点
        all_points = []
        for _, _, points in groups:
            all_points.extend(points)
        
        if all_points:
            all_x = [p[0] for p in all_points]
            all_y = [p[1] for p in all_points]
            
            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)
            
            # 添加边距
            margin = 0.05 * max(x_max - x_min, y_max - y_min)
            ax.set_xlim(x_min - margin, x_max + margin)
            ax.set_ylim(y_min - margin, y_max + margin)
    
    def _add_legend(self, ax, diff_mode=False):
        """添加图例
        
        Args:
            ax: matplotlib轴对象
            diff_mode: 是否为对比模式
        """
        # 创建线型示例
        line_examples = [
            Line2D([0], [0], color='black', linewidth=4, linestyle='solid', label='fence'),
            Line2D([0], [0], color='black', linewidth=2, linestyle='dashed', label='guide'),
            Line2D([0], [0], color='black', linewidth=2, linestyle='solid', label='region')
        ]
        
        # 如果是对比模式，添加差异标记说明
        if diff_mode:
            diff_examples = [
                Line2D([0], [0], marker='o', color='w', markersize=8, 
                      markerfacecolor='red', label='Only in file 1'),
                Line2D([0], [0], marker='o', color='w', markersize=8, 
                      markerfacecolor='blue', label='Only in file 2'),
                Line2D([0], [0], marker='o', color='w', markersize=8, 
                      markerfacecolor='purple', label='Type changed'),
                Line2D([0], [0], marker='o', color='w', markersize=8, 
                      markerfacecolor='green', label='Polygon changed')
            ]
            line_examples.extend(diff_examples)
        
        # 添加图例
        legend = ax.legend(handles=line_examples, 
                         title="Group Types & Differences", 
                         loc='upper right', 
                         fontsize='small',
                         bbox_to_anchor=(1, 1))
        ax.add_artist(legend)
    
    def _detect_differences(self, groups1, groups2):
        """检测两组groups之间的差异
        
        Args:
            groups1: 第一个文件的groups
            groups2: 第二个文件的groups
            
        Returns:
            dict: 差异信息
        """
        # 构建group名称到group的映射
        groups1_dict = {name: (group_type, points) for name, group_type, points in groups1}
        groups2_dict = {name: (group_type, points) for name, group_type, points in groups2}
        
        # 查找差异
        only_in_file1 = [name for name in groups1_dict if name not in groups2_dict]
        only_in_file2 = [name for name in groups2_dict if name not in groups1_dict]
        
        type_changed = []
        polygon_changed = []
        
        # 检查共有的groups
        common_names = set(groups1_dict.keys()) & set(groups2_dict.keys())
        for name in common_names:
            type1, points1 = groups1_dict[name]
            type2, points2 = groups2_dict[name]
            
            # 检查类型变化
            if type1 != type2:
                type_changed.append(name)
            
            # 检查多边形变化
            if self._polygon_changed(points1, points2):
                polygon_changed.append(name)
        
        # 构建差异标记信息
        file1_diff_markers = {}
        file2_diff_markers = {}
        
        for name in only_in_file1:
            file1_diff_markers[name] = 'only_in_file1'
            
        for name in only_in_file2:
            file2_diff_markers[name] = 'only_in_file2'
            
        for name in type_changed:
            file1_diff_markers[name] = 'type_changed'
            file2_diff_markers[name] = 'type_changed'
            
        for name in polygon_changed:
            file1_diff_markers[name] = 'polygon_changed'
            file2_diff_markers[name] = 'polygon_changed'
        
        return {
            'only_in_file1': only_in_file1,
            'only_in_file2': only_in_file2,
            'type_changed': type_changed,
            'polygon_changed': polygon_changed,
            'file1': file1_diff_markers,
            'file2': file2_diff_markers
        }
    
    def _polygon_changed(self, points1, points2):
        """检测两个多边形是否有变化
        
        Args:
            points1: 第一个多边形的点列表
            points2: 第二个多边形的点列表
            
        Returns:
            bool: 是否有变化
        """
        # 快速检查：点数不同
        if len(points1) != len(points2):
            return True
        
        # 创建shapely多边形对象进行比较
        try:
            poly1 = Polygon(points1)
            poly2 = Polygon(points2)
            
            # 检查差异
            difference = poly1.symmetric_difference(poly2)
            
            # 如果差异面积很小（考虑浮点数精度问题），认为多边形相同
            return difference.area > 1e-10
            
        except Exception:
            # 如果创建多边形失败，直接比较点坐标
            return points1 != points2


def main():
    parser = argparse.ArgumentParser(description='约束文件可视化工具')
    parser.add_argument('file1', help='第一个约束文件路径')
    parser.add_argument('--file2', '-f2', help='第二个约束文件路径（用于对比可视化）')
    parser.add_argument('--output', '-o', default='constraint_visualization.png', help='输出图像路径')
    
    args = parser.parse_args()
    
    visualizer = ConstraintVisualizer()
    
    if args.file2:
        print(f"对比可视化: {args.file1} 和 {args.file2}")
        visualizer.visualize_comparison(args.file1, args.file2, args.output)
    else:
        print(f"单文件可视化: {args.file1}")
        visualizer.visualize_single_file(args.file1, args.output)


if __name__ == "__main__":
    main()


'''
使用方法：
可视化单个约束文件：python constraint_visualizer.py constraint_file.tcl
可视化并对比两个约束文件：python constraint_visualizer.py constraint_file1.tcl constraint_file2.tcl
'''