'''This program takes an input line shapefile and creates a set of lines of specified width at a given spacing along the line.

Created by Karthik Aditya on 20.07.20'''

import math, sys, os, glob
from osgeo import ogr, osr
import shapely.geometry as shpgeo
import json

def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [shpgeo.LineString(line), None]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pdist = line.project(shpgeo.Point(p))
        if pdist == distance:
            return [
                shpgeo.LineString(coords[:i+1]),
                shpgeo.LineString(coords[i:])]
        if pdist > distance:
            cp = line.interpolate(distance)
            return [
                shpgeo.LineString(coords[:i] + [(cp.x, cp.y)]),
                shpgeo.LineString([(cp.x, cp.y)] + coords[i:])]

def line_slice(line, slice_width):
    ''' Take an input shapefile and slice it into pieces based on a given width and maximum number of slices'''
    fid = ogr.Open(line)
    lyr = fid.GetLayer(0)
    shape = lyr.GetFeature(0)
    lstring = shpgeo.shape(json.loads(shape.ExportToJson())['geometry']) #Get the line shapefile as a WKT LineString
    fts = {}
    i = 0
    print('Input loaded...')
    while i < lstring.length:
        if i == 0:
            ft, newbase = cut(lstring, slice_width) #This gives ft of size 0-slice_width, and newbase of size slice_width-end
            fts[i] = ft.to_wkt()
        else:
            try:
                ft, newbase = cut(newbase, slice_width)
                fts[i] = ft.to_wkt()
            except:
                break

        i += ft.length
    return fts
    
def create_polygon(key, cd):   
    '''Create a rectangle polygon out of a given set of points'''
    ring = ogr.Geometry(ogr.wkbLinearRing)
    coords = cd[key]
    for c in coords:
        ring.AddPoint(float(c[0]), float(c[1]))

    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly.ExportToWkt()

def create_line(key, cd):   
    '''Create a line out of a given 2 of points'''
    line = ogr.Geometry(ogr.wkbLineString)
    coords = cd[key]
    for c in coords:
        line.AddPoint(float(c[0]), float(c[1]))

    return line.ExportToWkt()

def write_shapefile(out_shp, cd, cs):
    '''Write the results to a polygon shapefile, based on the 'cd' coordinate dictionary'''
    driver = ogr.GetDriverByName('Esri Shapefile')
    ds = driver.CreateDataSource(out_shp)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(cs) #Get the spatial reference from the input line
    layer = ds.CreateLayer('', srs, ogr.wkbLineString)
    layer.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
    defn = layer.GetLayerDefn()

    for key in cd.keys():
        feat = ogr.Feature(defn)
        feat.SetField('ID', key)
        geom = ogr.CreateGeometryFromWkt(create_line(key, cd))
        feat.SetGeometry(geom)
    
        layer.CreateFeature(feat)
        del feat, geom
    del ds, layer
 
def perp_pts(x, y, m, edge_length, edges):
    '''Create points perpendicular to the line segment at a set distance'''
    x0, y0, x1, y1 = edges
    if m == 0:
        #Flat edge cases
        if y0 == y1:
            y1 = y + edge_length
            y2 = y - edge_length
            x1 = x
            x2 = x
        if x0 == x1:
            y1 = y
            y2 = y
            x1 = x + edge_length
            x2 = x - edge_length
    else:
        #A line perpendicular to x-y will have slope (-1/m)
        m_perp = (-1/m)
        
        #Use vector math to get points along perpendicular line
        if m > 0:
            x1 = x + (edge_length / math.sqrt(1 + m_perp**2))
            y1 = y + ((edge_length * m_perp) / math.sqrt(1+m_perp**2))
            x2 = x - (edge_length / math.sqrt(1 + m_perp**2))
            y2 = y - ((edge_length * m_perp) / math.sqrt(1+m_perp**2))
        
        if m < 0:
            x1 = x - (edge_length / math.sqrt(1 + m_perp**2))
            y1 = y - ((edge_length * m_perp) / math.sqrt(1+m_perp**2))
            x2 = x + (edge_length / math.sqrt(1 + m_perp**2))
            y2 = y + ((edge_length * m_perp) / math.sqrt(1+m_perp**2))
            
    return x1, y1, x2, y2
 
def create_lines(line, slice_width, edge_length):
    '''Main function, takes input line and saves out output file'''
    #Slice the line into chunks...
    linedict = line_slice(line, slice_width)
    
    #Get first and last point on the line, use them to build the box
    corner_dict = {}
    for key in linedict.keys():
        l = linedict[key]
        x0, y0 = l.replace('LINESTRING (', '').replace(')', '').split(',')[0].split(' ')
        x1, y1 = l.replace('LINESTRING (', '').replace(')', '').split(',')[-1].split(' ')[1:]
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        #x0, y0, x1, y1  are the leftmost and rightmost vertices of the line segment you want to make a box around
        
        #Get the slope of the line
        m = (y1 - y0) / (x1 - x0)

        # #Get the bounding box using the slope of the line
        topx_l, topy_l, botx_l, boty_l = perp_pts(x0, y0, m, edge_length, [x0, y0, x1, y1])
        corner_dict[key] = [[topx_l, topy_l], [botx_l, boty_l]]

    return corner_dict

if __name__ == "__main__":
    """
    Create cross-section across every line in a line shapefile

    line: path to lin layer in shapefile across which cross-section have to be created
    slice_width: distance between cross-sections
    edge_length: length of each half of cross-section. Total length will be twice
    """

    line = sys.argv[1]
    output = sys.argv[2]        
    slice_width = float(sys.argv[3])
    edge_length = float(sys.argv[4])

    print('Input:', line, 'Output:', output, 'Width:', slice_width, 'Edge Length:', edge_length)

    fid = ogr.Open(line)
    cs = fid.GetLayer().GetSpatialRef().ExportToWkt() #Get the coordinate system from the input for the output

    #Clean up the shapefile if it already exists
    if os.path.exists(output):
        print('Deleting old shapefile...')
        for fid in glob.glob(output.split('.')[0] + '*'):
            os.remove(fid)

    write_shapefile(output, create_lines(line, slice_width, edge_length), cs)
    print('Data Written.')
