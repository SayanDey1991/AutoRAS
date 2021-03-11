# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# Created by Tao Huang, March 2021, in Python 3.7
#
# Module to 1) create a 1D unsteady flow data file based on given boundary data;
#           2) create a HEC-RAS 1D unsteady flow plan file based on a template list;
#           3) modify the Manning's n (given multiply factor) in the original geometry file
#              and create a new geometry file with new Manning's n;
#           4) modify the original HEC-RAS project file;
#           5) run HEC-RAS 1D unsteady flow analysis; and
#           6) extract 1D unsteady base results from the generated HEC-RAS plan HDF file.
#
# Version 1.0
#
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import os
import pandas as pd
import numpy as np
from win32com.client import Dispatch
import h5py

## A function to create a 1D unsteady flow data file based on given boundary data

def Py2HecRas_1DU_Flow(ProjectName):
        """ProjectName is the name (without ".prj") of a HEC-RAS project.
        """
    # A function to read the flow hydrograph from the boundary condition CSV files
    
    def get_upstream_flow(RiverID,ReachID):
        # Change the data format for HEC-RAS unsteady flow data file
        # 10 numbers in each row and 8 placeholders for each data point

        flow_raw_data = pd.read_csv("./1D_Unsteady_BC/BC_"+str(RiverID)+"_"+str(ReachID)+".csv")

        flow_bc = ["Interval=1DAY\n",
                   "Flow Hydrograph= "+str(len(flow_raw_data))+"\n"]

        for i in range(len(flow_raw_data)):

            temp = "%8.1f"%flow_raw_data["Flow_cfs"][i]
            flow_bc.append(temp)

            if (i+1)%10 == 0 and i!=len(flow_raw_data)-1:
                temp = "\n"
                flow_bc.append(temp)

        flow_bc.append("\n")

        Start_DateTime = pd.to_datetime(flow_raw_data["DateTime"][0])
        Start_DateTime = Start_DateTime.strftime('%d%b%Y,%H:%M')

        fixed_content = ["DSS Path=\n",
                         "Use DSS=False\n",
                         "Use Fixed Start Time=True\n",
                         "Fixed Start Date/Time="+str(Start_DateTime)+"\n",
                         "Is Critical Boundary=False\n",
                         "Critical Boundary Flow=\n"]
        flow_bc += fixed_content

        return flow_bc

    # A function to read the friction slope from the boundary condition CSV files

    def get_downstream_fs(RiverID,ReachID):

        fs_raw_data = pd.read_csv("./1D_Unsteady_BC/BC_"+str(RiverID)+"_"+str(ReachID)+".csv")

        fs_bc = ["Friction Slope="+str(fs_raw_data["Friction Slope"][0])+",0\n"]

        return fs_bc

    # Initiate HEC-RAS API
    hec=Dispatch("RAS507.HECRASController")
    hec_geo=Dispatch("RAS507.HECRASGeometry")

    ras_file = os.path.join(os.getcwd(),ProjectName+".prj")

    hec.Project_Open(ras_file)

    # Numbers of rivers and the corresponding reaches
    River_No = hec_geo.nRiver()

    Reach_No = []

    for i in list(range(1,River_No+1)):   
        Reach_No.append(hec_geo.nReach(i)[0])

    River_ID = []

    for i in list(range(1,River_No+1)): 
        River_ID += [i]*Reach_No[i-1]
        
    Reach_ID = []

    for i in Reach_No: 
        Reach_ID += list(range(1,i+1))

    # create a dataframe to store ID of river and its corresponding ID of reach
    RR = pd.DataFrame(None,columns=['River_ID','Reach_ID'])
    RR['River_ID'] = River_ID
    RR['Reach_ID'] = Reach_ID

    River_Name = []
    Reach_Name = []

    for i in range(len(RR)):
            
        River_Name.append(hec_geo.RiverName(RR['River_ID'][i])[0])
        Reach_Name.append(hec_geo.ReachName(RR['River_ID'][i],RR['Reach_ID'][i])[0])
            
    # create a dataframe to store Names of river and its corresponding names of reach
    RRname = pd.DataFrame(None, columns=['River_Name','Reach_Name'])
    RRname['River_Name'] = River_Name
    RRname['Reach_Name'] = Reach_Name

    # A list to store the information for the unsteady flow data file

    UFD_file = ["Flow Title="+ProjectName+"\n",
                "Program Version=5.07\n",
                "Use Restart= 0\n"]

    for i in range(len(RR)):
            
        RiverName = RRname['River_Name'][i]
        ReachName = RRname['Reach_Name'][i]
        
        #read information of river stations: number of river station (NRS), list of RS (LRS) and type of RS (TRS)
        RiverID = RR['River_ID'][i]
        ReachID = RR['Reach_ID'][i]

        _,_,_,LRS,_ = hec.Geometry_GetNodes(RiverID,ReachID)

        #for the most upstream RS
        if ReachID == 1:
            Upstream_RS = LRS[0]
            UFD_file.append("Boundary Location="+RiverName+","+ReachName+","+Upstream_RS+",\n")
            UFD_file += get_upstream_flow(RiverID,ReachID)

        #for the most downstream RS
        elif ReachID == RR['Reach_ID'].max():
            Downstream_RS = LRS[-1]
            UFD_file.append("Boundary Location="+RiverName+","+ReachName+","+Downstream_RS+",\n")
            UFD_file += get_downstream_fs(RiverID,ReachID)

    f = open(ProjectName+".u01", "w")

    f.writelines(UFD_file)

    f.close()

    # close HEC-RAS Project and quit
    hec.Project_Close()
    hec.QuitRas()

    # delete HEC-RAS controller
    del hec
    del hec_geo

    print("HEC-RAS 1D unsteady flow data file for "+ProjectName+" is done!")

