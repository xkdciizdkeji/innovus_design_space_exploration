import os
import sys
import argparse
import subprocess
import time
import shutil
import random
import math
import matplotlib.pyplot as plt
import datetime
from decimal import Decimal
# 导入DEF解析器模块
from def_parser import parse_def_file
# 导入提取路由报告数据的模块
from extract_route_report import extract_data_from_logv
# 导入约束修改模块
from random_constraint_modifier import modify_constraint_file


# os.system("cd /mnt/hgfs/vm_share/eda/innovus_output_dse")
# os.system("./run_innovus_preparation.sh")

def analyze_def_file(def_file_path):
    """分析DEF文件并打印结果"""
    print(f"正在分析DEF文件: {def_file_path}")
    results = parse_def_file(def_file_path)
    if results:
        print("\n提取的参数:")
        print(f"版图长度单位: {results['units']}")
        print(f"版图尺寸: {results['dimensions']}")
        print(f"Row高度: {results['row_height']}")
        print(f"Instance groups数量: {len(results['instance_groups'])}")
        print("Instance groups列表:")
        for group in results['instance_groups']:
            print(f"  - {group}")
        return results
    else:
        print("DEF文件解析失败")
        return None

def run_innovus(case, boundary, core_utilization, iteration):
    """
    运行Innovus脚本
    
    参数:
        case: 案例名称
        boundary: 边界名称
        core_utilization: 核心利用率
        iteration: 迭代次数
    
    返回:
        bool: 是否成功运行
    """
    # cmd = f"./run_innovus_dynamic.sh {case} {boundary} {core_utilization} {iteration}"
    cmd = f"./run_innovus_dynamic.sh {case} {boundary} {core_utilization} {iteration} place"
    print(f"执行命令: {cmd}")
    
    try:
        return_code = os.system(cmd)
        if return_code != 0:
            print(f"运行Innovus失败，返回码: {return_code}")
            return False
        return True
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False


def generate_random_constraint(input_file, output_file, modification_type=None, shift_distance=1.0, num_groups=1, modifications_per_group=1):
    """
    生成随机约束文件
    
    参数:
        input_file: 输入约束文件
        output_file: 输出约束文件
        modification_type: 修改类型，如果为None则随机选择
        shift_distance: 移动距离
        num_groups: 要修改的组数量，默认为1
        modifications_per_group: 每个组要执行的修改次数，默认为1
    
    返回:
        list: 使用的修改类型列表
    """
    # 可用的修改类型
    mod_types = [
        "type_parameter",    # 修改-type参数
        "edge_shift",        # 边缘移动
        "add_boundary",      # 添加边界矩形
        "remove_boundary",   # 移除边界矩形
        "move_entire"        # 整体移动
    ]
    
    # 调用constraint修改函数
    modification_types_used = modify_constraint_file(input_file, output_file, modification_type, 
                                                   shift_distance, num_groups, modifications_per_group)
    
    return modification_types_used

