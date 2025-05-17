# 需要更改的路径：
# 1. BASE_PATH：mapped.v文件的路径
# 2. TAR_PATH：输出文件的路径
# 3. LIB_PATH：lib文件的路径
# 4. init_lef_file：lef文件的路径
# 5. init_verilog：mapped.v文件的路径
# 6. init_mmmc_file：asap.view文件的路径

# -a----         4/15/2025  12:37 AM          29134 Boundary_Areacoverage_250324_phase1_test1.txt
# -a----         4/15/2025  12:37 AM          29168 Boundary_Areacoverage_250324_phase1_test2.txt
# -a----         4/15/2025  12:37 AM          29137 Boundary_Areacoverage_250324_phase1_test3.txt
# -a----         4/15/2025  12:37 AM          28926 Boundary_Badoverlap_i0.txt
# -a----         4/15/2025  12:37 AM          29137 Boundary_Badoverlap_i100.txt
# -a----         4/15/2025  12:37 AM          28948 Boundary_Badoverlap_i250.txt
# -a----         4/15/2025  12:37 AM          29082 Boundary_BadSituation_OutofOrderComplete_i493.txt
# -a----         4/15/2025  12:37 AM          29085 Boundary_BadSituation_OutofOrderSlight-overlap_i499.txt
# -a----         4/15/2025  12:37 AM          29038 Boundary_BadSituation_overlap_i150.txt
# -a----         4/15/2025  12:37 AM          29132 Boundary_PinAffectCell_phase3best_test1.txt
# -a----         4/15/2025  12:37 AM          29164 Boundary_PinAffectCell_phase3best_test2.txt
# -a----         4/15/2025  12:37 AM          29153 Boundary_PinAffectCell_phase3initial_test1.txt
# -a----         4/15/2025  12:37 AM          29133 Boundary_PinAffectCell_phase3initial_test2.txt

# for core_utilization in 60 70 80 90

# echo '=================='${case}'__'${type}'__'${mode}'__'${boundary}
# echo '=================='${case}'__'${boundary}'__'${iter}


# ./run_innovus_preparation.sh case boundary core_utilization iter ending_point
# 后面的这些参数从命令行获取
case=$1
boundary=$2
core_utilization=$3
iter=$4
ending_point=${5:-route}  # 默认值为route

# 验证ending_point参数
if [[ "$ending_point" != "place" && "$ending_point" != "route" ]]; then
    echo "Error: ending_point必须是'place'或'route'"
    exit 1
fi

echo '==================case:'${case}'__boundary:'${boundary}'__core_utilization:'${core_utilization}'__iter:'${iter}'__ending_point:'${ending_point}

# 将/mnt/hgfs/vm_share/eda/lib/asap_project/asap.view文件中的路径
# create_constraint_mode -name CONSTRAINTS -sdc_files {不管是什么路径}
# 替换为create_constraint_mode -name CONSTRAINTS -sdc_files {/mnt/hgfs/vm_share/eda/synproj_asap/project_PE_array/PE_array/results/PE_array.mapped.sdc}
sed -i "s|create_constraint_mode -name CONSTRAINTS -sdc_files {.*}|create_constraint_mode -name CONSTRAINTS -sdc_files {/mnt/hgfs/vm_share/eda/synproj_asap/project_${case}/${case}/results/${case}.mapped.sdc}|" /mnt/hgfs/vm_share/eda/lib/asap_project/asap.view


# 定义路径变量
BASE_PATH=/mnt/hgfs/vm_share/eda/synproj_asap/project_${case}/${case}/results

TAR_PATH=/mnt/hgfs/vm_share/eda/innovus_output_dse/case__${case}__core_utilization__${core_utilization}__boundary__${boundary}__iter__${iter}
core_utilization_float=$(echo "scale=1; $core_utilization / 100" | bc)
# 将 core_utilization_float 转换为字符串
core_utilization_str="0$core_utilization_float"


# 使用cat和Here文档直接创建TCL文件
# cat > ${case}_${type}_${mode}_temp_cmd.tcl << EOF
cat > ${case}__${boundary}__${core_utilization}__${iter}.tcl << EOF
set SRCPATH $BASE_PATH
set TARPATH $TAR_PATH
set DESIGN $case


setMultiCpuUsage -localCpu max
set_global _enable_mmmc_by_default_flow      \$CTE::mmmc_default
suppressMessage ENCEXT-2799
win
set init_lef_file {/mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/techlef_misc/asap7_tech_1x_201209.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_L_1x_220121a.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_R_1x_220121a.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_SL_1x_220121a.lef /mnt/hgfs/vm_share/eda/lib/asap_project/asap7sc7p5t_28/LEF/asap7sc7p5t_28_SRAM_1x_220121a.lef}
set init_verilog \${SRCPATH}/\${DESIGN}.mapped.v
set init_mmmc_file /mnt/hgfs/vm_share/eda/lib/asap_project/asap.view
init_design