## a function to modify the Manning's n (multiply factor is given) in the original geometry file
## and generate a new geometry file with new Manning's n

def Py2HecRas_1DU_Geo(fl,fc,fr,ProjectName,g):
    """fl is the multiply factor for the LOB Manning's n
       fc is the multiply factor for the LOB Manning's n
       fr is the multiply factor for the LOB Manning's n
       g is the new number of geometry files
       """
    # a function to modify the Manning's n (multiply factor is given) in the original geometry file
    def Py2HecRas_1DU_MN(fl,fc,fr,ProjectName,g):
        # Initiate HEC-RAS API
        hec=Dispatch("RAS507.HECRASController")
        hec_geo=Dispatch("RAS507.HECRASGeometry")

        ras_file = os.path.join(os.getcwd(),ProjectName+".prj")

        hec.Project_Open(ras_file)

        # Numbers of rivers and the corresponding reaches
        River_No = hec_geo.nRiver()

        Reach_No = []

        for i in list(range(1,River_No+1)):   
            Reach_No.append(hec_geo.nReach(i)[0])

        River_ID = []

        for i in list(range(1,River_No+1)): 
            River_ID += [i]*Reach_No[i-1]
            
        Reach_ID = []

        for i in Reach_No: 
            Reach_ID += list(range(1,i+1))

        # create a dataframe to store ID of river and its corresponding ID of reach
        RR = pd.DataFrame(None,columns=['River_ID','Reach_ID'])
        RR['River_ID'] = River_ID
        RR['Reach_ID'] = Reach_ID

        River_Name = []
        Reach_Name = []
        RS=[]
        RS_type=[]

        for i in range(len(RR)):
            #read information of river stations: list of RS (LRS) and type of RS (TRS)

            _,_,_,LRS,TRS = hec.Geometry_GetNodes(RR['River_ID'][i],RR['Reach_ID'][i])

            for j in range(len(LRS)):    
                
                River_Name.append(hec_geo.RiverName(RR['River_ID'][i])[0])
                Reach_Name.append(hec_geo.ReachName(RR['River_ID'][i],RR['Reach_ID'][i])[0])
                RS.append(LRS[j])
                RS_type.append(TRS[j])
                
        # create a dataframe to store Names of river and its corresponding names of reach and River stations
        RRRS = pd.DataFrame(None, columns=['River_Name','Reach_Name','River_Station','RS_Type'])
        RRRS['River_Name'] = River_Name
        RRRS['Reach_Name'] = Reach_Name
        RRRS['River_Station'] = RS
        RRRS['RS_Type'] = RS_type

        for i in range(len(RRRS)):
            # get the simple river station instead of hydraulic structures
            if RRRS['RS_Type'][i] == "":
                # get the original Manning's values for LOB, Channel, and ROB
                ini_n = hec.Geometry_GetMann(RRRS['River_Name'][i],
                                             RRRS['Reach_Name'][i],
                                             RRRS['River_Station'][i])[5]

                # assign the new Manning's values for LOB, Channel, and ROB
                new_ln = fl*ini_n[0]
                new_cn = fc*ini_n[1]
                new_rn = fr*ini_n[2]

                hec.Geometry_SetMann_LChR(RRRS['River_Name'][i],
                                          RRRS['Reach_Name'][i],
                                          RRRS['River_Station'][i],
                                          new_ln,new_cn,new_rn)
        
        hec_geo.Save()

        hec.Project_Close()
        hec.QuitRas()

        del hec
        del hec_geo

    Py2HecRas_1DU_MN(fl,fc,fr,ProjectName,g)
    
    # read the initial geometry file (number is 99)
    f_old = open(ProjectName+'.g99','r')
    # write the new geometry data file
    f_new = open(ProjectName+'.g'+str(g).zfill(2),'w')

    for line in f_old:
        f_new.write(line)

    f_old.close()
    f_new.close()

    # restore the origial geometry file
    Py2HecRas_1DU_MN(1/fl,1/fc,1/fr,ProjectName,g=99)
    
    print("HEC-RAS 1D geometry file for "+ProjectName+" is done!")


