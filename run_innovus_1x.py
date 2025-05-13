#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
from decimal import Decimal

# 定义参数列表
core_utilizations = [60, 70, 80, 90]
cases = ["PE_array"]  # 可以根据需要添加 "fft8"
types_main = ["guide", "region", "fence"]
modes = ["inside", "outside", "outside_extend", "midside", "jigsaw", "rectangle"]
boundaries = [
    "Boundary_Areacoverage_250324_phase1_test1", "Boundary_Areacoverage_250324_phase1_test2", 
    "Boundary_Areacoverage_250324_phase1_test3", "Boundary_Badoverlap_i0", 
    "Boundary_Badoverlap_i100", "Boundary_Badoverlap_i250", 
    "Boundary_BadSituation_OutofOrderComplete_i493", 
    "Boundary_BadSituation_OutofOrderSlight-overlap_i499", 
    "Boundary_BadSituation_overlap_i150", 
    "Boundary_PinAffectCell_phase3best_test1", "Boundary_PinAffectCell_phase3best_test2", 
    "Boundary_PinAffectCell_phase3initial_test1", "Boundary_PinAffectCell_phase3initial_test2"
]

def run_command(cmd):
    """执行shell命令并返回输出"""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout

def create_tcl_script(case, type_name, mode, boundary, core_utilization, base_path, tar_path, core_utilization_str):
    """创建TCL脚本文件"""
    tcl_file = f"{case}_{type_name}_{mode}_temp_cmd.tcl"
    
    # 为类型和模式组合定制group_information部分
    group_info = ""
    if type_name not in ["no_type"]:
        group_info = f"$(cat ./output/{case}.{type_name}.{mode}.{boundary}_{core_utilization}.txt)"
    
    tcl_content = f'''
set SRCPATH {base_path}
set TARPATH {tar_path}
set DESIGN {case}


setMultiCpuUsage -localCpu max
set_global _enable_mmmc_by_default_flow      $CTE::mmmc_default
suppressMessage ENCEXT-2799
win
set init_lef_file {{/mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/techlef_misc/asap7_tech_1x_201209.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_L_1x_220121a.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_R_1x_220121a.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_SL_1x_220121a.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_SRAM_1x_220121a.lef}}
set init_verilog ${{SRCPATH}}/${{DESIGN}}.mapped.v
set init_mmmc_file /mnt/hgfs/vm_share/eda/lib/asap_project/asap.view
init_design

setAnalysisMode -reset
setAnalysisMode -analysisType onChipVariation -cppr both

# defIn /mnt/hgfs/vm_share/tools/innovus_project_pre_generation/PE_array.floorplan.{core_utilization}.def

getIoFlowFlag
setIoFlowFlag 0
floorPlan -site asap7sc7p5t -r 1 {core_utilization_str} 0.0 0.0 0.0 0.0
uiSetTool select
getIoFlowFlag
fit


# group information here
{group_info}

# Run placement
setRouteMode -earlyGlobalHonorMsvRouteConstraint false -earlyGlobalRoutePartitionPinGuide true
setEndCapMode -reset
setEndCapMode -boundary_tap false
setNanoRouteMode -quiet -droutePostRouteSpreadWire 1
setNanoRouteMode -quiet -timingEngine {{}}
setUsefulSkewMode -maxSkew false -noBoundary false -useCells {{HB4xp67_ASAP7_75t_R HB3xp67_ASAP7_75t_R HB2xp67_ASAP7_75t_R HB1xp67_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx3_ASAP7_75t_R BUFx2_ASAP7_75t_R BUFx24_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx12_ASAP7_75t_R BUFx10_ASAP7_75t_R INVxp67_ASAP7_75t_R INVxp33_ASAP7_75t_R INVx8_ASAP7_75t_R INVx6_ASAP7_75t_R INVx5_ASAP7_75t_R INVx4_ASAP7_75t_R INVx3_ASAP7_75t_R INVx2_ASAP7_75t_R INVx1_ASAP7_75t_R INVx13_ASAP7_75t_R INVx11_ASAP7_75t_R CKINVDCx9p33_ASAP7_75t_R CKINVDCx8_ASAP7_75t_R CKINVDCx6p67_ASAP7_75t_R CKINVDCx5p33_ASAP7_75t_R CKINVDCx20_ASAP7_75t_R CKINVDCx16_ASAP7_75t_R CKINVDCx14_ASAP7_75t_R CKINVDCx12_ASAP7_75t_R CKINVDCx11_ASAP7_75t_R CKINVDCx10_ASAP7_75t_R}} -maxAllowedDelay 1
setPlaceMode -reset
setPlaceMode -congEffort auto -timingDriven 1 -clkGateAware 1 -powerDriven 0 -ignoreScan 1 -reorderScan 1 -ignoreSpare 0 -placeIOPins 0 -moduleAwareSpare 0 -preserveRouting 0 -rmAffectedRouting 0 -checkRoute 0 -swapEEQ 0
setPlaceMode -fp false
setMultiCpuUsage -localCpu max
place_opt_design
report_route -summary
saveNetlist ${{TARPATH}}/${{DESIGN}}.postPlace.mapped.v
defOut -floorplan -netlist -routing ${{TARPATH}}/${{DESIGN}}.postPlace.def
# place_design


# Routing
setNanoRouteMode -quiet -timingEngine {{}}
setNanoRouteMode -quiet -routeSelectedNetOnly 0
setNanoRouteMode -quiet -routeTopRoutingLayer default
setNanoRouteMode -quiet -routeBottomRoutingLayer default
setNanoRouteMode -quiet -drouteEndIteration default
setNanoRouteMode -quiet -routeWithTimingDriven false
setNanoRouteMode -quiet -routeWithSiDriven false
routeDesign -globalDetail
report_route -summary

optDesign -postRoute
report_route -summary

############# extract spef #############
reset_parasitics
extractRC
rcOut -spef PE_array_no_constraint.spef
############# extract spef #############

# saveDesign ${{TARPATH}}/${{DESIGN}}.routed.enc

set dbgLefDefOutVersion 5.8
global dbgLefDefOutVersion
set dbgLefDefOutVersion 5.8
saveNetlist ${{TARPATH}}/${{DESIGN}}.postRoute.mapped.v
defOut -floorplan -netlist -routing ${{TARPATH}}/${{DESIGN}}.postRoute.def





timeDesign -postRoute -pathReports -drvReports -slackReports -numPaths 50 -prefix ${{DESIGN}}_postRoute -outDir ${{TARPATH}}/${{DESIGN}}_timingReports_postRoute


exit
'''
    
    with open(tcl_file, 'w') as f:
        f.write(tcl_content)
    
    os.chmod(tcl_file, 0o777)
    return tcl_file

