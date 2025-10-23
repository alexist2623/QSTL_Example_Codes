# ============================================================
# Vivado 2017.3  |  Pack "TraceTrig.v" into a reusable IP
# Usage (example):
#   vivado -mode batch -source TraceTrig.tcl
# ============================================================
set project_name "TraceTrig"
set project_dir "C:/Jeonghyun/SNU_GIT/PulseGenerator/QES_Pathwave/IP/TraceTrig"
create_project ${project_name} ${project_dir}/${project_name} -part xc7k325tffg676-2

add_files -norecurse {C:/Jeonghyun/SNU_GIT/PulseGenerator/QES_Pathwave/IP/TraceTrig/TraceTrig.v}
set boardpath {D:/Xilinx/Vivado/2017.3/data/boards/board_files}
set_property top TraceTrig [current_fileset]
set_property top_file { C:/Jeonghyun/SNU_GIT/PulseGenerator/QES_Pathwave/IP/TraceTrig/TraceTrig.v } [current_fileset]
ipx::package_project -root_dir C:/Jeonghyun/SNU_GIT/PulseGenerator/QES_Pathwave/IP/TraceTrig -vendor xilinx.com -library user -taxonomy /UserIP
ipx::save_core [ipx::current_core]
set_property  ip_repo_paths  C:/Jeonghyun/SNU_GIT/PulseGenerator/QES_Pathwave/IP/TraceTrig [current_project]
update_ip_catalog