setAnalysisMode -reset
setAnalysisMode -analysisType onChipVariation -cppr both

# defIn /mnt/hgfs/vm_share/tools/innovus_project_pre_generation/PE_array.floorplan.${core_utilization}.def

getIoFlowFlag
setIoFlowFlag 0
floorPlan -site asap7sc7p5t -r 1 ${core_utilization_str} 0.0 0.0 0.0 0.0
uiSetTool select
getIoFlowFlag
fit


# group information here

$(cat ./constraint/${case}__${boundary}__${core_utilization}__${iter}.txt)

# Run placement
setRouteMode -earlyGlobalHonorMsvRouteConstraint false -earlyGlobalRoutePartitionPinGuide true
setEndCapMode -reset
setEndCapMode -boundary_tap false
setNanoRouteMode -quiet -droutePostRouteSpreadWire 1
setNanoRouteMode -quiet -timingEngine {}
setUsefulSkewMode -maxSkew false -noBoundary false -useCells {HB4xp67_ASAP7_75t_R HB3xp67_ASAP7_75t_R HB2xp67_ASAP7_75t_R HB1xp67_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx3_ASAP7_75t_R BUFx2_ASAP7_75t_R BUFx24_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx12_ASAP7_75t_R BUFx10_ASAP7_75t_R INVxp67_ASAP7_75t_R INVxp33_ASAP7_75t_R INVx8_ASAP7_75t_R INVx6_ASAP7_75t_R INVx5_ASAP7_75t_R INVx4_ASAP7_75t_R INVx3_ASAP7_75t_R INVx2_ASAP7_75t_R INVx1_ASAP7_75t_R INVx13_ASAP7_75t_R INVx11_ASAP7_75t_R CKINVDCx9p33_ASAP7_75t_R CKINVDCx8_ASAP7_75t_R CKINVDCx6p67_ASAP7_75t_R CKINVDCx5p33_ASAP7_75t_R CKINVDCx20_ASAP7_75t_R CKINVDCx16_ASAP7_75t_R CKINVDCx14_ASAP7_75t_R CKINVDCx12_ASAP7_75t_R CKINVDCx11_ASAP7_75t_R CKINVDCx10_ASAP7_75t_R} -maxAllowedDelay 1
# setUsefulSkewMode -maxSkew false -noBoundary false -useCells {HB4xp67_ASAP7_75t_SRAM HB3xp67_ASAP7_75t_SRAM HB2xp67_ASAP7_75t_SRAM HB1xp67_ASAP7_75t_SRAM BUFx8_ASAP7_75t_SRAM BUFx6f_ASAP7_75t_SRAM BUFx5_ASAP7_75t_SRAM BUFx4f_ASAP7_75t_SRAM BUFx4_ASAP7_75t_SRAM BUFx3_ASAP7_75t_SRAM BUFx2_ASAP7_75t_SRAM BUFx24_ASAP7_75t_SRAM BUFx16f_ASAP7_75t_SRAM BUFx12f_ASAP7_75t_SRAM BUFx12_ASAP7_75t_SRAM BUFx10_ASAP7_75t_SRAM HB4xp67_ASAP7_75t_SL HB3xp67_ASAP7_75t_SL HB2xp67_ASAP7_75t_SL HB1xp67_ASAP7_75t_SL BUFx8_ASAP7_75t_SL BUFx6f_ASAP7_75t_SL BUFx5_ASAP7_75t_SL BUFx4f_ASAP7_75t_SL BUFx4_ASAP7_75t_SL BUFx3_ASAP7_75t_SL BUFx2_ASAP7_75t_SL BUFx24_ASAP7_75t_SL BUFx16f_ASAP7_75t_SL BUFx12f_ASAP7_75t_SL BUFx12_ASAP7_75t_SL BUFx10_ASAP7_75t_SL HB4xp67_ASAP7_75t_R HB3xp67_ASAP7_75t_R HB2xp67_ASAP7_75t_R HB1xp67_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx3_ASAP7_75t_R BUFx2_ASAP7_75t_R BUFx24_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx12_ASAP7_75t_R BUFx10_ASAP7_75t_R HB4xp67_ASAP7_75t_L HB3xp67_ASAP7_75t_L HB2xp67_ASAP7_75t_L HB1xp67_ASAP7_75t_L BUFx8_ASAP7_75t_L BUFx6f_ASAP7_75t_L BUFx5_ASAP7_75t_L BUFx4f_ASAP7_75t_L BUFx4_ASAP7_75t_L BUFx3_ASAP7_75t_L BUFx2_ASAP7_75t_L BUFx24_ASAP7_75t_L BUFx16f_ASAP7_75t_L BUFx12f_ASAP7_75t_L BUFx12_ASAP7_75t_L BUFx10_ASAP7_75t_L INVxp67_ASAP7_75t_SRAM INVxp33_ASAP7_75t_SRAM INVx8_ASAP7_75t_SRAM INVx6_ASAP7_75t_SRAM INVx5_ASAP7_75t_SRAM INVx4_ASAP7_75t_SRAM INVx3_ASAP7_75t_SRAM INVx2_ASAP7_75t_SRAM INVx1_ASAP7_75t_SRAM INVx13_ASAP7_75t_SRAM INVx11_ASAP7_75t_SRAM INVxp67_ASAP7_75t_SL INVxp33_ASAP7_75t_SL INVx8_ASAP7_75t_SL INVx6_ASAP7_75t_SL INVx5_ASAP7_75t_SL INVx4_ASAP7_75t_SL INVx3_ASAP7_75t_SL INVx2_ASAP7_75t_SL INVx1_ASAP7_75t_SL INVx13_ASAP7_75t_SL INVx11_ASAP7_75t_SL INVxp67_ASAP7_75t_R INVxp33_ASAP7_75t_R INVx8_ASAP7_75t_R INVx6_ASAP7_75t_R INVx5_ASAP7_75t_R INVx4_ASAP7_75t_R INVx3_ASAP7_75t_R INVx2_ASAP7_75t_R INVx1_ASAP7_75t_R INVx13_ASAP7_75t_R INVx11_ASAP7_75t_R INVxp67_ASAP7_75t_L INVxp33_ASAP7_75t_L INVx8_ASAP7_75t_L INVx6_ASAP7_75t_L INVx5_ASAP7_75t_L INVx4_ASAP7_75t_L INVx3_ASAP7_75t_L INVx2_ASAP7_75t_L INVx1_ASAP7_75t_L INVx13_ASAP7_75t_L INVx11_ASAP7_75t_L} -maxAllowedDelay 1
setPlaceMode -reset
setPlaceMode -congEffort auto -timingDriven 1 -clkGateAware 1 -powerDriven 0 -ignoreScan 1 -reorderScan 1 -ignoreSpare 0 -placeIOPins 0 -moduleAwareSpare 0 -preserveRouting 0 -rmAffectedRouting 0 -checkRoute 0 -swapEEQ 0
setPlaceMode -fp false
setMultiCpuUsage -localCpu max
place_opt_design
report_route -summary
saveNetlist \${TARPATH}/\${DESIGN}.postPlace.mapped.v
defOut -floorplan -netlist -routing \${TARPATH}/\${DESIGN}.postPlace.def
# place_design


