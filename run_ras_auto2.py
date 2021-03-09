# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 10:26:46 2020

@author: Sayan Dey
"""

import qgis
from qgis.core import *
from PyQt5.QtCore import *
import os
import parserasgeo as prg
import rascontrol
import win32com.client
import logging
#from zipfile import ZipFile
#from qgis.utils import iface

# USER INPUTS
RAS_prj_file = r"C:\Projects\UFOKN\RAS_Automation\CodeInput\RAS_1D_Wab_3Trib\WabashAndTributarie.prj"
output_folder = r"C:\Projects\UFOKN\RAS_Automation\CodeOutput"
log_filename = "log1.txt"




# #____________________________________________________________________________________________________
# # USER DEFINED FUNCTIONS

# def RASGeoWSE2Shp(RAS_geo_file, output_folder, rc):
    
#         g_filename = os.path.basename(RAS_geo_file).split(".")[0]
#         out_file_Xs = os.path.join(output_folder,g_filename + "_XS.shp")
#         #out_file_CL = os.path.join(output_folder,g_filename + "_CL.shp")
#         ctr=1
#         while(os.path.exists(out_file_Xs)):
#             logging.warning("Output Xs file already exists: renaming file")
#             out_file_Xs = os.path.join(output_folder,g_filename + str(ctr) + "_XS.shp")
#             ctr=ctr+1
#         # ctr=1
#         # while(os.path.exists(out_file_CL)):
#         #     logging.warning("Output CL file already exists: renaming file")
#         #     out_file_CL = os.path.join(output_folder,g_filename + str(ctr) + "_CL.shp")
#         #     ctr=ctr+1         
            
        
#         # LOAD RAS GEOMTERY AND GET CRS
#         RAS_geo_obj = prg.ParseRASGeo(RAS_geo_file)
#         logging.info("Extracting projection system")
#         epsg_code = [item.strip().split('=')[1] for item in RAS_geo_obj.geo_list if type(item)== str if "GIS Projection Zone" in item][0]
        
#         # CREATE SHAPEFILES
        
#         layerFields = qgis.core.QgsFields()
#         layerFields.append(qgis.core.QgsField('Xs_ID', QVariant.Double))
#         layerFields.append(qgis.core.QgsField('River', QVariant.String, len = 200))
#         layerFields.append(qgis.core.QgsField('Reach', QVariant.String, len = 200))
#         Xs_file_writer = qgis.core.QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
        
#         # layerFields_CL = qgis.core.QgsFields()
#         # layerFields_CL.append(qgis.core.QgsField('River', QVariant.String))
#         # layerFields_CL.append(qgis.core.QgsField('Reach', QVariant.String))
#         # CL_file_writer = qgis.core.QgsVectorFileWriter(out_file_CL, 'UTF-8', layerFields_CL, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
            
#         # LOAD XS AND WSEL in CREATED SHAPEFILE
        
#         profile_list = rc.get_profiles()
        
#         for Xs in RAS_geo_obj.get_cross_sections():
#             logging.info("Processing cross-section: " + str(Xs.header.station.value) + " River: " + Xs.river + " Reach: " + Xs.reach)
#             # make polyline from cutline
#             cutline_feat = QgsFeature()
#             cutline_x = [float(x[0]) for x in Xs.cutline.points]
#             cutline_y = [float(x[1]) for x in Xs.cutline.points]
#             cutline_point_list = [QgsPoint(cutline_x[i],cutline_y[i]) for i in range(len(cutline_x))]
#             cutline_feat.setGeometry(QgsGeometry.fromPolyline(cutline_point_list))
            
#             # Add 3D points to cutline
#             Xs_pt_list = []
#             #get first pt separately
#             Xs_pt = QgsPoint(cutline_x[0],cutline_y[0])
#             Xs_pt.addZValue()
#             Xs_pt.setZ(Xs.sta_elev.points[0][1])
#             Xs_pt.addMValue()
#             Xs_pt.setM(Xs.sta_elev.points[0][0])
#             Xs_pt_list.append(Xs_pt)
#             # loop through rest of the points
#             for sta_elev in Xs.sta_elev.points[1:-1]:
#                 Xs_pt = QgsPoint(cutline_feat.geometry().interpolate(sta_elev[0]).asPoint())
#                 Xs_pt.addZValue()
#                 Xs_pt.setZ(sta_elev[1])
#                 Xs_pt.addMValue()
#                 Xs_pt.setM(sta_elev[0])
#                 Xs_pt_list.append(Xs_pt)
#                 # print(sta_elev)
            
#             #get last pt separately
#             Xs_pt = QgsPoint(cutline_x[-1],cutline_y[-1])
#             Xs_pt.addZValue()
#             Xs_pt.setZ(Xs.sta_elev.points[-1][1])
#             Xs_pt.addMValue()
#             Xs_pt.setM(Xs.sta_elev.points[-1][0])
#             Xs_pt_list.append(Xs_pt)   
            
#             Xs_feat = QgsFeature()
#             Xs_feat.setGeometry(QgsGeometry.fromPolyline(Xs_pt_list))
#             attribute_value_list = [Xs.header.station.value,Xs.river, Xs.reach]
#             rc_xs  = rc.get_xs(Xs.header.station.value, Xs.river, Xs.reach)
#             for profile in profile_list:
#                 attribute_value_list.append(round(rc_xs.value(profile, rascontrol.WSEL),2))
#             Xs_feat.setAttributes(attribute_value_list)      
#             Xs_file_writer.addFeature(Xs_feat) 
                
#         # LOAD REACHES INTO CL SHAPEFILE
        
#         # for cur_CL in RAS_geo_obj.get_reaches():    
#         #     CL_feat = QgsFeature()
#         #     CL_x = [float(x[0]) for x in cur_CL.geo.points]
#         #     CL_y = [float(x[1]) for x in cur_CL.geo.points]
#         #     CL_point_list = [QgsPoint(CL_x[i],CL_y[i]) for i in range(len(CL_x))]
#         #     CL_feat.setGeometry(QgsGeometry.fromPolyline(CL_point_list))
#         #     CL_feat.setAttributes([cur_CL.header.river_name, cur_CL.header.reach_name])  
#         #     CL_file_writer.addFeature(CL_feat) 
        
#         del(Xs_file_writer)  
#         #return out_file_Xs
#         # del(CL_file_writer)
#         logging.info("Extraction complete for: " + RAS_geo_file.split("\\")[-1])  
        

# def RASExtractWSE(geo_shp_file, profile_list, xs_list):
#     pass
#     # layerFields = qgis.core.QgsFields()
#     # layerFields.append(qgis.core.QgsField('Xs_ID', QVariant.Double))
#     # layerFields.append(qgis.core.QgsField('River', QVariant.String))
#     # layerFields.append(qgis.core.QgsField('Reach', QVariant.String))
#     # Xs_file_writer = qgis.core.QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')




#____________________________________________________________________________________________________
# MAIN CODE
    
# log_file = os.path.join(output_folder,log_filename)
# logging.basicConfig(filename=log_file,
#                             filemode='a',
#                             format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
#                             datefmt='%H:%M:%S',
#                             level=logging.info)
# logging.info("Beginning Execution")


rc = rascontrol.RasController(version='507')
rc.open_project(RAS_prj_file)
run_status, run_message = rc.run_current_plan()
if run_status:
    # rascontrol doesnot return geo file so temporary roundabout
    hec = win32com.client.Dispatch("RAS507.HECRASController")
    hec.Project_Open(RAS_prj_file)
    RAS_geo_file = hec.CurrentGeomFile()
    profile_list = rc.get_profiles()
    # hec.close()
        
    # RASGeoWSE2Shp(RAS_geo_file, output_folder, rc)
    g_filename = os.path.basename(RAS_geo_file).split(".")[0]
    out_file_Xs = os.path.join(output_folder,g_filename + "_XS.shp")
    #out_file_CL = os.path.join(output_folder,g_filename + "_CL.shp")
    ctr=1
    while(os.path.exists(out_file_Xs)):
        logging.warning("Output Xs file already exists: renaming file")
        out_file_Xs = os.path.join(output_folder,g_filename + str(ctr) + "_XS.shp")
        ctr=ctr+1
   
        
    
    # LOAD RAS GEOMTERY AND GET CRS
    RAS_geo_obj = prg.ParseRASGeo(RAS_geo_file)
    logging.info("Extracting projection system")
    epsg_code = [item.strip().split('=')[1] for item in RAS_geo_obj.geo_list if type(item)== str if "GIS Projection Zone" in item][0]
    
    # CREATE SHAPEFILES
    
    layerFields = qgis.core.QgsFields()
    layerFields.append(qgis.core.QgsField('Xs_ID', QVariant.Double))
    layerFields.append(qgis.core.QgsField('River', QVariant.String, len = 200))
    layerFields.append(qgis.core.QgsField('Reach', QVariant.String, len = 200))
    for profile in profile_list:
        layerFields.append(qgis.core.QgsField(profile.name, QVariant.Double))
    Xs_file_writer = qgis.core.QgsVectorFileWriter(out_file_Xs, 'UTF-8', layerFields, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
    
    # layerFields_CL = qgis.core.QgsFields()
    # layerFields_CL.append(qgis.core.QgsField('River', QVariant.String))
    # layerFields_CL.append(qgis.core.QgsField('Reach', QVariant.String))
    # CL_file_writer = qgis.core.QgsVectorFileWriter(out_file_CL, 'UTF-8', layerFields_CL, QgsWkbTypes.LineStringZM, QgsCoordinateReferenceSystem('EPSG:' + epsg_code), 'ESRI Shapefile')
        
    # LOAD XS AND WSEL in CREATED SHAPEFILE
    
    
    
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
        attribute_value_list = [Xs.header.station.value,Xs.river, Xs.reach]
        rc_xs  = rc.get_xs(Xs.header.station.id, Xs.river, Xs.reach)
        for profile in profile_list:
            attribute_value_list.append(round(rc_xs.value(profile, rascontrol.WSEL),2))
        Xs_feat.setAttributes(attribute_value_list)      
        Xs_file_writer.addFeature(Xs_feat) 
            
    # LOAD REACHES INTO CL SHAPEFILE
    
    # for cur_CL in RAS_geo_obj.get_reaches():    
    #     CL_feat = QgsFeature()
    #     CL_x = [float(x[0]) for x in cur_CL.geo.points]
    #     CL_y = [float(x[1]) for x in cur_CL.geo.points]
    #     CL_point_list = [QgsPoint(CL_x[i],CL_y[i]) for i in range(len(CL_x))]
    #     CL_feat.setGeometry(QgsGeometry.fromPolyline(CL_point_list))
    #     CL_feat.setAttributes([cur_CL.header.river_name, cur_CL.header.reach_name])  
    #     CL_file_writer.addFeature(CL_feat) 
    
    del(Xs_file_writer)  
    #return out_file_Xs
    # del(CL_file_writer)
    logging.info("Extraction complete for: " + RAS_geo_file.split("\\")[-1])  


    
else:
    print("Error in running current plan: Program Terminated")
# profile = rc.get_profiles()[0]
# xs_list = rc.simple_xs_list()
# cross_sections = [100, 200, 300]  
# wsels = [rc.get_xs(xs).value(profile, rascontrol.WSEL) for xs in cross_sections]

# [rc.get_xs(cur_xs.xs_id, cur_xs.river, cur_xs.reach).value(profile,rascontrol.WSEL) for profile in rc.get_profiles()]
# [rc.get_xs(cur_xs.xs_id, cur_xs.river, cur_xs.reach).value(profile,rascontrol.WSEL) for cur_xs in xs_list]
    


rc.close()






















