import re
import sys
import os

def extract_data_from_logv(logv_file):
    """
    从innovus生成的logv文件中提取总线长、总过孔数和总运行时间
    
    参数:
        logv_file (str): logv文件路径
    
    返回:
        dict: 包含提取数据的字典，键有 'total_net_length', 'total_via_count', 'total_runtime'
    """
    # 初始化结果字典
    result = {
        'total_net_length': None,
        'total_via_count': None,
        'total_runtime': None
    }
    
    # 读取整个文件内容
    try:
        with open(logv_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return result
    
    # 找到所有 report_route -summary 命令块
    report_route_blocks = re.findall(r'\[.*?\] <CMD> report_route -summary.*?(?=\[.*?\] <CMD>|\Z)', content, re.DOTALL)
    
    if not report_route_blocks:
        print("未找到report_route -summary命令块")
        return result
    
    # 取最后一个report_route命令块
    last_report_block = report_route_blocks[-1]
    
    # 提取总线长
    total_net_length_match = re.search(r'Total net length = ([\d.]+)', last_report_block)
    if total_net_length_match:
        result['total_net_length'] = float(total_net_length_match.group(1))
    
    # 提取总过孔数
    # 先定位到Via Count Statistics部分
    via_stats_section = re.search(r'Via Count Statistics :.*?\+\-+\+\-+\+\s*\|\s*Total\s*\|\s*(\d+)\s*\|', last_report_block, re.DOTALL)
    if via_stats_section:
        result['total_via_count'] = int(via_stats_section.group(1))
    
    # 提取总运行时间（文件最后一行）
    last_line_match = re.search(r'\[.*?\s+(\d+)s\] --- Ending "Innovus"', content)
    if last_line_match:
        result['total_runtime'] = int(last_line_match.group(1))
    
    return result

def print_results(data):
    """打印提取的数据"""
    print("\n=== 提取的报告数据 ===")
    
    if data['total_net_length'] is not None:
        print(f"总线长: {data['total_net_length']} um")
    else:
        print("总线长: 未找到")
    
    if data['total_via_count'] is not None:
        print(f"总过孔数: {data['total_via_count']}")
    else:
        print("总过孔数: 未找到")
    
    if data['total_runtime'] is not None:
        print(f"总运行时间: {data['total_runtime']} 秒")
    else:
        print("总运行时间: 未找到")
    
    print("======================\n")

def main():
    """主函数，处理命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从innovus logv文件中提取路由报告数据')
    parser.add_argument('logv_file', help='logv文件路径')
    
    args = parser.parse_args()
    
    if not os.path.isfile(args.logv_file):
        print(f"错误: 文件 '{args.logv_file}' 不存在")
        return 1
    
    # 提取数据
    data = extract_data_from_logv(args.logv_file)
    
    # 打印结果
    print_results(data)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 


'''
使用示例:
python extract_route_report.py innovus_output_1x/case_1_1x_100/case_1_1x_100_route/case_1_1x_100_route.logv







调用方式:
from extract_route_report import extract_data_from_logv

# 提取数据
data = extract_data_from_logv("your_logv_file.logv")

# 使用提取的数据
total_net_length = data['total_net_length']  # 总线长
total_via_count = data['total_via_count']    # 总过孔数
total_runtime = data['total_runtime']        # 总运行时间

'''