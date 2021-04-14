# -*- coding: utf-8 -*-
"""
Created on Tue Mar  7 10:45:17 2021

@author: Sayan Dey

Provides functions for automating input/output HEC-RAS 1D steady state models

"""

import os, parserasgeo as prg, rascontrol
import win32com.client
import logging
from zipfile import ZipFile
import pandas as pd

import qgis
from qgis.core import *
from PyQt5.QtCore import *

RAS_version_string = "507"


def RunRASprj(RAS_prj_file):
    """
    Runs the current plan associated with HEC-RAS .prj file and returns associated plan and geometry file 
    if run does not throw an error
    
    Parameters
    ----------
    RAS_prj_file : string (filepath)
        

    Returns
    -------
    geometry file name : String
    
    plan file name: String

    """
    
    hec = win32com.client.Dispatch("RAS" + RAS_version_string + ".HECRASController")
    try:
        logging.info("Loading RAS Project")         
        hec.Project_Open(RAS_prj_file) 
        logging.info("Computing Current Plan")   
        hec.Compute_CurrentPlan(None,None,True)
    except:  
        logging.error("Current RAS plan failed to execute")
        return("Error")
    else:
        run_status = hec.Compute_Complete()
        logging.info("Run_status: " + str(run_status))    
        if run_status:
            return([RAS_prj_file, hec.CurrentGeomFile(), hec.CurrentPlanFile()])
        else:
            logging.error("Error in running current plan") 
            return("Error")
    finally: 
        hec.QuitRas()
        
def LocateRASprj(input_folder,output_file):
    """
    locates HEC-RAS prj files

    Parameters
    ----------
    input_folder : filepath (string)
        folder where all unzipped files are located.
    output_file: filepath (string) to output csv
        file which stores list of prj, geo and plan files

    Returns
    -------
    None

    """        
    RAS_file_df = pd.DataFrame(columns=["prj","geo","plan"])
    for root, dirs, files in os.walk(input_folder):
        for name in files:
            if name.endswith(".prj"):
                logging.info("Processing: " + root)
                print("Processing: " + root)
                result = RunRASprj(os.path.join(root, name))
                if result != "Error":
                    logging.info("Storing RAS project info")
                    result_series = pd.Series(result, index = RAS_file_df.columns)
                    RAS_file_df = RAS_file_df.append(result_series, ignore_index=True) 
    RAS_file_df.to_csv(output_file)
                    
                    

        
def _unzip_files(input_folder,unzip_filelist):
    """
    Parameters
    ----------
    folder_name : filepath (string)
        folder containing the zipped HEC-RAS files
    unzip_filelist : list
        list of zipped files processed

    Returns
    -------
    ctr : Integer
        Number of zip files processed in current run
    unzip_file_list : List
        list of all zipped files processed 

    """
    
    ctr = 0
    for root, dirs, files in os.walk(input_folder):
        for name in files:
            cur_file = os.path.join(root, name)
            if name.endswith(".zip") and cur_file not in unzip_filelist:
                try:
                    with ZipFile(cur_file, 'r') as zip_ref:
                        zip_ref.extractall(root + "//" + name[:-4])
                        ctr = ctr+1
                        unzip_filelist.append(cur_file)
                except:  
                    logging.error("Cannot unzip: " + cur_file)
    return ctr, unzip_filelist

def unzip_all(folder_name):
    """
    Unzips all .zip folders in a given folder, including those inside zipped folders    

    Parameters
    ----------
    folder_name : filepath (string)
        folder containing the zipped HEC-RAS files

    Returns
    -------
    NONE

    """
    logging.info("Begin Unzipping")   
    unzip_list = []   
    total_zip_file_ctr = 0
    zip_file_ctr, unzip_list = _unzip_files(folder_name, unzip_list)
    total_zip_file_ctr = total_zip_file_ctr + zip_file_ctr
    while zip_file_ctr > 0:
        logging.info("New files unzipped: " + str(zip_file_ctr))  
        zip_file_ctr, unzip_list = _unzip_files(folder_name,unzip_list)
        
    logging.info("Unzipping Finished")   
    logging.info("Total files unzipped: " + str(total_zip_file_ctr))
    
    
