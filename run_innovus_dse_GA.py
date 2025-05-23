import os
import sys
import argparse
import subprocess
import time
import shutil
import random
import math
import matplotlib.pyplot as plt
import numpy as np
import datetime
import copy
from decimal import Decimal
# 导入DEF解析器模块
from def_parser import parse_def_file
# 导入提取路由报告数据的模块
from extract_route_report import extract_data_from_logv
# 导入约束修改模块
from random_constraint_modifier import modify_constraint_file

class Individual:
    """表示遗传算法中的一个个体"""
    def __init__(self, case, boundary, core_utilization, iteration, mod_types=None, num_groups=None):
        self.case = case
        self.boundary = boundary
        self.core_utilization = core_utilization
        self.iteration = iteration
        self.constraint_file = f"constraint/{case}__{boundary}__{core_utilization}__{iteration}.txt"
        self.fitness = float('inf')  # 适应度（总线长，越小越好）
        self.total_net_length = None
        self.total_via_count = None
        self.runtime = None
        self.mod_types = mod_types if mod_types else []  # 应用的修改类型
        self.num_groups = num_groups  # 修改的组数
        self.evaluated = False  # 是否已评估
        self.parent_boundaries = []  # 记录父代的boundary信息
        self.origin = "random"  # 个体来源：original(原始)、crossover(交叉)、mutation(变异)、random(随机)

    def evaluate(self, verbose=True):
        """
        评估个体的适应度
        
        返回:
            bool: 是否成功评估
        """
        if verbose:
            print(f"评估个体 iteration={self.iteration}")
        
        # 运行Innovus
        success = run_innovus(self.case, self.boundary, self.core_utilization, self.iteration)
        if not success:
            print(f"个体 {self.iteration} 运行失败")
            return False
        
        # 提取结果
        logv_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{self.case}__core_utilization__{self.core_utilization}__boundary__{self.boundary}__iter__{self.iteration}/innovus.logv"
        data = extract_data_from_logv(logv_path)
        
        if data['total_net_length'] is None:
            print(f"无法从迭代 {self.iteration} 中提取总线长")
            return False
        
        # 更新适应度和相关指标
        self.total_net_length = data['total_net_length']
        self.total_via_count = data['total_via_count']
        self.runtime = data['total_runtime']
        self.fitness = data['total_net_length']  # 使用总线长作为适应度
        self.evaluated = True
        
        if verbose:
            print(f"个体 {self.iteration} 评估结果: 适应度={self.fitness}, 总线长={self.total_net_length}")
        
        return True

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