def main():
    # 主循环
    for core_utilization in core_utilizations:
        for case in cases:
            # 主循环 - 正常类型
            for type_name in types_main:
                for mode in modes:
                    for boundary in boundaries:
                        print(f'=================={case}_{type_name}_{mode}_{boundary}')
                        
                        # 更新asap.view文件中的SDC路径
                        cmd = f"sed -i \"s|create_constraint_mode -name CONSTRAINTS -sdc_files {{.*}}|create_constraint_mode -name CONSTRAINTS -sdc_files {{/mnt/hgfs/vm_share/eda/synproj_asap/project_{case}/{case}/results/{case}.mapped.sdc}}|\" /mnt/hgfs/vm_share/eda/lib/asap_project/asap.view"
                        run_command(cmd)
                        
                        # 定义路径变量
                        base_path = f"/mnt/hgfs/vm_share/eda/synproj_asap/project_{case}/{case}/results"
                        tar_path = f"/mnt/hgfs/vm_share/eda/innovus_output__{core_utilization}__1x/{boundary}/{case}__{type_name}__{mode}"
                        core_utilization_float = Decimal(core_utilization) / Decimal(100)
                        core_utilization_str = f"0{core_utilization_float}"
                        
                        # 创建TCL命令文件
                        tcl_file = create_tcl_script(case, type_name, mode, boundary, core_utilization, 
                                                    base_path, tar_path, core_utilization_str)
                        
                        # 删除之前存在的目录并创建新的
                        if os.path.exists(tar_path):
                            shutil.rmtree(tar_path)
                        os.makedirs(tar_path, exist_ok=True)
                        
                        # 切换到目标目录并运行Innovus
                        current_dir = os.getcwd()
                        os.chdir(tar_path)
                        
                        innovus_cmd = f"innovus -no_gui -files /mnt/hgfs/vm_share/tools/innovus_project_pre_generation/{tcl_file}"
                        run_command(innovus_cmd)
                        
                        # 返回原来的目录
                        os.chdir(current_dir)
            
            # 对照组循环
            for type_name in ["no_type"]:
                for mode in ["no_mode"]:
                    print(f'=================={case}_{type_name}_{mode}')
                    
                    # 更新asap.view文件中的SDC路径
                    cmd = f"sed -i \"s|create_constraint_mode -name CONSTRAINTS -sdc_files {{.*}}|create_constraint_mode -name CONSTRAINTS -sdc_files {{/mnt/hgfs/vm_share/eda/synproj_asap/project_{case}/{case}/results/{case}.mapped.sdc}}|\" /mnt/hgfs/vm_share/eda/lib/asap_project/asap.view"
                    run_command(cmd)
                    
                    # 定义路径变量
                    base_path = f"/mnt/hgfs/vm_share/eda/synproj_asap/project_{case}/{case}/results"
                    tar_path = f"/mnt/hgfs/vm_share/eda/innovus_output__{core_utilization}__1x/{case}__{type_name}__{mode}"
                    core_utilization_float = Decimal(core_utilization) / Decimal(100)
                    core_utilization_str = f"0{core_utilization_float}"
                    
                    # 创建TCL命令文件，对照组没有boundary参数
                    tcl_file = create_tcl_script(case, type_name, mode, "", core_utilization, 
                                               base_path, tar_path, core_utilization_str)
                    
                    # 删除之前存在的目录并创建新的
                    if os.path.exists(tar_path):
                        shutil.rmtree(tar_path)
                    os.makedirs(tar_path, exist_ok=True)
                    
                    # 切换到目标目录并运行Innovus
                    current_dir = os.getcwd()
                    os.chdir(tar_path)
                    
                    innovus_cmd = f"innovus -no_gui -files /mnt/hgfs/vm_share/tools/innovus_project_pre_generation/{tcl_file}"
                    run_command(innovus_cmd)
                    
                    # 返回原来的目录
                    os.chdir(current_dir)

if __name__ == "__main__":
    main()
