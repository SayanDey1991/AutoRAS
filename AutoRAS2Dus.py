# -*- coding: utf-8 -*-
"""
Created on Mon Mar 15 14:26 2021
@author: Tianle Xu
Provides functions for automating input/output HEC-RAS 2D unsteady state models
"""

import math
import h5py
import random
import numpy as np
import pandas as pd
import utils
import matplotlib.pyplot as plt
from shapely.geometry import MultiPoint, Point, Polygon, mapping
import fiona
from fiona import collection
from fiona.crs import from_epsg

def get_wse(input_plan_file, input_geometry_file, sample_points, coordinate_system):
    """
    extracts water surface elevation (wse) data from geometry file based on some sample points within 2D interior area 
    
    Parameters
    ----------
    input_plan_file : string(filepath of the plan file)
    input_geometry_file: string(filepath of the geometry file)
    sample_points: list(coordinate of sample points)
    coordinate_system: string(from_epsg(...))
        
    Returns
    -------
    data/random_points.shp : a csv file with wse data of given points
    """
    # read plan hdf file 
    f = h5py.File(input_plan_file, 'r')
    # extract the data of cells center coordinate
    c = f['/Geometry/2D Flow Areas/2D Interior Area/Cells Center Coordinate']
    c = np.array(c)
    # store x-coordinate and y-coordinate data in saparate lists
    x, y = c.T

    # extract the data of water surface elevation
    wse = f['/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/2D Interior Area/Water Surface']
    wse = np.array(wse)

    # extract the data of time date stamp
    td = f['/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time Date Stamp']
    # trsnform data type from bytestring to string
    td = np.char.decode(td)

    # read geometry hdf file
    f1 = h5py.File(input_geometry_file, 'r')
    # extract the perimeter data of the 2D interior area
    perimeter = f1['/Geometry/2D Flow Areas/2D Interior Area/Perimeter']
    perimeter = np.array(perimeter)
    # create the boundary polygon
    perimeter = Polygon(perimeter)

    pt_valid = []
    for point in sample_points:
        point = Point(point)
        if not perimeter.contains(point): # check if the point is within the 2D interior region
            print('The point ('+ str(point.x)+','+ str(point.y) + ') is out of the 2D interior region')
            continue
        else:
            pt_valid.append([point.x, point.y])
    # print all valid points 
    print('Coordinate of valid points:')
    print(pt_valid)

    # Create the random-point shapefile
    utils.create_shp(pt_valid, 'data/random_points.shp', coordinate_system) #from_epsg(102673)

    # Set the parameters for IDW method
    r = 150 # block radius
    p = 2 # p-value
    for k in pt_valid:
        xz = k[0]
        yz = k[1]
        elev = []
        # predict elevation data
        for i in range(len(wse)):
            z = wse[i]
            elev.append(utils.idw_rblock(xz,yz,r,p,x,y,z))
        elev = np.array(elev) # store the predicted data of wse in a list
        # combine the wse data of the point and time date stamp data
        td = np.column_stack((td, elev))

    # store the data in a pandas dataframe
    df = pd.DataFrame(td)
    df[1] = pd.to_numeric(df[1])
    # print(df.head())
    # save to csv file
    df.rename(columns={ df.columns[0]: "Time" }, inplace = True) # rename the first column as 'Time'
    df.to_csv('data/wse_point.csv', index=False)

def idw_rblock(xz,yz,r,p,x,y,z):
    """
    IDW interpolation method 
    
    Parameters
    ----------
    xz: x-coordinate of unsampled point
    yz: y-coordinate of unsampled point
    r: search radius
    p: power value of IDW 
    x: x-coordinate of the sample point
    y: y-coordinate of the sample point
    z: z-coordinate of the sample point
        
    Returns
    -------
    z_idw : estimated z value of the unmeasured point
    """
    x_block=[]
    y_block=[]
    z_block=[]
    xr_min=xz-r
    xr_max=xz+r
    yr_min=yz-r
    yr_max=yz+r
    for i in range(len(x)):
        # condition to test if a point is within the block
        if ((x[i]>=xr_min and x[i]<=xr_max) and (y[i]>=yr_min and y[i]<=yr_max)):
            x_block.append(x[i])
            y_block.append(y[i])
            z_block.append(z[i])
            
    #calculate weight based on distance and p value
    w_list=[]
    for j in range(len(x_block)):
        d=math.sqrt((xz-x_block[j])**2+(yz-y_block[j])**2) 
        if d>0:
            w=1/(d**p)
            w_list.append(w)
            z0=0
        else:
            w_list.append(0) #if meet this condition, it means d<=0, weight is set to 0
    
    #check if there is 0 in weight list
    w_check=0 in w_list
    if w_check==True:
        idx=w_list.index(0) # find index for weight=0
        z_idw=z_block[idx] # set the value to the current sample value
    else:
        wt=np.transpose(w_list)
        z_idw=np.dot(z_block,wt)/sum(w_list) # idw calculation using dot product
    return z_idw

# function to create shapefile
def create_shp(coordinate, output_file_name, crs):
    """
    create a point shapefile
    
    Parameters
    ----------
    coordinate: coordinate of points
    output_file_name: string(output file name)
    crs: from_epsg(...) (coordinate system)
        
    Returns
    -------
    point shapefile : shapefile of points
    """
    # write the data into shapefile 
    schema = { 'geometry': 'Point', 'properties': { 'Long': 'float', 'Lat': 'float' } }
    with collection(output, "w", "ESRI Shapefile", schema, crs) as output:
        for i in coordinate:
            point = Point(float(i[0]), float(i[1]))
            output.write({'properties': {
                            'Long': i[0],
                            'Lat': i[1]   # write longitude and latitude to the attribute table
                        },
                        'geometry': mapping(point)
                    })