def RASGeo2gdf(RAS_geo_file):
    """
    Parameters
    ----------
    RAS_geo_file : String (filepath) 
        filepath to RAS geo file.

    Returns
    -------
    fin_XS_gdf : geodataframe
        geodataframe containing cross-sections with x,y,z
    fin_CL_gdf : geodataframe

    """   
    pass

def RASExtractCRS(RAS_geo_file):
    """
    returns the EPSG code of geo file if it exists else return None
    
    Parameters
    ----------
    RAS_geo_file : file path to RAS geometry file

    Returns
    -------
    String : EPSG Code
    
    """
    try:
        RAS_geo_obj = prg.ParseRASGeo(RAS_geo_file)
        epsg_code = [item.strip().split('=')[1] for item in RAS_geo_obj.geo_list if type(item)== str if "GIS Projection Zone" in item][0]
        return epsg_code
    except:
        logging.error("Error in extracting CRS of geomtry file")
        return None    

                    
def RASGeo2Shp(RAS_geo_file, output_folder):
    """
    extracts centerline and cross-sections from HEC-RAS geometry file to shapefile

    Parameters
    ----------
    RAS_geo_file : TYPE
        DESCRIPTION.
    output_folder : TYPE
        DESCRIPTION.

    Returns
    -------
    true if operation was successful else false
    Two shapefiles, one containing centerlines and another containing cross-sections

    """
    try:
        g_filename = os.path.basename(RAS_geo_file).split(".")[0]
        out_file_Xs = os.path.join(output_folder,g_filename + "_XS.shp")
        out_file_CL = os.path.join(output_folder,g_filename + "_CL.shp")
        ctr=1
        while(os.path.exists(out_file_Xs)):
            logging.warning("Output Xs file already exists: renaming file")
            out_file_Xs = os.path.join(output_folder,g_filename + str(ctr) + "_XS.shp")
            ctr=ctr+1
        ctr=1
        while(os.path.exists(out_file_CL)):
            logging.warning("Output CL file already exists: renaming file")
            out_file_CL = os.path.join(output_folder,g_filename + str(ctr) + "_CL.shp")
            ctr=ctr+1         
            
        
        # LOAD RAS GEOMTERY AND GET CRS
        RAS_geo_obj = prg.ParseRASGeo(RAS_geo_file)
        logging.info("Extracting projection system")
        epsg_code = RASExtractCRS(RAS_geo_file)
        
        # CREATE SHAPEFILES
        
        layerFields = QgsFields()
        layerFields.append(QgsField('Xs_ID', QVariant.Double))
        layerFields.append(QgsField('River', QVariant.String, len=200))
        layerFields.append(QgsField('Reach', QVariant.String, len=200))
        Xs_file_writer = QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
        
        layerFields_CL = QgsFields()
        layerFields_CL.append(QgsField('River', QVariant.String, len=200))
        layerFields_CL.append(QgsField('Reach', QVariant.String, len=200))
        CL_file_writer = QgsVectorFileWriter(out_file_CL, 'UTF-8', layerFields_CL, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
            
        # LOAD XS in CREATED SHAPEFILE
        
        for Xs in RAS_geo_obj.get_cross_sections():
            logging.info("Processing cross-section: " + str(Xs.header.station.value) + " River: " + Xs.river + " Reach: " + Xs.reach)
            # make polyline from cutline
            cutline_feat = QgsFeature()
            cutline_x = [float(x[0]) for x in Xs.cutline.points]
            cutline_y = [float(x[1]) for x in Xs.cutline.points]
            cutline_point_list = [QgsPoint(cutline_x[i],cutline_y[i]) for i in range(len(cutline_x))]
            cutline_feat.setGeometry(QgsGeometry.fromPolyline(cutline_point_list))
            
            # Add 3D points to cutline
            Xs_pt_list = []
            #get first pt separately
            Xs_pt = QgsPoint(cutline_x[0],cutline_y[0])
            Xs_pt.addZValue()
            Xs_pt.setZ(Xs.sta_elev.points[0][1])
            Xs_pt.addMValue()
            Xs_pt.setM(Xs.sta_elev.points[0][0])
            Xs_pt_list.append(Xs_pt)
            # loop through rest of the points
            for sta_elev in Xs.sta_elev.points[1:-1]:
                Xs_pt = QgsPoint(cutline_feat.geometry().interpolate(sta_elev[0]).asPoint())
                Xs_pt.addZValue()
                Xs_pt.setZ(sta_elev[1])
                Xs_pt.addMValue()
                Xs_pt.setM(sta_elev[0])
                Xs_pt_list.append(Xs_pt)
                # print(sta_elev)
            
            #get last pt separately
            Xs_pt = QgsPoint(cutline_x[-1],cutline_y[-1])
            Xs_pt.addZValue()
            Xs_pt.setZ(Xs.sta_elev.points[-1][1])
            Xs_pt.addMValue()
            Xs_pt.setM(Xs.sta_elev.points[-1][0])
            Xs_pt_list.append(Xs_pt)   
            
            Xs_feat = QgsFeature()
            Xs_feat.setGeometry(QgsGeometry.fromPolyline(Xs_pt_list))
            Xs_feat.setAttributes([Xs.header.station.value,Xs.river, Xs.reach])      
            Xs_file_writer.addFeature(Xs_feat) 
                
        # LOAD REACHES INTO CL SHAPEFILE
        
        for cur_CL in RAS_geo_obj.get_reaches():    
            CL_feat = QgsFeature()
            CL_x = [float(x[0]) for x in cur_CL.geo.points]
            CL_y = [float(x[1]) for x in cur_CL.geo.points]
            CL_point_list = [QgsPoint(CL_x[i],CL_y[i]) for i in range(len(CL_x))]
            CL_feat.setGeometry(QgsGeometry.fromPolyline(CL_point_list))
            CL_feat.setAttributes([cur_CL.header.river_name, cur_CL.header.reach_name])  
            CL_file_writer.addFeature(CL_feat) 
        
        del(Xs_file_writer)   
        del(CL_file_writer)
        logging.info("Extraction complete for: " + RAS_geo_file.split("\\")[-1])  
        return True
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logging.error("Error in extracting geometry:" + exc_tb.tb_lineno)
        return False
        
def RASExtractGeo(file_csv, output_folder):
    """
    reads a list of geo files from csv file and calls RASGeo2Shp to extarct CL and XS
    it then calls RASBoundingPoly to create bounding poly

    Parameters
    ----------
    file_list : csv file containing column "geo" of geo files
        
    output_folder: filepath to folder where all outputs are to be written

    Returns
    -------
    None.

    """
    df = pd.read_csv(file_csv)
    for geo_file in df["geo"]:
        result1 = RASGeo2Shp(geo_file,output_folder)
        result2 = RASBoundingPoly_Simple(geo_file,output_folder)


def RASBoundingPoly_Simple(RAS_geo_file,output_folder):
    """
    Creates a bounding polygon around the XS and saves to shp
    Works for single stream reaches only

    Returns
    -------
    Writes Shapefile containing bounding poly
    True if successful
    

    """
    try:
        
        g_filename = os.path.basename(RAS_geo_file).split(".")[0]
        out_file_BP = os.path.join(output_folder,g_filename + "_BP.shp")
        ctr=1
        while(os.path.exists(out_file_BP)):
            logging.warning("Output BP file already exists: renaming file")
            out_file_BP = os.path.join(output_folder,g_filename + str(ctr) + "_BP.shp")
            ctr=ctr+1
        
        # LOAD RAS GEOMTERY AND GET CRS
        RAS_geo_obj = prg.ParseRASGeo(RAS_geo_file)
        logging.info("Extracting projection system")
        epsg_code = RASExtractCRS(RAS_geo_file)
        
        #get sorted XS list
        xs_list = [(Xs,Xs.header.station.value) for Xs in RAS_geo_obj.get_cross_sections()]
        xs_list.sort(key=lambda x: x[1], reverse=True)
        
        bp_pts = [QgsPointXY(float(x[0]),float(x[1])) for x in xs_list[0][0].cutline.points] #first xs pts
        strt_pts = []
        end_pts = []
        
        for tup in xs_list[1:-1]:
            Xs = tup[0]
            strt_pts.append(QgsPointXY(float(Xs.cutline.points[0][0]),float(Xs.cutline.points[0][1]))) 
            end_pts.append(QgsPointXY(float(Xs.cutline.points[-1][0]),float(Xs.cutline.points[-1][1])))
            
        bp_pts.extend(end_pts)
        last_xs_pts = [QgsPointXY(float(x[0]),float(x[1])) for x in xs_list[-1][0].cutline.points]
        last_xs_pts.reverse()
        bp_pts.extend(last_xs_pts)
        strt_pts.reverse()
        bp_pts.extend(strt_pts)
        
        # save polygon in shapefile
        layerFields = QgsFields()
        layerFields.append(QgsField('BP_ID', QVariant.Double))
        
        Xs_file_writer = QgsVectorFileWriter(out_file_BP, 'UTF-8', layerFields, QgsWkbTypes.Polygon, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
        Xs_feat = QgsFeature()
        Xs_feat.setGeometry(QgsGeometry.fromPolygonXY([bp_pts]))
        Xs_feat.setAttributes([0])      # set this later 
        Xs_file_writer.addFeature(Xs_feat) 
        del(Xs_file_writer)
        return True
    
    except:
        logging.error("Error in creating bounding polygon")
        return False
        
    

def RASExtractWSE(RAS_prj_file,output_file):
    """
    extracts wse for all XS for all flows in current plan and writes to csv file

    Parameters
    ----------
    RAS_prj_file : filepath (String)
        filepath to RAS .prj file.
    output_file : filepath (String)
        filepth to a csv file where result to be written 
        (if file already exists, it will be rewritten).

    Returns
    -------
    None.

    """
    
    # layerFields = qgis.core.QgsFields()
    # layerFields.append(qgis.core.QgsField('Xs_ID', QVariant.Double))
    # layerFields.append(qgis.core.QgsField('River', QVariant.String))
    # layerFields.append(qgis.core.QgsField('Reach', QVariant.String))
    # Xs_file_writer = qgis.core.QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
    rc = rascontrol.RasController(version=RAS_version_string)
    rc.open_project(RAS_prj_file)
    
    cross_sections = rc.simple_xs_list()
    profile_list = rc.get_profiles()    
    wsels = [[rc.get_xs(xs.xs_id,xs.river,xs.reach).value(profile, rascontrol.WSEL)
              for profile in profile_list]             
              for xs in cross_sections]
    
    #create dataframe 
    column_list = [profile.name for profile in profile_list]
    fin_df = pd.DataFrame(wsels, columns=column_list)
    fin_df["River"] = [xs.river for xs in cross_sections]
    fin_df["Reach"] = [xs.reach for xs in cross_sections]
    fin_df["Xs_ID"] = [xs.xs_id for xs in cross_sections]  
    
    # write to file 
    fin_df.to_csv(output_file)
    
    # quit ras
    rc.close()
    
# def XS3D2Voronoi(Xs_shp_file):
#     try:
#         Xs_lyr = QgsVectorLayer(Xs_shp_file,"" ,"ogr")
        
        
#         return True        
#     except Exception as e:
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         logging.error("Error in triangulation:" + exc_tb.tb_lineno)
#         return False
        
        
    
    
    
    