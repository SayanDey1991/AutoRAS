# -*- coding: utf-8 -*-
"""
Created on Tue Mar  7 10:45:17 2021

@author: Sayan Dey

Provides functions for automating input/output HEC-RAS 1D steady state models

"""

import os, parserasgeo as prg, rascontrol as rc
import win32com.client
import logging
from zipfile import ZipFile
import pandas as pd

import qgis
from qgis.core import *
from PyQt5.QtCore import *


def RunRASprj(RAS_prj_file):
    """
    Runs the current plan associated with HEC-RAS .prj file and returns associated geometry file 
    if run does not throw an error
    
    Parameters
    ----------
    RAS_prj_file : string (filepath)
        

    Returns
    -------
    geometry file name : String

    """
    
    hec = win32com.client.Dispatch("RAS507.HECRASController")
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
            return(hec.CurrentGeomFile())
        else:
            logging.error("Error in running current plan") 
            return("Error")
    finally: 
        hec.QuitRas()
        
def unzip_all(folder_name, unzip_filelist):
    """
    Unzips all .zip folders in a given folder, including those inside zipped folders    

    Parameters
    ----------
    folder_name : TYPE
        DESCRIPTION.
    unzip_filelist : TYPE
        DESCRIPTION.

    Returns
    -------
    ctr : TYPE
        DESCRIPTION.
    unzip_filelist : TYPE
        DESCRIPTION.

    """
    ctr = 0
    zip_file_ctr, unzip_list = unzip_all(folder_name,unzip_filelist)
    while zip_file_ctr > 0:
        logging.info("Total file unzipped: " + str(zip_file_ctr))  
        zip_file_ctr, unzip_list = unzip_all(folder_name,unzip_filelist)
        for root, dirs, files in os.walk(folder_name):
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
        epsg_code = [item.strip().split('=')[1] for item in RAS_geo_obj.geo_list if type(item)== str if "GIS Projection Zone" in item][0]
        
        # CREATE SHAPEFILES
        
        layerFields = qgis.core.QgsFields()
        layerFields.append(qgis.core.QgsField('Xs_ID', QVariant.Double))
        layerFields.append(qgis.core.QgsField('River', QVariant.String))
        layerFields.append(qgis.core.QgsField('Reach', QVariant.String))
        Xs_file_writer = qgis.core.QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
        
        layerFields_CL = qgis.core.QgsFields()
        layerFields_CL.append(qgis.core.QgsField('River', QVariant.String))
        layerFields_CL.append(qgis.core.QgsField('Reach', QVariant.String))
        CL_file_writer = qgis.core.QgsVectorFileWriter(out_file_CL, 'UTF-8', layerFields_CL, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
            
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
    except:
        logging.error("Error in extracting geometry")
        
def RASExtractWSE(geo_shp_file, profile_list, xs_list):
    """
    

    Parameters
    ----------
    geo_shp_file : TYPE
        DESCRIPTION.
    profile_list : TYPE
        DESCRIPTION.
    xs_list : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    
    layerFields = qgis.core.QgsFields()
    layerFields.append(qgis.core.QgsField('Xs_ID', QVariant.Double))
    layerFields.append(qgis.core.QgsField('River', QVariant.String))
    layerFields.append(qgis.core.QgsField('Reach', QVariant.String))
    Xs_file_writer = qgis.core.QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
    
    cross_sections = [Xs.station for Xs in RAS_geo_obj.get_cross_sections()]    
    wsels = [rc.get_xs(xs).value(profile, rascontrol.WSEL) for xs in cross_sections]
    fin_df = pd.DataFrame([cross_sections,wsels])
    fin_df.to_csv(os.path.join(folder_name,"wse.csv"))