## a function to Modify the original project file

def Py2HecRas_1DU_Project(u,g,p,ProjectName):
    """u is the added number of unsteady flow data files
       g is the added number of geometry files
       p is the added number of plan files
       """
    # list of the added unsteady flow data file
    uf = "Unsteady File=u"+str(u).zfill(2)+"\n"

    # list of the added plan file
    pf = "Plan File=p"+str(p).zfill(2)+"\n"

    if g != 0:
        gf = "Geom File=g"+str(g).zfill(2)+"\n"
    else:
        gf = ""

    # Modify the original project file

    f_prj = open(ProjectName+".prj", "r")

    prj_contents = f_prj.readlines()

    f_prj.close()

    f_prj = open(ProjectName+".prj", "w")

    if gf:
        prj_contents.insert(4,gf+uf+pf)
    else:
        prj_contents.insert(4,uf+pf)

    f_prj.writelines(prj_contents)

    f_prj.close()

    print("HEC-RAS 1D unsteady project file for "+ProjectName+" is done!")

## a function to formulate several plan files
# by selecting a specific set of geometry data and unsteady flow data file

def Py2HecRas_1DU_Plan(g,u,StartDateTime,EndDateTime,CI="1HOUR",HI="1DAY",MI="1DAY",DI="1DAY",ProjectName="test"):
    """g is the number of geometry data files
       u is the number of unsteady flow data files
       StartDateTime is the starting simulation datetime(YYYY-MM-DD,HH:mm)
       EndDateTime is the ending simulation datetime(YYYY-MM-DD,HH:mm)
       CI is computation interval
       HI is hydrograph output interval
       MI is mapping output interval
       DI is detailed output interval
       """
    # Initiate HEC-RAS API
    hec=Dispatch("RAS507.HECRASController")
    ras_file = os.path.join(os.getcwd(),ProjectName+".prj")

    hec.Project_Open(ras_file)
    
    # list of geometry data files
    gf = ["Geom File=g"+str(i).zfill(2) for i in range(1,g+1)]

    # list of unsteady flow data files
    uf = ["Flow File=u"+str(i).zfill(2) for i in range(1,u+1)]

    # change the format of the simulation datetime
    StartDT = pd.to_datetime(StartDateTime)
    StartDT = StartDT.strftime('%d%b%Y,%H:%M')
    EndDT = pd.to_datetime(EndDateTime)
    EndDT = EndDT.strftime('%d%b%Y,%H:%M')

    # change the simulation interval
    Computation_Interval=CI
    Output_Interval=HI
    Instantaneous_Interval=DI
    Mapping_Interval=MI

    # a list stores the template of an unsteady plan file

    template_uf =  ['Plan Title=tempate_uf\n',
                    'Program Version=5.07\n',
                    'Short Identifier=unsteadyflow                                                              \n',
                    'Simulation Date=01JAN2008,00:00,07JAN2008,00:00\n',
                    'Geom File=g01\n',
                    'Flow File=u01\n',
                    'Subcritical Flow\n',
                    'K Sum by GR= 0 \n',
                    'Std Step Tol= .01 \n',
                    'Critical Tol= .01 \n',
                    'Num of Std Step Trials= 20 \n',
                    'Max Error Tol= .3 \n',
                    'Flow Tol Ratio= .001 \n',
                    'Split Flow NTrial= 30 \n',
                    'Split Flow Tol= .02 \n',
                    'Split Flow Ratio= .02 \n',
                    'Log Output Level= 0 \n',
                    'Friction Slope Method= 1 \n',
                    'Unsteady Friction Slope Method= 2 \n',
                    'Unsteady Bridges Friction Slope Method= 1 \n',
                    'Parabolic Critical Depth\n',
                    'Global Vel Dist= 0 , 0 , 0 \n',
                    'Global Log Level= 0 \n',
                    'CheckData=True\n',
                    'Encroach Param=-1 ,0,0, 0 \n',
                    'Computation Interval=1HOUR\n',
                    'Output Interval=1DAY\n',
                    'Instantaneous Interval=1DAY\n',
                    'Mapping Interval=1DAY\n',
                    'Computation Time Step Use Courant=        0\n',
                    'Computation Time Step Use Time Series=    0\n',
                    'Computation Time Step Max Courant=\n',
                    'Computation Time Step Min Courant=\n',
                    'Computation Time Step Count To Double=0\n',
                    'Computation Time Step Max Doubling=0\n',
                    'Computation Time Step Max Halving=0\n',
                    'Computation Time Step Residence Courant=0\n',
                    'Run HTab=-1 \n',
                    'Run UNet=-1 \n',
                    'Run Sediment= 0 \n',
                    'Run PostProcess= 0 \n',
                    'Run WQNet= 0 \n',
                    'Run RASMapper=-1 \n',
                    'UNET Theta= 1 \n',
                    'UNET Theta Warmup= 1 \n',
                    'UNET ZTol= .02 \n',
                    'UNET ZSATol= .02 \n', 'UNET QTol=\n',
                    'UNET MxIter= 20 \n',
                    'UNET Max Iter WO Improvement= 0 \n',
                    'UNET MaxInSteps= 0 \n',
                    'UNET DtIC= 0 \n',
                    'UNET DtMin= 0 \n',
                    'UNET MaxCRTS= 20 \n',
                    'UNET WFStab= 2 \n',
                    'UNET SFStab= 1 \n',
                    'UNET WFX= 1 \n',
                    'UNET SFX= 1 \n',
                    'UNET 1D Methodology=Finite Difference\n',
                    'UNET DSS MLevel= 4 \n', 'UNET Pardiso=0\n',
                    'UNET DZMax Abort= 100 \n',
                    'UNET Use Existing IB Tables=-1 \n',
                    'UNET Froude Reduction=False\n',
                    'UNET Froude Limit= .8 \n',
                    'UNET Froude Power= 4 \n',
                    'UNET D1 Cores= 0 \n',
                    'UNET D2 Coriolis=0\n',
                    'UNET D2 Cores= 0 \n',
                    'UNET D2 Theta= 1 \n',
                    'UNET D2 Theta Warmup= 1 \n',
                    'UNET D2 Z Tol= .01 \n',
                    'UNET D2 Volume Tol= .01 \n',
                    'UNET D2 Max Iterations= 20 \n',
                    'UNET D2 Equation= 0 \n',
                    'UNET D2 TotalICTime=\n',
                    'UNET D2 RampUpFraction=.1\n',
                    'UNET D2 TimeSlices= 1 \n',
                    'UNET D2 Eddy Viscosity=\n',
                    'UNET D2 BCVolumeCheck=0\n',
                    'UNET D2 Latitude=\n',
                    'UNET D1D2 MaxIter= 0 \n',
                    'UNET D1D2 ZTol=.01\n',
                    'UNET D1D2 QTol=.1\n',
                    'UNET D1D2 MinQTol=1\n',
                    'DSS File=dss\n',
                    'Write IC File= 0 \n',
                    'Write IC File at Fixed DateTime=0\n',
                    'IC Time=,,\n',
                    'Write IC File Reoccurance=\n',
                    'Write IC File at Sim End=0\n',
                    'Echo Input=False\n',
                    'Echo Parameters=False\n',
                    'Echo Output=False\n',
                    'Write Detailed= 0 \n',
                    'HDF Write Warmup=0\n',
                    'HDF Write Time Slices=0\n',
                    'HDF Flush=0\n',
                    'HDF Face Node Velocities=0\n',
                    'HDF Compression= 1 \n',
                    'HDF Chunk Size= 1 \n',
                    'HDF Spatial Parts= 1 \n',
                    'HDF Use Max Rows=0\n',
                    'HDF Fixed Rows= 1 \n',
                    'Calibration Method= 0 \n',
                    'Calibration Iterations= 20 \n',
                    'Calibration Max Change=.05\n',
                    'Calibration Tolerance=.2\n',
                    'Calibration Maximum=1.5\n',
                    'Calibration Minimum=.5\n',
                    'Calibration Optimization Method= 1 \n',
                    'Calibration Window=,,,\n',
                    'WQ AD Non Conservative\n',
                    'WQ ULTIMATE=-1\n',
                    'WQ Max Comp Step=1HOUR\n',
                    'WQ Output Interval=15MIN\n',
                    'WQ Output Selected Increments= 0 \n',
                    'WQ Output face flow=0\n',
                    'WQ Output face velocity=0\n',
                    'WQ Output face area=0\n',
                    'WQ Output face dispersion=0\n',
                    'WQ Output cell volume=0\n',
                    'WQ Output cell surface area=0\n',
                    'WQ Output cell continuity=0\n',
                    'WQ Output cumulative cell continuity=0\n',
                    'WQ Output face conc=0\n',
                    'WQ Output face dconc_dx=0\n',
                    'WQ Output face courant=0\n',
                    'WQ Output face peclet=0\n',
                    'WQ Output face adv mass=0\n',
                    'WQ Output face disp mass=0\n',
                    'WQ Output cell mass=0\n',
                    'WQ Output cell source sink temp=0\n',
                    'WQ Output nsm pathways=0\n',
                    'WQ Output nsm derived pathways=0\n',
                    'WQ Output MaxMinRange=-1\n',
                    'WQ Daily Max Min Mean=-1\n',
                    'WQ Daily Range=0\n',
                    'WQ Daily Time=0\n',
                    'WQ Create Restart=0\n',
                    'WQ Fixed Restart=0\n',
                    'WQ Restart Simtime=\n',
                    'WQ Restart Date=\n',
                    'WQ Restart Hour=\n',
                    'WQ System Summary=0\n',
                    'WQ Write To DSS=0\n',
                    'WQ Use Fixed Temperature=0\n',
                    'WQ Fixed Temperature=\n',
                    'Sorting and Armoring Iterations= 10 \n',
                    'XS Update Threshold= .02 \n',
                    'Bed Roughness Predictor= 0 \n',
                    'Hydraulics Update Threshold= .02 \n',
                    'Energy Slope Method= 1 \n',
                    'Volume Change Method= 1 \n',
                    'Sediment Retention Method= 0 \n',
                    'XS Weighting Method= 0 \n',
                    'Number of US Weighted Cross Sections= 1 \n',
                    'Number of DS Weighted Cross Sections= 1 \n',
                    'Upstream XS Weight=0\n', 'Main XS Weight=1\n',
                    'Downstream XS Weight=0\n',
                    "Number of DS XS's Weighted with US Boundary= 1 \n",
                    'Upstream Boundary Weight= 1 \n',
                    'Weight of XSs Associated with US Boundary= 0 \n',
                    "Number of US XS's Weighted with DS Boundary= 1 \n",
                    'Downstream Boundary Weight= .5 \n',
                    'Weight of XSs Associated with DS Boundary= .5 \n',
                    'Percentile Method= 0 \n',
                    'Sediment Output Level= 3 \n',
                    'Mass or Volume Output= 0 \n',
                    'Output Increment Type= 1 \n',
                    'Profile and TS Output Increment= 1 \n',
                    'XS Output Flag= 0 \n',
                    'XS Output Increment= 10 \n',
                    'Write Gradation File= 0 \n',
                    'Read Gradation Hotstart= 0 \n',
                    'Gradation File Name=\n',
                    'Write HDF5 File= 1 \n',
                    'Write Binary Output= 1 \n',
                    'Write DSS Sediment File= 0 \n',
                    'SV Curve= 0 \n',
                    'Specific Gage Flag= 0 \n']

    # New plan files are different combinations of geometry data files and unsteady flow data files
    pn = hec.Plan_Names()[0]
    ProjectName=ProjectName

    for i in range(g):
        for j in range(u):

            pn += 1
            
            # read the initial HEC-RAS plan file
            f_old = template_uf

            # write the new plan file
            f_new = open(ProjectName+'.p'+str(pn).zfill(2),'w')

            for line in f_old:
                if "Plan Title=" in line:
                    # replace the Plan Title
                    #line = line.replace("Plan Title="+filename,"Plan Title=g"+str(i+1).zfill(2)+"u"+str(j+1).zfill(2))
                    #line = "Plan Title=g"+str(i+1).zfill(2)+"u"+str(j+1).zfill(2)+"\n"
                    line = "Plan Title=Plan "+str(pn).zfill(2)+"\n"
                    
                elif "Short Identifier=" in line:
                    # replace the Short Identifier
                    line = "Short Identifier=g"+str(i+1).zfill(2)+"u"+str(j+1).zfill(2)+"\n"

                elif "Simulation Date=" in line:
                    # replace the simulation datetime
                    line = "Simulation Date="+str(StartDT)+','+str(EndDT)+"\n"

                elif "Geom File=" in line:
                    # replace the Geom File
                    line = line.replace("Geom File=g01",gf[i])
                    
                elif "Flow File=" in line:
                    # replace the Flow File
                    line = line.replace("Flow File=u01",uf[j])

                elif "Computation Interval=" in line:
                    # replace the Computation Interval
                    line = "Computation Interval="+Computation_Interval+"\n"

                elif "Output Interval=" in line:
                    # replace the Output Interval
                    line = "Output Interval="+Output_Interval+"\n"

                elif "Instantaneous Interval=" in line:
                    # replace the Instantaneous Interval
                    line = "Instantaneous Interval="+Instantaneous_Interval+"\n"

                elif "Mapping Interval=" in line:
                    # replace the Mapping Interval
                    line = "Mapping Interval="+Mapping_Interval+"\n"
                    
                f_new.write(line)

            f_new.close()
    
    # modify the original project file
    Py2HecRas_1DU_Project(u=u,g=0,p=pn,ProjectName)
    
    # close HEC-RAS Project
    hec.Project_Close()
    hec.QuitRas()
    
    # delete HEC-RAS controller
    del hec
      
    print("HEC-RAS 1D unsteady flow plan file "+ProjectName+" is done!")


