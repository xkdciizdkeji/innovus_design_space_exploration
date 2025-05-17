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
    
    try:
        # 按行读取文件
        with open(logv_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return result
    
    # 查找 report_route -summary 命令的所有位置
    summary_positions = []
    for i, line in enumerate(lines):
        if "<CMD> report_route -summary" in line:
            summary_positions.append(i)
    
    if not summary_positions:
        print(f"未在 {logv_file} 中找到 report_route -summary 命令")
        return result
    
    # 使用最后一个报告块
    pos = summary_positions[-1]
    
    # 提取总线长 - 从命令位置向下搜索
    for j in range(pos, min(pos + 200, len(lines))):
        if "Total net length =" in lines[j]:
            wire_match = re.search(r'Total net length = ([\d\.]+)', lines[j])
            if wire_match:
                result['total_net_length'] = float(wire_match.group(1))
            break
    
    # 提取总过孔数 - 先找到 Via Count Statistics 部分
    via_section_start = -1
    for j in range(pos, min(pos + 200, len(lines))):
        if "Via Count Statistics :" in lines[j]:
            via_section_start = j
            break
    
    # 在该部分中查找 Total 行
    if via_section_start > 0:
        for j in range(via_section_start, min(via_section_start + 50, len(lines))):
            if "|     Total      |" in lines[j]:
                via_match = re.search(r'\|\s+Total\s+\|\s+(\d+)\s+\|', lines[j])
                if via_match:
                    result['total_via_count'] = int(via_match.group(1))
                break
    
    # 从最后一行提取总运行时间
    for i in range(len(lines)-1, max(0, len(lines)-50), -1):  # 从末尾向上搜索最多50行
        if "--- Ending \"Innovus\"" in lines[i]:
            time_match = re.search(r'\[\d+/\d+ \d+:\d+:\d+\s+(\d+)s\]', lines[i])
            if time_match:
                result['total_runtime'] = int(time_match.group(1))
            break
    
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