def initialize_population(case, boundaries, core_utilization, population_size, def_results, base_iteration=1):
    """
    初始化种群，使用多个boundary文件作为初始基因池
    
    参数:
        case: 案例名称
        boundaries: 边界名称列表
        core_utilization: 核心利用率
        population_size: 种群大小
        def_results: DEF解析结果，用于确定组数
        base_iteration: 迭代计数起始值
    
    返回:
        list: 个体列表
    """
    print("初始化种群...")
    
    # 确定总group数量
    total_groups = len(def_results['instance_groups']) if def_results and 'instance_groups' in def_results else 16
    
    # 可用的修改类型
    mod_types = [
        "type_parameter",    # 修改-type参数
        "edge_shift",        # 边缘移动
        "add_boundary",      # 添加边界矩形
        "remove_boundary",   # 移除边界矩形
        "move_entire"        # 整体移动
    ]
    
    population = []
    
    # 首先添加每个boundary的原始约束个体
    for i, boundary in enumerate(boundaries):
        individual = Individual(case, boundary, core_utilization, i)
        base_constraint_file = f"constraint/{case}__{boundary}__{core_utilization}__0.txt"
        
        # 确保原始约束文件存在
        if not os.path.exists(base_constraint_file):
            print(f"警告: 原始约束文件 {base_constraint_file} 不存在，将跳过此boundary")
            continue
            
        individual.constraint_file = base_constraint_file
        individual.origin = "original"
        individual.mod_types = ["initial"]
        individual.num_groups = 0
        population.append(individual)
    
    # 如果初始边界个体数量小于种群大小，生成剩余个体
    remaining_count = population_size - len(population)
    if remaining_count > 0:
        print(f"生成剩余 {remaining_count} 个个体以达到种群大小 {population_size}...")
        
        # 生成方法：1/3使用交叉，1/3使用变异，1/3使用随机生成
        crossover_count = remaining_count // 3
        mutation_count = remaining_count // 3
        random_count = remaining_count - crossover_count - mutation_count
        
        global_iteration = len(boundaries)  # 迭代号从boundary数量开始
        
        # 1. 使用交叉生成一部分个体
        if len(population) >= 2 and crossover_count > 0:
            for i in range(crossover_count):
                # 随机选择两个不同的父代
                parent1, parent2 = random.sample(population, 2)
                
                # 选择子代使用哪个boundary (随机选择一个父代的boundary)
                child_boundary = random.choice([parent1.boundary, parent2.boundary])
                
                # 创建子代
                global_iteration += 1
                child = Individual(case, child_boundary, core_utilization, global_iteration)
                child.origin = "crossover"
                child.parent_boundaries = [parent1.boundary, parent2.boundary]
                
                # 生成子代约束文件 (简单交叉：使用父代1的约束文件)
                parent1_file = parent1.constraint_file
                child_file = child.constraint_file
                
                # 从两个父代约束文件中进行交叉
                crossover_modifications = perform_crossover(parent1_file, parent2.constraint_file, child_file, total_groups)
                
                child.mod_types = crossover_modifications
                child.num_groups = len(crossover_modifications) if crossover_modifications else 0
                population.append(child)
        
        # 2. 使用变异生成一部分个体
        if len(population) >= 1 and mutation_count > 0:
            for i in range(mutation_count):
                # 随机选择一个父代
                parent = random.choice(population)
                
                # 创建变异个体 (使用相同的boundary)
                global_iteration += 1
                mutant = Individual(case, parent.boundary, core_utilization, global_iteration)
                mutant.origin = "mutation"
                mutant.parent_boundaries = [parent.boundary]
                
                # 随机确定要修改的组数
                num_groups = random.randint(1, max(1, total_groups // 3))
                
                # 生成随机约束文件
                new_constraint_file = mutant.constraint_file
                modifications = generate_random_constraint(parent.constraint_file, new_constraint_file, None, num_groups=num_groups)
                
                mutant.mod_types = modifications
                mutant.num_groups = num_groups
                population.append(mutant)
        
        # 3. 随机生成剩余个体
        for i in range(random_count):
            # 随机选择一个boundary
            boundary = random.choice(boundaries)
            
            global_iteration += 1
            individual = Individual(case, boundary, core_utilization, global_iteration)
            individual.origin = "random"
            
            # 获取该boundary的基础约束文件
            base_constraint_file = f"constraint/{case}__{boundary}__{core_utilization}__0.txt"
            
            # 随机确定要修改的组数
            num_groups = random.randint(1, max(1, total_groups // 2))
            
            # 生成随机约束文件
            new_constraint_file = individual.constraint_file
            modifications = generate_random_constraint(base_constraint_file, new_constraint_file, None, num_groups=num_groups)
            
            individual.mod_types = modifications
            individual.num_groups = num_groups
            population.append(individual)
    
    return population

def perform_crossover(parent1_file, parent2_file, child_file, total_groups):
    """
    执行约束文件的交叉操作
    
    参数:
        parent1_file: 父代1的约束文件
        parent2_file: 父代2的约束文件
        child_file: 子代的约束文件
        total_groups: 总组数
    
    返回:
        list: 交叉使用的修改类型
    """
    # 选择交叉点
    crossover_point = random.randint(1, total_groups - 1)
    
    # 读取两个父代约束文件内容
    with open(parent1_file, 'r') as f1:
        parent1_lines = f1.readlines()
    
    with open(parent2_file, 'r') as f2:
        parent2_lines = f2.readlines()
    
    # 找出create_group行的索引
    p1_groups = [(i, line) for i, line in enumerate(parent1_lines) if "create_group" in line]
    p2_groups = [(i, line) for i, line in enumerate(parent2_lines) if "create_group" in line]
    
    # 如果任一父代没有足够的组，则直接复制父代1的文件
    if len(p1_groups) < crossover_point or len(p2_groups) < total_groups - crossover_point:
        shutil.copy(parent1_file, child_file)
        return ["copy_parent1"]
    
    # 创建子代约束文件内容
    child_lines = parent1_lines.copy()
    
    # 从父代2复制剩余的组
    modifications = []
    for i in range(crossover_point, min(total_groups, len(p2_groups))):
        if i < len(p1_groups):
            child_lines[p1_groups[i][0]] = p2_groups[i][1]
            modifications.append(f"crossover_group_{i}")
    
    # 写入子代约束文件
    with open(child_file, 'w') as f:
        f.writelines(child_lines)
    
    return modifications

def crossover(parent1, parent2, case, boundary, core_utilization, iteration, def_results):
    """
    执行约束交叉操作
    
    参数:
        parent1, parent2: 父代个体
        case, boundary, core_utilization: 案例参数
        iteration: 新个体的迭代号
        def_results: DEF解析结果
    
    返回:
        Individual: 交叉后的子代个体
    """
    # 随机选择一个父代的boundary
    child_boundary = random.choice([parent1.boundary, parent2.boundary])
    
    # 创建新个体
    child = Individual(case, child_boundary, core_utilization, iteration)
    child.origin = "crossover"
    child.parent_boundaries = [parent1.boundary, parent2.boundary]
    
    # 确定总group数量
    total_groups = len(def_results['instance_groups']) if def_results and 'instance_groups' in def_results else 16
    
    # 执行交叉操作
    modifications = perform_crossover(parent1.constraint_file, parent2.constraint_file, child.constraint_file, total_groups)
    
    child.mod_types = modifications
    child.num_groups = len(modifications) if modifications else 0
    
    return child

def mutate(individual, case, boundary, core_utilization, iteration, mutation_rate=0.2, def_results=None, 
          current_generation=1, max_generations=50, high_gen_ratio=0.3, low_gen_ratio=0.7):
    """
    对个体进行变异
    
    参数:
        individual: 要变异的个体
        case, boundary, core_utilization: 案例参数
        iteration: 新个体的迭代号
        mutation_rate: 变异概率
        def_results: DEF解析结果
        current_generation: 当前代数
        max_generations: 最大代数
        high_gen_ratio: 高代数比例 (相当于低温阶段)
        low_gen_ratio: 低代数比例 (相当于高温阶段)
    
    返回:
        Individual: 变异后的个体
    """
    # 确定是否执行变异
    if random.random() > mutation_rate:
        return individual
    
    # 创建新个体，使用相同的boundary
    mutant = Individual(case, individual.boundary, core_utilization, iteration)
    mutant.origin = "mutation"
    mutant.parent_boundaries = [individual.boundary]
    
    # 确定总group数量
    total_groups = len(def_results['instance_groups']) if def_results and 'instance_groups' in def_results else 16
    
    # 计算代数比例 (0-1之间，0表示第一代，1表示最后一代)
    generation_ratio = (current_generation - 1) / max(1, max_generations - 1)
    
    # 根据代数动态调整要修改的组数
    if generation_ratio <= low_gen_ratio:  # 早期阶段 (相当于高温)
        # 早期阶段修改更多组
        max_group_number = total_groups
        min_group_number = max(1, total_groups // 3)
        group_range = max_group_number - min_group_number
        # 随着代数增加线性减少要修改的组数
        early_ratio = generation_ratio / low_gen_ratio
        num_groups = max(1, int(max_group_number - early_ratio * group_range))
    elif generation_ratio >= high_gen_ratio:  # 后期阶段 (相当于低温)
        # 后期阶段只修改少量组
        num_groups = 1
    else:  # 中期阶段
        # 中期阶段修改的组数在1到总组数的1/3之间线性变化
        mid_ratio = (generation_ratio - low_gen_ratio) / (high_gen_ratio - low_gen_ratio)
        num_groups = max(1, int(total_groups // 3 * (1 - mid_ratio) + 1 * mid_ratio))
    
    # 动态调整每个组的修改次数
    if generation_ratio <= low_gen_ratio:  # 早期阶段
        # 早期阶段每个组执行更多次修改
        modifications_per_group = 5  # 最大修改次数
    elif generation_ratio >= high_gen_ratio:  # 后期阶段
        # 后期阶段每个组只执行一次修改
        modifications_per_group = 1  # 最小修改次数
    else:  # 中期阶段
        # 中期阶段修改次数线性减少
        mid_ratio = (generation_ratio - low_gen_ratio) / (high_gen_ratio - low_gen_ratio)
        modifications_per_group = max(1, int(5 - 4 * mid_ratio))
    
    # 动态调整变动幅度
    if generation_ratio <= low_gen_ratio:  # 早期阶段
        # 早期阶段使用较大的变动幅度
        max_shift = 5.0
        min_shift = 1.5
        # 随着代数增加线性减少变动幅度
        early_ratio = generation_ratio / low_gen_ratio
        shift_distance = max_shift - early_ratio * (max_shift - min_shift)
    elif generation_ratio >= high_gen_ratio:  # 后期阶段
        # 后期阶段使用较小的变动幅度
        shift_distance = 0.5
    else:  # 中期阶段
        # 中期阶段变动幅度线性减少
        mid_ratio = (generation_ratio - low_gen_ratio) / (high_gen_ratio - low_gen_ratio)
        shift_distance = 1.5 - mid_ratio
    
    print(f"变异设置: 代数={current_generation}/{max_generations}, 修改组数={num_groups}, 每组修改次数={modifications_per_group}, 变动幅度={shift_distance:.2f}")
    
    # 生成随机约束文件
    new_constraint_file = mutant.constraint_file
    modifications = generate_random_constraint(individual.constraint_file, new_constraint_file, None, 
                                             shift_distance=shift_distance, 
                                             num_groups=num_groups,
                                             modifications_per_group=modifications_per_group)
    
    mutant.mod_types = modifications
    mutant.num_groups = num_groups
    
    return mutant

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
    # 调用constraint修改函数
    modification_types_used = modify_constraint_file(input_file, output_file, modification_type, 
                                                   shift_distance, num_groups, modifications_per_group)
    
    return modification_types_used

def genetic_algorithm(case, boundaries, core_utilization, population_size=20, max_generations=50, 
                     tournament_size=3, crossover_rate=0.8, mutation_rate=0.2, elitism=2):
    """
    执行遗传算法
    
    参数:
        case: 案例名称
        boundaries: 边界名称列表
        core_utilization: 核心利用率
        population_size: 种群大小
        max_generations: 最大代数
        tournament_size: 锦标赛选择的大小
        crossover_rate: 交叉概率
        mutation_rate: 变异概率
        elitism: 精英个体数量
        
    返回:
        dict: 包含最佳结果的字典
    """
    # 获取当前时间作为日志文件名的一部分
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 使用第一个边界和总边界数量来生成文件名，避免文件名过长
    primary_boundary = boundaries[0]
    boundary_count = len(boundaries)
    log_file = f"{current_time}__{case}__{primary_boundary}__{core_utilization}__GA.txt"
    
    # 创建日志文件并写入头部信息
    with open(log_file, "w") as f:
        f.write(f"# 遗传算法优化日志\n")
        f.write(f"# 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 案例: {case}\n")
        f.write(f"# 主参考边界: {primary_boundary}\n")
        f.write(f"# 所有边界列表: {', '.join(boundaries)}\n")
        f.write(f"# 核心利用率: {core_utilization}\n")
        f.write(f"# 种群大小: {population_size}\n")
        f.write(f"# 最大代数: {max_generations}\n")
        f.write(f"# 锦标赛大小: {tournament_size}\n")
        f.write(f"# 交叉概率: {crossover_rate}\n")
        f.write(f"# 变异概率: {mutation_rate}\n")
        f.write(f"# 精英数量: {elitism}\n")
        f.write("\n")
        f.write("generation,individual,boundary,origin,parent_boundaries,modification_types,total_net_length,total_via_count,runtime,fitness,num_groups\n")
    
    # 为每个boundary执行初始迭代（参考设计）
    all_def_results = {}
    reference_individuals = []
    
    for boundary in boundaries:
        print(f"执行边界 {boundary} 的初始迭代 (iteration 0)...")
        success = run_innovus(case, boundary, core_utilization, 0)
        if not success:
            print(f"边界 {boundary} 的初始迭代失败，跳过此边界")
            continue
        
        # 提取初始结果
        logv_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{case}__core_utilization__{core_utilization}__boundary__{boundary}__iter__0/innovus.logv"
        initial_data = extract_data_from_logv(logv_path)
        
        if initial_data['total_net_length'] is None:
            print(f"无法从边界 {boundary} 的初始迭代中提取总线长，跳过此边界")
            continue
        
        # 获取DEF文件解析，确定总group数量
        def_path = f"/mnt/hgfs/vm_share/eda/innovus_output_dse/case__{case}__core_utilization__{core_utilization}__boundary__{boundary}__iter__0/{case}.def"
        def_results = parse_def_file(def_path)
        all_def_results[boundary] = def_results
        
        # 初始化参考个体
        reference_individual = Individual(case, boundary, core_utilization, 0)
        reference_individual.total_net_length = initial_data['total_net_length']
        reference_individual.total_via_count = initial_data['total_via_count']
        reference_individual.runtime = initial_data['total_runtime']
        reference_individual.fitness = initial_data['total_net_length']
        reference_individual.evaluated = True
        reference_individual.mod_types = ["initial"]
        reference_individual.num_groups = 0
        reference_individual.origin = "original"
        
        reference_individuals.append(reference_individual)
        
        # 记录初始迭代到日志
        with open(log_file, "a") as f:
            parent_boundaries_str = ""
            mod_types_str = "initial"
            f.write(f"0,0,{boundary},original,{parent_boundaries_str},{mod_types_str},{initial_data['total_net_length']},{initial_data['total_via_count']},{initial_data['total_runtime']},{initial_data['total_net_length']},0\n")
    
    if not reference_individuals:
        print("所有边界的初始迭代都失败，退出程序")
        return None
    
    # 使用第一个成功的boundary的def_results作为参考
    primary_def_results = next(iter(all_def_results.values()))
    
    # 初始化种群
    base_iteration = len(boundaries)  # 个体迭代号从boundary数量开始
    population = initialize_population(case, boundaries, core_utilization, population_size, primary_def_results, base_iteration)
    
    # 用参考个体替换种群中的前几个个体
    for i, ref_ind in enumerate(reference_individuals):
        if i < len(population):
            population[i] = ref_ind
    
    # 评估初始种群
    eval_count = len(reference_individuals)  # 已经评估了参考个体
    for individual in population:
        if not individual.evaluated:
            success = individual.evaluate()
            if success:
                eval_count += 1
                # 记录到日志
                with open(log_file, "a") as f:
                    mod_types_str = ','.join(individual.mod_types) if individual.mod_types else "unknown"
                    parent_boundaries_str = ','.join(individual.parent_boundaries) if individual.parent_boundaries else ""
                    f.write(f"0,{individual.iteration},{individual.boundary},{individual.origin},{parent_boundaries_str},{mod_types_str},{individual.total_net_length},{individual.total_via_count},{individual.runtime},{individual.fitness},{individual.num_groups}\n")
    
    # 初始化最佳个体
    best_individual = min(population, key=lambda ind: ind.fitness if ind.evaluated else float('inf'))
    
    # 如果最佳个体没有被评估，则使用第一个参考个体
    if not best_individual.evaluated:
        best_individual = reference_individuals[0]
    
    # 记录每一代的最佳适应度
    best_fitness_history = [best_individual.fitness]
    avg_fitness_history = [sum(ind.fitness for ind in population if ind.evaluated) / max(1, sum(1 for ind in population if ind.evaluated))]
    generation_history = [0]
    
    # 开始遗传算法迭代
    generation = 1
    global_iteration = max([ind.iteration for ind in population]) + 1  # 全局迭代计数器
    
    # 设置代数比例的高低阈值，用于控制变异强度
    high_gen_ratio = 0.7  # 高代数比例阈值 (70%的代数后进入精细优化阶段)
    low_gen_ratio = 0.3   # 低代数比例阈值 (30%的代数前为大幅探索阶段)
    
    while generation <= max_generations:
        print(f"\n=== 开始第 {generation} 代 ===")
        
        # 从当前种群中选择精英个体
        sorted_population = sorted([ind for ind in population if ind.evaluated], key=lambda ind: ind.fitness)
        elites = sorted_population[:min(elitism, len(sorted_population))]
        
        # 创建新一代种群
        new_population = []
        
        # 添加精英个体
        new_population.extend(elites)
        
        # 通过选择、交叉和变异创建新个体
        while len(new_population) < population_size:
            # 选择父代
            parent1 = select_parents(population, tournament_size)
            parent2 = select_parents(population, tournament_size)
            
            # 如果父代相同，尝试重新选择
            attempt = 0
            while parent1 == parent2 and attempt < 3:
                parent2 = select_parents(population, tournament_size)
                attempt += 1
            
            # 决定是否执行交叉
            if random.random() < crossover_rate and parent1 != parent2:
                # 交叉
                global_iteration += 1
                child = crossover(parent1, parent2, case, parent1.boundary, core_utilization, global_iteration, primary_def_results)
                # 变异 (传递当前代数和最大代数)
                global_iteration += 1
                child = mutate(child, case, child.boundary, core_utilization, global_iteration, mutation_rate, 
                              primary_def_results, current_generation=generation, max_generations=max_generations,
                              high_gen_ratio=high_gen_ratio, low_gen_ratio=low_gen_ratio)
            else:
                # 只进行变异 (传递当前代数和最大代数)
                global_iteration += 1
                child = mutate(parent1, case, parent1.boundary, core_utilization, global_iteration, mutation_rate, 
                              primary_def_results, current_generation=generation, max_generations=max_generations,
                              high_gen_ratio=high_gen_ratio, low_gen_ratio=low_gen_ratio)
            
            new_population.append(child)
        
        # 确保新种群大小不超过指定大小
        new_population = new_population[:population_size]
        
        # 评估新种群中未评估的个体
        for individual in new_population:
            if not individual.evaluated:
                success = individual.evaluate()
                if success:
                    # 记录到日志
                    with open(log_file, "a") as f:
                        mod_types_str = ','.join(individual.mod_types) if individual.mod_types else "unknown"
                        parent_boundaries_str = ','.join(individual.parent_boundaries) if individual.parent_boundaries else ""
                        f.write(f"{generation},{individual.iteration},{individual.boundary},{individual.origin},{parent_boundaries_str},{mod_types_str},{individual.total_net_length},{individual.total_via_count},{individual.runtime},{individual.fitness},{individual.num_groups}\n")
        
        # 更新种群
        population = new_population
        
        # 找出当前代的最佳个体
        generation_best = min([ind for ind in population if ind.evaluated], key=lambda ind: ind.fitness, default=None)
        
        # 更新全局最佳个体
        if generation_best and (not best_individual.evaluated or generation_best.fitness < best_individual.fitness):
            best_individual = generation_best
            print(f"发现新的最佳个体: iteration={best_individual.iteration}, boundary={best_individual.boundary}, fitness={best_individual.fitness}")
        
        # 记录历史
        best_fitness_history.append(best_individual.fitness)
        evaluated_individuals = [ind for ind in population if ind.evaluated]
        avg_fitness = sum(ind.fitness for ind in evaluated_individuals) / max(1, len(evaluated_individuals))
        avg_fitness_history.append(avg_fitness)
        generation_history.append(generation)
        
        print(f"第 {generation} 代完成")
        print(f"当前最佳适应度: {best_individual.fitness} (boundary: {best_individual.boundary})")
        print(f"平均适应度: {avg_fitness}")
        
        generation += 1
    
    # 遗传算法结束
    print("\n\n===== 遗传算法结束 =====")
    print(f"最佳个体: iteration={best_individual.iteration}, boundary={best_individual.boundary}")
    print(f"适应度(总线长): {best_individual.fitness}")
    print(f"总过孔数: {best_individual.total_via_count}")
    print(f"运行时间: {best_individual.runtime}")
    print(f"约束文件: {best_individual.constraint_file}")
    
    # 绘制适应度变化图
    plt.figure(figsize=(12, 6))
    plt.plot(generation_history, best_fitness_history, 'b-', label='Best Fitness')
    plt.plot(generation_history, avg_fitness_history, 'r--', label='Average Fitness')
    plt.title('Genetic Algorithm Optimization')
    plt.xlabel('Generation')
    plt.ylabel('Fitness (Total Net Length)')
    plt.legend()
    plt.grid(True)
    
    # 保存图片时也使用相同的命名方式
    plot_file = f"{current_time}__{case}__{primary_boundary}__{core_utilization}__GA_plot.png"
    plt.savefig(plot_file)
    plt.close()
    
    print(f"适应度变化图保存为: {plot_file}")
    print(f"日志文件保存为: {log_file}")
    
    # 构建结果字典
    best_result = {
        'iteration': best_individual.iteration,
        'boundary': best_individual.boundary,
        'total_net_length': best_individual.fitness,
        'total_via_count': best_individual.total_via_count,
        'runtime': best_individual.runtime,
        'constraint_file': best_individual.constraint_file
    }
    
    return best_result

def select_parents(population, tournament_size=3):
    """
    使用锦标赛选择法选择父代
    
    参数:
        population: 种群
        tournament_size: 锦标赛大小
    
    返回:
        Individual: 选中的个体
    """
    # 随机选择tournament_size个个体
    tournament = random.sample(population, min(tournament_size, len(population)))
    
    # 选择适应度最好（最小）的个体
    return min(tournament, key=lambda ind: ind.fitness if ind.evaluated else float('inf'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='基于遗传算法的Innovus设计空间探索工具')
    parser.add_argument('-c', '--case', default='PE_array', help='案例名称')
    parser.add_argument('-b', '--boundary', default='Boundary_Areacoverage_250324_phase1_test3', 
                        help='边界名称，多个边界以逗号分隔，如"boundary1,boundary2,boundary3"')
    parser.add_argument('-u', '--utilization', default='70', help='核心利用率')
    parser.add_argument('-p', '--population', type=int, default=20, help='种群大小')
    parser.add_argument('-g', '--generations', type=int, default=50, help='最大代数')
    parser.add_argument('-t', '--tournament', type=int, default=3, help='锦标赛大小')
    parser.add_argument('-x', '--crossover', type=float, default=0.8, help='交叉概率')
    parser.add_argument('-m', '--mutation', type=float, default=0.2, help='变异概率')
    parser.add_argument('-e', '--elitism', type=int, default=2, help='精英个体数量')
    parser.add_argument('-d', '--def-file', help='要分析的DEF文件路径')
    parser.add_argument('--high-gen-ratio', type=float, default=0.7, help='高代数比例阈值，用于控制变异强度')
    parser.add_argument('--low-gen-ratio', type=float, default=0.3, help='低代数比例阈值，用于控制变异强度')
    
    args = parser.parse_args()
    
    if args.def_file:
        # 分析DEF文件
        from def_parser import analyze_def_file
        analyze_def_file(args.def_file)
    else:
        # 解析多个boundary
        boundaries = [b.strip() for b in args.boundary.split(',')]
        print(f"使用以下多个边界文件: {boundaries}")
        
        # 执行遗传算法
        best_result = genetic_algorithm(
            args.case,
            boundaries,
            args.utilization,
            population_size=args.population,
            max_generations=args.generations,
            tournament_size=args.tournament,
            crossover_rate=args.crossover,
            mutation_rate=args.mutation,
            elitism=args.elitism
        )
        
        if best_result:
            print("\n最佳结果:")
            for key, value in best_result.items():
                print(f"{key}: {value}")

'''

python run_innovus_dse_GA.py -c PE_array -b "Boundary_Areacoverage_250324_phase1_test3,Boundary_Badoverlap_i100,Boundary_BadSituation_OutofOrderComplete_i493,Boundary_PinAffectCell_phase3best_test2,Boundary_PinAffectCell_phase3initial_test2"


'''