## a function to run a 1D unsteady flow analysis and extract the results

def Py2HecRas_1DU_Run(ProjectName):
    """This function takes a ProjectName of HEC-RAS 1D unsteady flow analysis as input.
       Run the HEC-RAS model, and then extract the base results of all the cross sections,
       which are saved as CSV files in the results folder - '1D_Unsteady_Results'."""

    # function to create a folder to store the results if it does not exist

    def ResultsFolder(Folder):
        if os.path.exists(Folder) == False:
            os.mkdir(Folder)

    # Initiate HEC-RAS API
    hec=Dispatch("RAS507.HECRASController")
    #hec_geo=Dispatch("RAS507.HECRASGeometry")

    ProjectName = ProjectName

    ras_file = os.path.join(os.getcwd(),ProjectName+".prj")

    hec.ShowRas()

    hec.Project_Open(ras_file)

    # obtain the number and name of plan files
    #PlanNo=hec.Plan_Names()[0]
    PlanNames=hec.Plan_Names()[1]

    #hec.Plan_SetCurrent(PlanNames[i])
    hec.Plan_SetCurrent(PlanNames[0])

    ### extract resilts from 1D HEC-RAS unsteady flow analysis

    Folder1 = './1D_Unsteady_Results/'
    ResultsFolder(Folder1)

    Msg1,Msg2,Msg3,Msg4 = hec.Compute_CurrentPlan(None,None,True)

    # extract results from HDF file(e.g.,PlanName.p01.hdf)
    # read the datasets and groups in the HDF5 file
    hdf = h5py.File(hec.CurrentPlanFile()+'.hdf', 'r')

    # extract WSE
    WSE_all = np.array(hdf.get('Results')
                       .get('Unsteady')
                       .get('Output')
                       .get('Output Blocks')
                       .get('Base Output')
                       .get('Unsteady Time Series')
                       .get('Cross Sections')
                       .get('Water Surface'))

    WSE_all = np.transpose(WSE_all)

    # extract flow
    flow_all = np.array(hdf.get('Results')
                        .get('Unsteady')
                        .get('Output')
                        .get('Output Blocks')
                        .get('Base Output')
                        .get('Unsteady Time Series')
                        .get('Cross Sections')
                        .get('Flow'))

    flow_all = np.transpose(flow_all)

    # extract average velocity of flow in main channel
    VC_all = np.array(hdf.get('Results')
                        .get('Unsteady')
                        .get('Output')
                        .get('Output Blocks')
                        .get('Base Output')
                        .get('Unsteady Time Series')
                        .get('Cross Sections')
                        .get('Velocity Channel'))

    VC_all = np.transpose(VC_all)

    # extract average velocity of flow in total cross section
    VT_all = np.array(hdf.get('Results')
                        .get('Unsteady')
                        .get('Output')
                        .get('Output Blocks')
                        .get('Base Output')
                        .get('Unsteady Time Series')
                        .get('Cross Sections')
                        .get('Velocity Total'))

    VT_all = np.transpose(VT_all)

    DateTime = np.array(hdf.get('Results')
                        .get('Unsteady')
                        .get('Output')
                        .get('Output Blocks')
                        .get('Base Output')
                        .get('Unsteady Time Series')
                        .get('Time Date Stamp'))

    DateTime = [str(DateTime[i]).split("'")[1] for i in range(len(DateTime))]
    DateTime = pd.to_datetime(DateTime)
    DateTime = DateTime.strftime('%d-%m-%Y %H:%M:%S')
    DateTime = list(DateTime)
    
    # extract the information of all the cross sections

    CS_all = np.array(hdf.get('Results')
                      .get('Unsteady')
                      .get('Output')
                      .get('Output Blocks')
                      .get('Base Output')
                      .get('Unsteady Time Series')
                      .get('Cross Sections')
                      .get('Cross Section Only'))

    CS_all = [str(CS_all[i]).split("'")[1] for i in range(len(CS_all))]

    CS_all = np.array([CS_all[i].split() for i in range(len(CS_all))])

    Xs_ID = CS_all[:,2]

    River = CS_all[:,0]

    Reach = CS_all[:,1]

    # organize the dataframe for output

    WSE_all = np.c_[River,Reach,WSE_all]

    flow_all = np.c_[River,Reach,flow_all]

    VC_all = np.c_[River,Reach,VC_all]

    VT_all = np.c_[River,Reach,VT_all]

    DateTime = ['River','Reach']+DateTime

    # create dataframes to store the WSE (stage),flow, and velocity of all the cross sections

    WSE = pd.DataFrame(WSE_all,
                       index=Xs_ID,
                       columns=DateTime)
    WSE.index.name = 'Xs_ID'

    flow = pd.DataFrame(flow_all,
                       index=Xs_ID,
                       columns=DateTime)
    flow.index.name = 'Xs_ID'

    VC = pd.DataFrame(VC_all,
                      index=Xs_ID,
                      columns=DateTime)
    VC.index.name = 'Xs_ID'

    VT = pd.DataFrame(VT_all,
                      index=Xs_ID,
                      columns=DateTime)
    VT.index.name = 'Xs_ID'
    

    # save WSE and flow of all the CS as CSV in the "1D_Unsteady_Results" folder
    WSE.to_csv(Folder1 + "WSE of "+ ProjectName +".csv")
    flow.to_csv(Folder1 + "Flow of "+ ProjectName +".csv")
    VC.to_csv(Folder1 + "Channel velocity of "+ ProjectName +".csv")
    VT.to_csv(Folder1 + "Cross section velocity of "+ ProjectName +".csv")

    # close HEC-RAS Project and quit
    hec.Project_Close()
    hec.QuitRas()

    # delete HEC-RAS controller
    del hec

    print("HEC-RAS 1D unsteady flow results for "+ProjectName+" are done!")


# the following condition checks whether we are running as a script, in which case run the test code

if __name__ == '__main__':

    Py2HecRas_1DU_Flow(ProjectName="WabashAndTributarie")

    Py2HecRas_1DU_Plan(g=1,u=1,
                       StartDateTime="2008-01-21 00:00",
                       EndDateTime="2008-02-21 00:00",
                       ProjectName="WabashAndTributarie")

    Py2HecRas_1DU_Run(ProjectName="WabashAndTributarie")
    