timeDesign -preCTS -pathReports -drvReports -slackReports -numPaths 50 -prefix \${DESIGN}_preCTS -outDir \${TARPATH}/\${DESIGN}_timingReports_preCTS
EOF

# 如果ending_point是route，则添加路由相关的TCL命令
if [[ "$ending_point" == "route" ]]; then
cat >> ${case}__${boundary}__${core_utilization}__${iter}.tcl << EOF

# Routing
setNanoRouteMode -quiet -timingEngine {}
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

# saveDesign \${TARPATH}/\${DESIGN}.routed.enc

set dbgLefDefOutVersion 5.8
global dbgLefDefOutVersion
set dbgLefDefOutVersion 5.8
saveNetlist \${TARPATH}/\${DESIGN}.postRoute.mapped.v
defOut -floorplan -netlist -routing \${TARPATH}/\${DESIGN}.postRoute.def





timeDesign -postRoute -pathReports -drvReports -slackReports -numPaths 50 -prefix \${DESIGN}_postRoute -outDir \${TARPATH}/\${DESIGN}_timingReports_postRoute
EOF
fi

# 添加exit命令结束TCL文件
cat >> ${case}__${boundary}__${core_utilization}__${iter}.tcl << EOF

exit
EOF

echo "Current directory before creating temp file: $(pwd)"
# echo "Creating file: ${case}_${type}_${mode}_temp_cmd.tcl"
echo "Creating file: ${case}__${boundary}__${core_utilization}__${iter}.tcl"
echo "File created. Checking if it exists: $(ls -la ${case}__${boundary}__${core_utilization}__${iter}.tcl 2>/dev/null || echo 'File not found')"

# 设置权限
chmod 777 ${case}__${boundary}__${core_utilization}__${iter}.tcl

# 删除之前存在的
rm -rf ${TAR_PATH}
# 创建输出目录
mkdir -p ${TAR_PATH}
cd ${TAR_PATH}

# 使用临时文件运行innovus
# timeout 5h innovus -no_gui -files /mnt/hgfs/vm_share/tools/innovus_project_pre_generation/${case}_${type}_${mode}_temp_cmd.tcl || echo "Innovus timed out after 20 minutes for ${case}_${type}_${mode}, continuing with next configuration..."
innovus -no_gui -files /mnt/hgfs/vm_share/tools/innovus_design_space_exploration/${case}__${boundary}__${core_utilization}__${iter}.tcl

# 返回原来的目录
cd /mnt/hgfs/vm_share/tools/innovus_design_space_exploration
