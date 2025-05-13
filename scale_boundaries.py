#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import os
import argparse

def scale_boundaries(input_file, output_file, original_size, target_size, precision=6):
    """
    按指定比例放缩boundaries文件中的多边形坐标
    
    参数:
        input_file: 输入文件路径
        output_file: 输出文件路径
        original_size: 原始尺寸，格式为 (x0, y0)
        target_size: 目标尺寸，格式为 (x1, y1)
        precision: 输出坐标的小数位数
    """
    # 计算x和y方向的缩放比例
    x_scale = target_size[0] / original_size[0]
    y_scale = target_size[1] / original_size[1]
    
    print(f"缩放比例: x方向 = {x_scale:.6f}, y方向 = {y_scale:.6f}")
    
    try:
        # 读取输入文件
        with open(input_file, 'r') as f:
            content = f.read()
        
        # 找到所有坐标点并替换
        def scale_coords(match):
            x = float(match.group(1)) * x_scale
            y = float(match.group(2)) * y_scale
            return f"{x:.{precision}f},{y:.{precision}f};"
        
        # 使用正则表达式替换所有坐标点
        scaled_content = re.sub(r'([-\d.]+),([-\d.]+);', scale_coords, content)
        
        # 写入输出文件
        with open(output_file, 'w') as f:
            f.write(scaled_content)
        
        print(f"成功放缩boundaries文件并保存到 {output_file}")
        
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return False
    
    return True

def batch_scale_boundaries(input_dir, output_dir, original_size, target_size, precision=6, appendix=''):
    """
    批量处理文件夹中的所有boundaries文件
    
    参数:
        input_dir: 输入文件夹路径
        output_dir: 输出文件夹路径
        original_size: 原始尺寸，格式为 (x0, y0)
        target_size: 目标尺寸，格式为 (x1, y1)
        precision: 输出坐标的小数位数
        appendix: 输出文件名的后缀
    
    返回:
        (成功处理的文件数, 处理失败的文件数)
    """
    # 确保输出文件夹存在
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    # 遍历输入文件夹中的所有文件
    for filename in os.listdir(input_dir):
        input_file = os.path.join(input_dir, filename)
        
        # 添加后缀到文件名
        if appendix:
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}{appendix}{ext}"
        else:
            output_filename = filename
            
        output_file = os.path.join(output_dir, output_filename)
        
        # 只处理常规文件，跳过子文件夹
        if os.path.isfile(input_file):
            print(f"\n处理文件: {filename} -> {output_filename}")
            if scale_boundaries(input_file, output_file, original_size, target_size, precision):
                success_count += 1
            else:
                fail_count += 1
    
    return success_count, fail_count

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='放缩boundaries文件中的多边形坐标')
    parser.add_argument('input', help='输入boundaries文件路径或文件夹路径(批处理模式)')
    parser.add_argument('output', help='输出boundaries文件路径或文件夹路径(批处理模式)')
    parser.add_argument('--original', '-o', nargs=2, type=float, required=True,
                        metavar=('X0', 'Y0'), help='原始版图大小 (x0 y0)')
    parser.add_argument('--target', '-t', nargs=2, type=float, required=True,
                        metavar=('X1', 'Y1'), help='目标版图大小 (x1 y1)')
    parser.add_argument('--precision', '-p', type=int, default=6,
                        help='输出坐标的小数位数 (默认: 6)')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='批处理模式，处理整个文件夹')
    parser.add_argument('--appendix', '-a', type=str, default='',
                        help='输出文件名的后缀 (例如: "_scaled")')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    original_size = (args.original[0], args.original[1])
    target_size = (args.target[0], args.target[1])
    
    print(f"原始版图大小: ({original_size[0]}, {original_size[1]})")
    print(f"目标版图大小: ({target_size[0]}, {target_size[1]})")
    
    if args.appendix:
        print(f"输出文件名后缀: {args.appendix}")
    
    if args.batch:
        print(f"批处理模式: 从 {args.input} 处理到 {args.output}")
        success_count, fail_count = batch_scale_boundaries(
            args.input, args.output, original_size, target_size, args.precision, args.appendix)
        
        print(f"\n处理完成: 成功 {success_count} 个文件, 失败 {fail_count} 个文件")
        return 0 if fail_count == 0 else 1
    else:
        # 单个文件处理时的输出文件路径处理
        output_path = args.output
        if args.appendix:
            dir_name = os.path.dirname(output_path)
            basename = os.path.basename(output_path)
            name, ext = os.path.splitext(basename)
            new_basename = f"{name}{args.appendix}{ext}"
            output_path = os.path.join(dir_name, new_basename)
            print(f"输出文件: {output_path}")
            
        success = scale_boundaries(args.input, output_path, original_size, target_size, args.precision)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())


'''
运行示例：
单个处理:
python scale_boundaries.py ./boundaries/boundary_4x4systolic-array_areacoverage.txt ./scaled_boundaries/boundary_4x4systolic-array_areacoverage.txt --original 70 70 --target 126.864 126.360
python scale_boundaries.py .\boundaries\boundary_fft8_250321_layout-cover_new.txt .\boundaries\boundary_fft8_250321_layout-cover_scaled.txt --original 235 235 --target 234.576 234.360

批量处理:
python .\scale_boundaries.py .\boundaries\10\ .\scaled_boundaries\10\ --original 70 70 --target 126.864 126.360 --batch

加后缀:
python .\scale_boundaries.py .\boundaries\10\ .\scaled_boundaries\10\ --original 70 70 --target 126.864 126.360 --batch --appendix _scaled
'''