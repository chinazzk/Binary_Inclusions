#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 10:26:04 2020

@author: zech0001
"""

import numpy as np
import ogs5py 
import binary_inclusions as bi

nn = 4
cond = np.loadtxt("../data/conditions.txt")

porosity = 0.31
storage = 0.0001
dispersivity_long = 0.01
dispersivity_trans = 0.01
keff1,keff2 = 2e-6,2e-4

domain={'x_0':-20,'x_L':200,'z_0':52,'z_L':62,'dx':0.25,'dz':0.05}
head_left,head_right = 63.0,62.34
source_pump=1.166e-5

time_steps = np.array([72, 997])
time_step_size = np.array([3600, 86400])
out_steps=86400.*np.array([9,49,126,202,279,370,503,594,1000])

### rfd file -time dependent source/boundary conditions       
rfd_tim = [0,86400.,172800.,176400.,259200.,864000.,8640000.,86400000.]
rfd_mass = [1.,1.,1.,0.,0.,0.,0.,0]

### ------------------------generate ogs base class------------------------- #
sim = ogs5py.OGS(task_root='../data/simulations/sim_{}'.format(nn), task_id='sim_{}_'.format(nn))   

### ----------------------- write process file ------------------------------# 
sim.pcs.add_block(PCS_TYPE='GROUNDWATER_FLOW')
sim.pcs.add_block(PCS_TYPE='MASS_TRANSPORT')  

### ----------------------- meh & geometry---- ------------------------------# 
domain.update(
        nx=int((domain['x_L']-domain['x_0'])/domain['dx']),
        nz=int((domain['z_L']-domain['z_0'])/domain['dz']),
        )

sim.msh.generate(
        "rectangular", 
        dim=2,
        mesh_origin=[domain['x_0'],domain['z_0']],
        element_no=[domain['nx'],domain['nz']],
        element_size=[domain['dx'],domain['dz']],
        )
sim.msh.swap_axis("y", "z")

# specify points and lines for boundary conditions and output
sim.gli.generate(
        "rectangular", 
        dim=2,
        ori=(domain['x_0'],domain['z_0']),
        size=(domain['x_L']-domain['x_0'],domain['z_L']-domain['z_0']),
        )
sim.gli.add_polyline(points=[0, 1], name="bottom")
sim.gli.add_polyline(points=[0, 3], name='left')
sim.gli.add_polyline(points=[2, 3], name="top")
sim.gli.add_polyline(points=[1, 2], name='right')
sim.gli.add_polyline(points=[[0, domain['z_0']+5.2, 0], [0,domain['z_0']+5.8, 0]], name='source')
sim.gli.swap_axis("y", "z")
  
### -----------------------  properties------------------------------------- #  
sim.mfp.add_block(#FLUID_PROPERTIES
        FLUID_TYPE='LIQUID',
        PCS_TYPE='HEAD',
        DENSITY=[1, 1000.],	
        VISCOSITY =[1, 0.001],
        )
sim.mcp.add_block(
        NAME='CONCENTRATION1',
        MOBILE=1,
        DIFFUSION=[1,1.0e-08],
        )
sim.msp.add_block(DENSITY = [1, 2000])

sim.mmp.add_block(
        GEOMETRY_DIMENSION=2, 
        GEOMETRY_AREA='1.0', 
        POROSITY='1 {}'.format(porosity), 
        TORTUOSITY='1 1.0', 
        STORAGE='1 {}'.format(storage), 
        MASS_DISPERSION=[1,dispersivity_long,dispersivity_trans])
#sim.mmp.update_block(PERMEABILITY_TENSOR=['ISOTROPIC', '1e-6']) # for homogeneous K-distribution

### --------------------heterogeneous K: binary structure ------------------ #  

sim.mpd.add(name="conductivity")
sim.mpd.add_block(
        MSH_TYPE="GROUNDWATER_FLOW", 
        MMP_TYPE="PERMEABILITY", 
        DIS_TYPE="ELEMENT", 
)

np.random.seed() #20201012+2

BI=bi.Block_Binary_Inclusions(
        dim         = 2,
        axis        = 0,
        k_bulk      = [keff1,keff2],  # conductivity value of bulk
        k_incl      = [keff2,keff1],  # conductivity value of inclusions
        nn          = [4,20],       # number of inclusions-blocks in x-direction
        ll          = [10,10],      # inclusion length in x-direction
        nz          = 20,           # number of inclusions in z-direction
        lz          = 0.5,          # inclusion length in z-direction
        nn_incl     = [3,3],        # number of inclusions within different K 
        )

#BI=bi.Simple_Binary_Inclusions(
#        dim     = 2,
#        k_bulk  = keff1,
#        k_incl  = keff2,
#        nx      = 22,    # number of inclusions in x-direction
#        lx      = 10,   # inclusion length in x-direction
#        nz      = 20,   # number of inclusions in z-direction
#        lz      = 0.5,  # inclusion length in z-direction
#        nz_incl = 3,    # number of inclusions with different K 
#        )
BI.scales2mesh(sim.msh.centroids_flat,x0=domain['x_0'],z0=domain['z_0'])

###########################################
### Simple 2D binary inclusion structure
#BI.structure()
#BI.bimodal_Keff(keff1,keff2)

BI.structure(bimodalKeff=True)
BI.structure2mesh()

sim.mpd.update_block(
        DATA=zip(range(len(BI.kk_mesh)), BI.kk_mesh),
        )
# write the new mpd file
sim.mpd.write_file()

### set conductivity to binary inclusion structure 
sim.mmp.update_block(PERMEABILITY_DISTRIBUTION=sim.mpd.file_name)

### -------- boundary, source and innitial condition file --------------------- #
### flow Boundary conditions depending on bc
sim.bc.add_block(
        PCS_TYPE='GROUNDWATER_FLOW', 
        PRIMARY_VARIABLE='HEAD', 
        GEO_TYPE=['POLYLINE', 'left'], 
        DIS_TYPE=['CONSTANT', head_left],
        )
sim.bc.add_block(
        PCS_TYPE='GROUNDWATER_FLOW', 
        PRIMARY_VARIABLE='HEAD', 
        GEO_TYPE=['POLYLINE', 'right'], 
        DIS_TYPE=['CONSTANT', head_right],
        )
### Transport boundary conditions
sim.bc.add_block(
        PCS_TYPE='MASS_TRANSPORT', 
        PRIMARY_VARIABLE='CONCENTRATION1', 
        GEO_TYPE=['POLYLINE', 'top'], 
        DIS_TYPE=['CONSTANT', 0.0],
        )
sim.bc.add_block(
        PCS_TYPE='MASS_TRANSPORT', 
        PRIMARY_VARIABLE='CONCENTRATION1', 
        GEO_TYPE=['POLYLINE', 'bottom'], 
        DIS_TYPE=['CONSTANT', 0.00 ]
        )  
sim.bc.add_block(
        PCS_TYPE='MASS_TRANSPORT', 
        PRIMARY_VARIABLE='CONCENTRATION1', 
        GEO_TYPE=['POLYLINE', 'left'], 
        DIS_TYPE=['CONSTANT', 0.00 ],
        )  
### Transport source condition
sim.st.add_block(
        PCS_TYPE='MASS_TRANSPORT', 
        PRIMARY_VARIABLE='CONCENTRATION1', 
        GEO_TYPE=['POLYLINE', 'source'], 
        DIS_TYPE=['CONSTANT_NEUMANN', 1e-08], 
        TIM_TYPE='CURVE 1',
        )
sim.st.add_block(
        PCS_TYPE='GROUNDWATER_FLOW', 
        PRIMARY_VARIABLE='HEAD', 
        GEO_TYPE=['POLYLINE', 'source'], 
        DIS_TYPE=['CONSTANT_NEUMANN', source_pump], 
        TIM_TYPE='CURVE 1',
        )
sim.rfd.add_block(
        CURVES=zip(rfd_tim,rfd_mass)
        )    

### initial conditions 
sim.ic.add_block(
        PCS_TYPE='GROUNDWATER_FLOW',
        PRIMARY_VARIABLE='HEAD',
        GEO_TYPE='DOMAIN', 
        DIS_TYPE=['CONSTANT', 0.5*(head_right-head_left)],
        )
sim.ic.add_block(
        PCS_TYPE='MASS_TRANSPORT', 
        PRIMARY_VARIABLE='CONCENTRATION1', 
        GEO_TYPE='DOMAIN', 
        DIS_TYPE=['CONSTANT', 0],
        )
### --------------- timing, output and numerics ---------------------------- #
### time file
sim.tim.add_block(
        PCS_TYPE='GROUNDWATER_FLOW', 
        TIME_START = 0, 
        TIME_END = 7200, #864000, 
        TIME_STEPS=zip(time_steps, time_step_size),
        )
sim.tim.add_block(
        PCS_TYPE='MASS_TRANSPORT', 
        TIME_START=0,
        TIME_END=7200,#86400000, 
        TIME_STEPS=zip(time_steps, time_step_size),
        )     
###  output file 
sim.out.add_block(
        NOD_VALUES=zip(['HEAD','CONCENTRATION1']), 
        ELE_VALUES=zip(['VELOCITY1_X','VELOCITY1_Y','VELOCITY1_Z']), 
        GEO_TYPE='DOMAIN', 
        DAT_TYPE='VTK', 
        TIM_TYPE=zip(out_steps),
        )
### num file 
sim.num.add_block(  # set the parameters for the solver
        PCS_TYPE='GROUNDWATER_FLOW', 
        LINEAR_SOLVER=[2, 1, 1.0e-12, 1000, 1.0, 100, 4],
        ELE_GAUSS_POINTS=3,     
        )
sim.num.add_block(  # set the parameters for the solver
        PCS_TYPE='MASS_TRANSPORT', 
        LINEAR_SOLVER=[2, 1, 1.0e-8, 100, 1.0, 100, 4],
        ELE_GAUSS_POINTS=3,
        )

sim.write_input()
#sim.run_model()
#sim.msh.export_mesh(
#    filepath='{}/conductivity.vtu'.format(sim.task_root),
#    file_format="vtk",
#    cell_data_by_id={"transmissivity": BI.kk_mesh},
#)