def simulated_annealing(case, boundary, core_utilization, max_iterations=100, initial_temperature=1.0, cooling_rate=0.99, min_temperature=0.01, high_temp_ratio=0.7, low_temp_ratio=0.3):
    """
    执行模拟退火算法
    
    参数:
        case: 案例名称
        boundary: 边界名称
        core_utilization: 核心利用率
        max_iterations: 最大迭代次数
        initial_temperature: 初始温度
        cooling_rate: 冷却率
        min_temperature: 最小温度
        high_temp_ratio: 高温阈值比例（相对于初始温度）
        low_temp_ratio: 低温阈值比例（相对于初始温度）
    
    返回:
        dict: 包含最佳结果的字典
    """
    # 获取当前时间作为日志文件名的一部分
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{current_time}__{case}__{boundary}__{core_utilization}.txt"
    
    # 创建日志文件并写入头部信息
    with open(log_file, "w") as f:
        f.write(f"# 模拟退火算法优化日志\n")
        f.write(f"# 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 案例: {case}\n")
        f.write(f"# 边界: {boundary}\n")
        f.write(f"# 核心利用率: {core_utilization}\n")
        f.write(f"# 最大迭代次数: {max_iterations}\n")
        f.write(f"# 初始温度: {initial_temperature}\n")
        f.write(f"# 冷却率: {cooling_rate}\n")
        f.write(f"# 最小温度: {min_temperature}\n")
        f.write(f"# 高温阈值比例: {high_temp_ratio}\n")
        f.write(f"# 低温阈值比例: {low_temp_ratio}\n")
        f.write("\n")
        f.write("iteration,modification_type,total_net_length,total_via_count,runtime,loss,loss_change,temperature,accepted,num_groups,modifications_per_group,max_shift_distance\n")
    
    # 执行初始迭代
    print(f"执行初始迭代 (iteration 0)...")
    success = run_innovus(case, boundary, core_utilization, 0)
    if not success:
        print("初始迭代失败，退出程序")
        return None
    
    # 提取初始结果
    # logv_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__${case}__core_utilization__${core_utilization}__boundary__${boundary}__iter__0/innovus.logv"
    logv_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{case}__core_utilization__{core_utilization}__boundary__{boundary}__iter__0/innovus.logv"
    initial_data = extract_data_from_logv(logv_path)
    
    if initial_data['total_net_length'] is None:
        print("无法从初始迭代中提取总线长，退出程序")
        return None
    
    # 初始化最佳结果
    best_result = {
        'iteration': 0,
        'total_net_length': initial_data['total_net_length'],
        'total_via_count': initial_data['total_via_count'],
        'runtime': initial_data['total_runtime'],
        'constraint_file': f"constraint/{case}__{boundary}__{core_utilization}__0.txt"
    }
    
    # 记录损失值历史
    loss_history = [initial_data['total_net_length']]
    temperature_history = [initial_temperature]
    iteration_history = [0]
    
    # 获取DEF文件解析，确定总group数量
    def_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{case}__core_utilization__{core_utilization}__boundary__{boundary}__iter__0/{case}.def"
    def_results = parse_def_file(def_path)
    total_groups = len(def_results['instance_groups']) if def_results and 'instance_groups' in def_results else 16  # 默认值为16
    
    # 记录初始迭代到日志
    with open(log_file, "a") as f:
        f.write(f"0,initial,{initial_data['total_net_length']},{initial_data['total_via_count']},{initial_data['total_runtime']},{initial_data['total_net_length']},0,{initial_temperature},True,1\n")
    
    # 当前最佳约束文件
    current_constraint_file = f"constraint/{case}__{boundary}__{core_utilization}__0.txt"
    loss_last = initial_data['total_net_length']
    
    # 初始化温度
    temperature = initial_temperature
    
    # 温度阈值，用于调整修改的group数量
    high_temp_threshold = initial_temperature * high_temp_ratio  # 高温阈值
    low_temp_threshold = initial_temperature * low_temp_ratio    # 低温阈值
    
    # 初始化变动幅度参数
    base_shift_distance = 1.0  # 基础变动幅度
    max_shift_distance = 5.0   # 最大变动幅度
    min_shift_distance = 0.5   # 最小变动幅度
    
    # 初始化每个组的修改次数参数
    max_modifications_per_group = 5  # 最大修改次数
    min_modifications_per_group = 1  # 最小修改次数
    
    # 开始模拟退火算法
    iteration = 1
    while iteration <= max_iterations and temperature >= min_temperature:
        print(f"\n=== 开始迭代 {iteration} ===")
        print(f"当前温度: {temperature}")
        
        # 根据温度动态调整要修改的group数量
        if temperature >= high_temp_threshold:
            # 高温时修改所有group
            num_groups = total_groups
        elif temperature <= low_temp_threshold:
            # 低温时只修改一个group
            num_groups = 1
        else:
            # 中间温度时，线性减少要修改的group数量
            temp_ratio = (temperature - low_temp_threshold) / (high_temp_threshold - low_temp_threshold)
            num_groups = max(1, int(1 + temp_ratio * (total_groups - 1)))
        
        # 根据温度动态调整每个group的修改次数
        if temperature >= high_temp_threshold:
            # 高温时每个组执行最大次数修改
            modifications_per_group = max_modifications_per_group
        elif temperature <= low_temp_threshold:
            # 低温时每个组只执行最小次数修改
            modifications_per_group = min_modifications_per_group
        else:
            # 中间温度时，线性减少修改次数
            temp_ratio = (temperature - low_temp_threshold) / (high_temp_threshold - low_temp_threshold)
            modifications_per_group = max(min_modifications_per_group, 
                                          int(min_modifications_per_group + temp_ratio * (max_modifications_per_group - min_modifications_per_group)))
        
        # 根据温度动态调整变动幅度
        if temperature >= high_temp_threshold:
            # 高温时使用最大变动幅度
            current_shift_distance = max_shift_distance
        elif temperature <= low_temp_threshold:
            # 低温时使用最小变动幅度
            current_shift_distance = min_shift_distance
        else:
            # 中间温度时，线性减少变动幅度
            temp_ratio = (temperature - low_temp_threshold) / (high_temp_threshold - low_temp_ratio)
            current_shift_distance = min_shift_distance + temp_ratio * (max_shift_distance - min_shift_distance)
        
        print(f"本次迭代将修改 {num_groups} 个组，每个组 {modifications_per_group} 次修改，变动幅度为 {current_shift_distance:.2f}")
        
        # 生成新的约束文件
        new_constraint_file = f"constraint/{case}__{boundary}__{core_utilization}__{iteration}.txt"
        modification_type = generate_random_constraint(current_constraint_file, new_constraint_file, None, 
                                                      shift_distance=current_shift_distance, 
                                                      num_groups=num_groups,
                                                      modifications_per_group=modifications_per_group)
        print(f"生成新约束文件: {new_constraint_file} (修改类型: {modification_type}, 修改组数: {num_groups})")
        
        # 运行Innovus
        success = run_innovus(case, boundary, core_utilization, iteration)
        if not success:
            print(f"迭代 {iteration} 运行失败，跳过此迭代")
            # 降低温度
            temperature *= cooling_rate
            iteration += 1
            continue
        
        # 提取结果
        # logv_path = get_logv_path(case, iteration)
        # logv_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{case}__core_utilization__${core_utilization}__boundary__${boundary}__iter__${iteration}/innovus.logv"
        logv_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{case}__core_utilization__{core_utilization}__boundary__{boundary}__iter__{iteration}/innovus.logv"
        current_data = extract_data_from_logv(logv_path)
        
        if current_data['total_net_length'] is None:
            print(f"无法从迭代 {iteration} 中提取总线长，跳过此迭代")
            # 降低温度
            temperature *= cooling_rate
            iteration += 1
            continue
        
        # 计算当前损失
        loss_current = current_data['total_net_length']
        loss_change = loss_current - loss_last
        
        # 决定是否接受新解
        accept = False
        if loss_change <= 0:
            # 如果新解更好，则总是接受
            accept = True
            print(f"发现更好的解: {loss_current} (改进: {-loss_change})")
        else:
            # 如果新解更差，则以一定概率接受
            acceptance_probability = math.exp(-loss_change / temperature)
            random_value = random.random()  # 生成[0,1)之间的随机数
            accept = random_value < acceptance_probability
            print(f"新解更差: {loss_current} (恶化: {loss_change})")
            print(f"接受概率: {acceptance_probability}, 随机值: {random_value}, 接受: {accept}")
        
        # 记录到历史
        loss_history.append(loss_current)
        temperature_history.append(temperature)
        iteration_history.append(iteration)
        
        # 记录到日志，增加记录修改的组数量和每个组的修改类型
        with open(log_file, "a") as f:
            # 将修改类型列表转换为字符串，便于日志记录
            mod_types_str = ','.join(modification_type) if modification_type else "initial"
            f.write(f"{iteration},{mod_types_str},{current_data['total_net_length']},{current_data['total_via_count']},{current_data['total_runtime']},{loss_current},{loss_change},{temperature},{accept},{num_groups},{modifications_per_group},{current_shift_distance:.2f}\n")
        
        if accept:
            # 接受新解
            loss_last = loss_current
            current_constraint_file = new_constraint_file
            
            # 更新最佳解
            if loss_current < best_result['total_net_length']:
                best_result = {
                    'iteration': iteration,
                    'total_net_length': loss_current,
                    'total_via_count': current_data['total_via_count'],
                    'runtime': current_data['total_runtime'],
                    'constraint_file': new_constraint_file
                }
                print(f"更新最佳解: 迭代 {iteration}, 总线长 = {loss_current}")
        else:
            # 不接受新解，但保存迭代器结果用于分析
            print(f"拒绝新解，保持当前最佳解: 总线长 = {loss_last}")
        
        # 降低温度
        temperature *= cooling_rate
        iteration += 1
    
    # 模拟退火结束
    print("\n\n===== 模拟退火算法结束 =====")
    print(f"最佳解: 迭代 {best_result['iteration']}")
    print(f"总线长: {best_result['total_net_length']}")
    print(f"总过孔数: {best_result['total_via_count']}")
    print(f"运行时间: {best_result['runtime']}")
    print(f"约束文件: {best_result['constraint_file']}")
    
    # 绘制损失函数的折线图
    plt.figure(figsize=(12, 6))
    plt.plot(iteration_history, loss_history, 'b-', label='Total Net Length')
    plt.title('Simulated Annealing Optimization')
    plt.xlabel('Iteration')
    plt.ylabel('Total Net Length')
    plt.grid(True)
    plt.legend()
    
    # 添加温度曲线在同一图中（使用第二个Y轴）
    ax2 = plt.twinx()
    ax2.plot(iteration_history, temperature_history, 'r--', label='Temperature')
    ax2.set_ylabel('Temperature', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    
    # 标记最佳解
    plt.axvline(x=best_result['iteration'], color='g', linestyle='--')
    plt.text(best_result['iteration'], best_result['total_net_length'], 
             f"Best: {best_result['total_net_length']:.2f}", 
             ha='right', va='bottom')
    
    # 保存图片
    plot_file = f"{current_time}__{case}__{boundary}__{core_utilization}_plot.png"
    plt.savefig(plot_file)
    plt.close()
    
    print(f"损失函数图保存为: {plot_file}")
    print(f"日志文件保存为: {log_file}")
    
    return best_result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Innovus设计空间探索工具')
    parser.add_argument('-c', '--case', default='PE_array', help='案例名称')
    parser.add_argument('-b', '--boundary', default='Boundary_Areacoverage_250324_phase1_test3', help='边界名称')
    parser.add_argument('-u', '--utilization', default='70', help='核心利用率')
    parser.add_argument('-i', '--iterations', type=int, default=100, help='最大迭代次数')
    parser.add_argument('-t', '--temperature', type=float, default=1.0, help='初始温度')
    parser.add_argument('-r', '--rate', type=float, default=0.99, help='冷却率')
    parser.add_argument('-m', '--min-temp', type=float, default=0.01, help='最小温度')
    parser.add_argument('-d', '--def-file', help='要分析的DEF文件路径')
    parser.add_argument('--high-temp-ratio', type=float, default=0.7, help='高温阈值比例（相对于初始温度）')
    parser.add_argument('--low-temp-ratio', type=float, default=0.3, help='低温阈值比例（相对于初始温度）')
    parser.add_argument('--max-modifications', type=int, default=5, help='每个组的最大修改次数')
    parser.add_argument('--min-modifications', type=int, default=1, help='每个组的最小修改次数') 
    parser.add_argument('--max-shift', type=float, default=3.0, help='最大移动距离')
    parser.add_argument('--min-shift', type=float, default=0.5, help='最小移动距离')
    
    args = parser.parse_args()
    
    if args.def_file:
        # 分析DEF文件
        analyze_def_file(args.def_file)
    else:
        # 执行模拟退火算法
        best_result = simulated_annealing(
            args.case, 
            args.boundary, 
            args.utilization, 
            max_iterations=args.iterations,
            initial_temperature=args.temperature,
            cooling_rate=args.rate,
            min_temperature=args.min_temp,
            high_temp_ratio=args.high_temp_ratio,
            low_temp_ratio=args.low_temp_ratio
        )
        
        if best_result:
            print("\n最佳结果:")
            for key, value in best_result.items():
                print(f"{key}: {value}")



