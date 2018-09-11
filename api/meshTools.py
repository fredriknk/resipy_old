# MESH TOOLS 
"""
Created on Wed May 30 10:19:09 2018, python 3.6.5
@author: jamyd91
Import a vtk file with an unstructured grid (triangular/quad elements) and 
creates a mesh object (with associated functions). The mesh object can have quad or
triangular elements. module has capacity to show meshes, inverted results, apply a function 
to mesh parameters. 

Classes: 
    mesh_obj
Functions: 
    tri_cent() - computes the centre point for a 2d triangular element
    vtk_import() - imports a triangular / quad unstructured grid from a vtk file
    readR2_resdat () - reads resistivity values from a R2 file. 
    quad_mesh () - creates a quadrilateral mesh given electrode x and y coordinates 
                 (returns info needed for R2in) 
    tri_mesh () - calls gmshWrap and interfaces with gmsh.exe to make a trianglur mesh

Dependencies: 
    numpy (conda lib)
    matplotlib (conda lib)
    scipy (conda lib)
    gmshWrap(pyR2 api module)
    python3 standard libaries
Nb: Module has a heavy dependence on numpy and matplotlib packages
"""
#import standard python packages
import tkinter as tk
from tkinter import filedialog
import os, platform, warnings
from subprocess import PIPE, Popen, call
import time
#import anaconda default libraries
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap
import matplotlib.tri as tri
#import R2gui API package 
#if __name__ =="__main__" or __name__=="meshTools":
#    import gmshWrap as gw 
#else:
import api.gmshWrap as gw

#%% create mesh object
class Mesh_obj: 
    """
    creates a mesh class
    
    Parameters
    ----------
    num_nodes: int
        number of nodes
    num_elms: int 
        number of elements 
    node_x: list, 1d numpy array
        x coordinates of nodes 
    node_y: list, 1d numpy array
        coordinates of nodes
    node_z: list, 1d numpy array
        z coordinates of nodes 
    node_id: list
        node id number (ie 1,2,3,4,...)
    elm_id: list
        element id number 
    node_data: list of lists of ints 
        nodes of element vertices in the form [[node1],[node2],[node3],...], each
        node id should be an integer type. 
    elm_centre: list of lists of floats
        centre of elements (x,y)
    elm_area: list 
        area of each element
    cell_type: list of ints
        code referencing cell geometry (e.g. triangle) according to vtk format
    cell_attributes: list of floats
        the values of the attributes given to each cell 
    atribute_title: string 
        what is the attribute? we may use conductivity instead of resistivity for example
    original_file_path: string, optional
        file path to where the mesh file was originally imported
    regions: optional
        element indexes for a material in the mesh (needs further explanation)
        
    Returns
    ----------
    Mesh_obj: object
        
    """    
    def __init__(self,#function constructs our mesh object. 
                 num_nodes,#number of nodes
                 num_elms,#number of elements 
                 node_x,#x coordinates of nodes 
                 node_y,#y coordinates of nodes
                 node_z,#z coordinates of nodes 
                 node_id,#node id number 
                 elm_id,#element id number 
                 node_data,#nodes of element vertices
                 elm_centre,#centre of elements (x,y)
                 elm_area,#area of each element
                 cell_type,#according to vtk format
                 cell_attributes,#the values of the attributes given to each cell 
                 atribute_title,#what is the attribute? we may use conductivity instead of resistivity for example
                 original_file_path='N/A',
                 regions=None) :
        #assign varaibles to the mesh object 
        self.num_nodes=num_nodes
        self.num_elms=num_elms
        self.node_x = node_x
        self.node_y = node_y
        self.node_z = node_z
        self.node_id=node_id
        self.elm_id=elm_id
        self.con_matrix = node_data #connection matrix
        self.elm_centre=elm_centre
        self.elm_area=elm_area
        self.cell_type=cell_type
        self.cell_attributes=cell_attributes 
        self.atribute_title=atribute_title
        self.original_file_path=original_file_path
        self.mesh_title = "not_given"
        self.no_attributes = 1
        self.regions = regions
        self.attr_cache={}
        #decide if mesh is 3D or not 
        if max(node_z) - min(node_z) == 0: # mesh is probably 2D 
            self.ndims=2
        else:
            self.ndims=3
    
    
    def add_e_nodes(self,e_nodes):
        self.e_nodes = e_nodes
        self.elec_x = np.array(self.node_x)[np.array(e_nodes)]
        self.elec_y = np.array(self.node_y)[np.array(e_nodes)]
    
    #add some functions to allow adding some extra attributes to mesh 
    def add_sensitivity(self,values):#sensitivity of the mesh
        if len(values)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.sensitivities = values
        
    def add_conductivities(self,values):
        if len(values)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.conductivities = values
        
    def log10(self):#adds a log 10 (resistivity) to the mesh
        Mesh_obj.no_attributes += 1
        self.log_attribute=np.log10(self.cell_attributes)
        
    def file_path(self):#returns the file path from where the mesh was imported
        return(format(self.original_file_path))
       
    def Type2VertsNo(self):#converts vtk cell types into number of vertices each element has 
        if int(self.cell_type[0])==5:#then elements are triangles
            return 3
        elif int(self.cell_type[0])==8 or int(self.cell_type[0])==9:#elements are quads
            return 4
        elif int(self.cell_type[0]) == 11: # elements are voxels
            return 8
        #add element types as neccessary 
        else:
            print("WARNING: unrecognised cell type")
            return 0
        
    def summary(self):
        #prints summary information about the mesh
        print("\n_______mesh summary_______")
        print("Number of elements: %i"%int(self.num_elms))
        print("Number of nodes: %i"%int(self.num_nodes))
        #print("Attribute title: %s"%self.atribute_title)
        print("Number of cell vertices: %i"%self.Type2VertsNo())
        print("Number of cell attributes: %i"%int(self.no_attributes))
        print("original file path: %s"%self.file_path())
        print("\n")

    def show(self,color_map = 'Spectral',#displays the mesh using matplotlib
             color_bar = True,
             xlim = "default",
             ylim = "default",
             ax = None,
             electrodes = True,
             sens = False,
             edge_color = 'k',
             contour=False,
             vmin=None,
             vmax=None,
             attr=None):
        """
        displays a 2d mesh and attribute 
        
        Parameters
        ----------
        color_map : string, 
            color map reference 
        color_bar : Boolian, 
            True to plot colorbar 
        xlim: tuple
            axis x limits as (xmin, xmax)
        ylim: tuple
            axis y limits as (ymin, ymax)
        ax: matplotlib axis handle,
            axis handle if preexisting (error will thrown up if not) figure is to be cast to.
        electrodes: Boolian 
            enter true to add electrodes to plot
        sens: Boolian, 
            enter true to plot sensitivities 
        edge_color: string
            color of the cell edges, set to None if you dont want an edge
        contour: boolian
            if True, plot filled contours
        vmin: float
            minimum limit for the color bar scale 
        vmax: float
            maximum limit for the color bar scale 
        attr: string
            which attribute in the mesh to plot, references a dictionary of attributes. attr is passed 
            as the key for this dictionary
        
        Returns
        ----------
        matplotlib figure with mesh 
        
        Notes
        ----------
        Show a mesh object using matplotlib. The color map variable should be 
        a string refering to the color map you want (default is "jet").
        As we're using the matplotlib package here any color map avialable within 
        matplotlib package can be used to display the mesh here also. See: 
        https://matplotlib.org/2.0.2/examples/color/colormaps_reference.html
        """
        #check color map argument is a string 
        if not isinstance(color_map,str):#check the color map variable is a string
            raise NameError('color_map variable is not a string')
            #not currently checking if the passed variable is in the matplotlib library
        
        ### overall this code section needs prettying up to make it easier to change attributes ### 
        #decide which attribute to plot, we may decide to have other attritbutes! 
        if attr is None: 
            #plots default attribute
            X=np.array(self.cell_attributes) # maps resistivity values on the color map
            color_bar_title = self.atribute_title
        else:
            try:
                X = np.array(self.attr_cache[attr])
                color_bar_title = attr
            except (KeyError, AttributeError):
                raise KeyError("Cannot find attr_cache attribute in mesh object or 'attr' does not exist.")

        iplot = False
        if ax is None:
            iplot = True
            fig,ax=plt.subplots()
        #if no dimensions are given then set the plot limits to edge of mesh
        try: 
            if xlim=="default":
                xlim=[min(self.elec_x),max(self.elec_x)]
            if ylim=="default":
                doiEstimate = 2/3*np.abs(self.elec_x[0]-self.elec_x[-1]) # TODO depends on longest dipole
                print(doiEstimate)
                ylim=[min(self.elec_y)-doiEstimate,max(self.elec_y)]
        except AttributeError:
            if xlim=="default":
                xlim=[min(self.node_x),max(self.node_x)]
            if ylim=="default":
                ylim=[min(self.node_y),max(self.node_y)]
                
        ##plot mesh! ##
        a = time.time() #start timer on how long it takes to plot the mesh
        #compile mesh coordinates into polygon coordinates  
        nodes = np.c_[self.node_x, self.node_y]
        connection = np.array(self.con_matrix).T # connection matrix 
        #compile polygons patches into a "patch collection"
        ###X=np.array(self.cell_attributes) # maps resistivity values on the color map### <-- disabled 
        coordinates = nodes[connection]
        if vmin is None:
            vmin = np.min(X)
        if vmax is None:
            vmax = np.max(X)
        
        if edge_color == None or edge_color=='none' or edge_color=='None':
            edge_color='face'#set the edge colours to the colours of the polygon patches

        if contour is False:
            coll = PolyCollection(coordinates, array=X, cmap=color_map, edgecolors=edge_color,linewidth=0.5)
            coll.set_clim(vmin=vmin, vmax=vmax)
            ax.add_collection(coll)#blit polygons to axis
            cax = coll
        else:
            x = np.array(self.elm_centre[0])
            y = np.array(self.elm_centre[1])
            z = np.array(X)
#            xmin, xmax = np.min(x), np.max(x)
#            ymin, ymax = np.min(y), np.max(y)
#            dx = (xmax-xmin)/40
#            dy = (ymax-ymin)/40
#            xi, yi = np.meshgrid(np.linspace(xmin-dx, xmax+dx, 40),
#                                 np.linspace(ymin-dy, ymax+dy, 40))
#            print(np.min(xi), np.max(xi), np.min(yi), np.max(yi))
#            zi = griddata((x, y), z, (xi.flatten(), yi.flatten()))#, method='linear')
#            zi = zi.reshape(xi.shape)
#            cax = ax.contourf(xi, yi, zi, cmap=color_map, edgecolors=edge_color)
            triang = tri.Triangulation(x,y)
            cax = ax.tricontourf(triang, z)
            
        ax.autoscale()
        #were dealing with patches and matplotlib isnt smart enough to know what the right limits are, hence set axis limits 
        ax.set_ylim(ylim)
        ax.set_xlim(xlim)
        ax.set_xlabel('Distance')
        ax.set_ylabel('Elevation')
        
        if color_bar:#add the color bar 
            cbar = plt.colorbar(cax, ax=ax)#add colorbar
            cbar.set_label(color_bar_title) #set colorbar title      
        
        ax.set_aspect('equal')#set aspect ratio equal (stops a funny looking mesh)

        #biuld alpha channel if we have sensitivities 
        if sens:
            try:
                weights = np.array(self.sensitivities) #values assigned to alpha channels 
                alphas = np.linspace(1, 0, self.num_elms)#array of alpha values 
                raw_alpha = np.ones((self.num_elms,4),dtype=float) #raw alpha values 
                raw_alpha[..., -1] = alphas
                alpha_map = ListedColormap(raw_alpha) # make a alpha color map which can be called by matplotlib
                #make alpha collection
                alpha_coll = PolyCollection(coordinates, array=weights, cmap=alpha_map, edgecolors=None)
                #*** the above line can cuase issues "attribute error" no np.array has not attribute get_transform, 
                #*** i still cant figure out why this is becuase its the same code used to plot the resistivities 
                ax.add_collection(alpha_coll)
            except AttributeError:
                print("no sensitivities in mesh object to plot")
        
        if electrodes: #try add electrodes to figure if we have them 
            try: 
                ax.plot(self.elec_x,self.elec_y,'ko')
            except AttributeError:
                print("no electrodes in mesh object to plot")
        print('Mesh plotted in %6.5f seconds'%(time.time()-a))
        
        if iplot == True:
            return fig
        
    def apply_func(self,mesh_paras,material_no,new_key,function,*args):
        """
        applys a function to a mesh by material number and mesh parameter
        
        Parameters
        ----------
        mesh_paras: 
            mesh parameters from which new parameters are calculated 
        material_no: list of ints
            material type assigned to each element, should be numbered consectively from 1 to n. in the form 1 : 1 : 2 : n.
            ...ie if you have 2 materials in the mesh then pass an array of ones and twos.
        new_key: string
            key assigned to the parameter in the attr_cache. DOES NOT default
        function: function
            function to be applied to mesh attributes, first argument must be the mesh parameter
        args: [see function info]
            all arguments to be passed through function after to modify the mesh parameter,
            ... argument must be in the form of [(argA1,argB1),(argA2,argB2)], 
            ... where letters are the material, numbers refer to the argument number
        
        Returns
        ----------
        new parameters added to Mesh_obj.attr_dict
        """
    
        if len(material_no)!=len(mesh_paras):
            raise ValueError('Mismatch between the number of material propeties (for the mesh) and parameters to be converted')
        new_para=[0]*self.num_elms
        #iterate through each set of argument variables
        for iteration in range(len(args[0])):
            parameters=[items[iteration] for items in args]#return parameters 
            parameters.insert(0,0)#this adds an element to the front of the parameters which can be swapped out resistivity
            for i in range(self.num_elms):
                if material_no[i]==iteration+1:#does the material match the iteration? 
                    parameters[0]=mesh_paras[i]#change parameter value at start of variables list
                    new_para[i]=function(*parameters)#compute new parameter   
        self.attr_cache[new_key] = new_para
        self.no_attributes += 1
        #return new_para
        
    def assign_material_attribute(self,material_no,attr_list,new_key):
        """
        Asssigns values to the mesh which depend on region / material only. E.G 
        a single resistivity value 
            
        Parameters
        ----------
        material_no : array or list
            integers starting at 0 or 1, and ascend in intervals of 1, which 
            correspond to a material in the mesh returned from assign_attr_ID. 
        attr_list : list
            list of values corresponding to a material number in the mesh. eg. if you had 3 regions in the mesh then you give
            [resistivity1,resistivity2,resistivity3]
        new_key: string
            key identifier assigned to the attribute in the attr_cache. 
        
        Returns 
        ----------
        mesh object will now have the new attribute added. Use the mesh.show() function to see the result. 
        """ 
        if len(material_no) != self.num_elms:
            raise ValueError("Mismatch between the number of elements and material propeties")
        
        new_para=[0]*self.num_elms
        
        if min(material_no)==1:#cor_fac allows for compatability with an index system starting at 1 or 0 
            cor_fac=1
        else:
            cor_fac=0
       
        for i in range(self.num_elms):
            new_para[i] = attr_list[int(material_no[i]) - cor_fac]
        
        self.attr_cache[new_key] = new_para
        self.no_attributes += 1

            
    def add_attribute(self,values,key):
        #add a new attribute to mesh 
        if len(values)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.no_attributes += 1
        self.attr_cache[key]=values #allows us to add an attributes to each element.
        #this function needs fleshing out more to allow custom titles and attribute names
    
    def add_attr_dict(self,attr_dict):
        self.attr_cache=attr_dict
        self.no_attributes = len(attr_dict)
    
    def update_attribute(self,new_attributes,new_title='default'):
        #allows you to reassign the cell attributes in the mesh object 
        if len(new_attributes)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.cell_attributes=new_attributes
        self.atribute_title=str(new_title)
    
    @classmethod # creates a mesh object from a mesh dictionary
    def mesh_dict2obj(cls,mesh_info):
        """
        converts a mesh dictionary produced by the gmsh2r2mesh and vtkimport functions into a 
        mesh object, its an alternative way to make a mesh object. 
        ***Intended for development use***
            
        Parameters
        ----------
        mesh_info: dictionary 
            mesh parameters stored in a dictionary rather than a mesh, useful for debugging parsers
            
        Returns
        ---------- 
        mesh class object
    """
        #check the dictionary is a mesh
        try: 
            if mesh_info['dict_type']!='mesh_info':
                raise NameError("dictionary is not a mesh type")
        except KeyError:
                raise ImportError("dictionary has no dict type variable") 
        #covert into an object 
        obj=cls(mesh_info['num_nodes'],
                     mesh_info['num_elms'], 
                     mesh_info['node_x'],
                     mesh_info['node_y'],
                     mesh_info['node_z'],
                     mesh_info['node_id'],
                     mesh_info['elm_id'],
                     mesh_info['node_data'],
                     mesh_info['elm_centre'],
                     mesh_info['elm_area'],
                     mesh_info['cell_type'],
                     mesh_info['parameters'],
                     mesh_info['parameter_title'],
                     mesh_info['original_file_path'])
        try:
            obj.add_attr_dict(mesh_info['cell_attributes'])
        except KeyError as e:
            print('error in add_attr_dict', e)
            pass
        try:
            obj.regions = mesh_info['element_ranges']
        except KeyError:
            pass
                
        return (obj)
    
    @staticmethod
    def help_me():#a basic help me file, needs fleshing out
        available_functions=["show","summary","show_mesh","log10","add_attribute","mesh_dict2obj","Type2VertsNo"]
        print("\n_______________________________________________________")#add some lines, make info look pretty
        print("available functions within the mesh_obj class: \n")
        for i in range(len(available_functions)):
            print("%s"%available_functions[i])
        print("_______________________________________________________")
        
    def write_vtk(self,file_path='default', title=None):
        """
        writes a vtk file
        
        Parameters
        ------------
        file_path : string 
            maps where python will write the file. if left as default then mesh.vtk
            will be written the current working directory. 
        title: string
            header string written at the top of the vtk file 
        
        Returns
        ----------
        vtk file written to specified directory
        """
        #decide where to save the file 
        if file_path == "default":
            file_path = "mesh.vtk"
        #open file and write header information    
        fh = open(file_path,'w')
        fh.write("# vtk DataFile Version 3.0\n")
        if title == None:
            try:
                title = self.mesh_title
            except AttributeError:
                title = "output from R2 gui meshTools module"
        fh.write(title+"\n")
        fh.write("ASCII\nDATASET UNSTRUCTURED_GRID\n")
        #define node coordinates
        fh.write("POINTS %i double\n"%self.num_nodes)
        for i in range(self.num_nodes):
            fh.write("%8.6f\t%8.6f\t%8.6f\n"%(self.node_x[i],self.node_y[i],self.node_z[i]))
        #define the connection matrix    
        no_verts = self.Type2VertsNo()
        no_readable = self.num_elms*(1+no_verts)
        fh.write("CELLS %i %i\n"%(self.num_elms,no_readable))
        for i in range(self.num_elms):
            fh.write("%i\t"%no_verts)
            for k in range(no_verts):
                fh.write("{}    ".format(self.con_matrix[k][i]))
            fh.write("\n")
        #cell types
        fh.write("CELL_TYPES %i\n"%self.num_elms)
        [fh.write("%i "%self.cell_type[i]) for i in range(self.num_elms)];fh.write("\n")
        #write out the data
        fh.write("CELL_DATA %i\n"%self.num_elms)
        for i,key in enumerate(self.attr_cache):
            fh.write("SCALARS %s double 1\n"%key)
            fh.write("LOOKUP_TABLE default\n")
            [fh.write("%8.6f "%self.attr_cache[key][j]) for j in range(self.num_elms)]
            fh.write("\n")
        
        #finish writing
        fh.write("POINT_DATA %i"%self.num_nodes)        
        fh.close()
    
    def write_attr(self,attr_key,file_name='_res.dat',file_path='defualt'):
        """
        writes a attribute to a _res.dat type file. file_name entered seperately 
        becuase it will be needed for the R2 config file. The reason for this function
        is so you can write a forward model parameter input file. 
        Parameters
        ---------
        attr_key: string
            key identifying the attr to be written in the mesh object attr_cache
        file_name: string
            name of the _res.dat type file
        file_path: string
            directory to which the file will be saved in, if left as none then the
            file will be written in the current working directory 
        Returns
        ---------
        #_res.dat type file 
        """
        #formality checks 
        if len(file_name)>15:
            raise NameError("File name for _res.dat type file cannot be longer than 15 characters")
            
        if isinstance(file_name,str)==False or isinstance(file_path,str) == False:
            raise NameError("file_name and file_path arguments must be strings")
        
        if file_path == 'defualt':#no directory given then ignore file path input
            file_path = file_name
        else:#reassign file_path to full path including the name
            file_path = os.path.join(file_path,file_name)
        
        #the format of the _res.dat file is such that
        #| x coordinate | y coordinate | value | log(value) | 
        fh = open(file_path,'w')#open file handle 
        x_coords=self.elm_centre[0]#get element coordinates
        y_coords=self.elm_centre[1]
        values=self.attr_cache[attr_key]
        log_values=np.log10(np.array(values))
        for i in range(self.num_elms):
            fh.write("\t{: 10.5e}\t{: 10.5e}\t{: 10.5e}\t{: 10.5e}\n".format(x_coords[i],y_coords[i],values[i],log_values[i]))
            
        fh.close()
        
        
        
    
    def asgn_atbrte_ID(self,poly_data):
        """
        Assign material/region assocations with certain elements in the mesh 
        say if you have an area you'd like to forward model. 
        ***2D ONLY***
            
        Parameters
        ----------
        poly_data: dictionary 
            with the vertices (x,y) of each point in the polygon
            
        Returns
        ---------- 
        a list of element assocaitions starting at 1. So 1 for the first region defined in the region_data variable, 2 for the
        second region defined and so on. If the element cant be assigned to a region then it'll be left at 0. 
        """   
        no_elms=self.num_elms#number of elements 
        elm_xy=self.elm_centre#centriods of mesh elements 
        material_no=[0]*no_elms#attribute number
        
        if not isinstance(poly_data,dict):
            raise Exception("poly_data input is not a dictionary")
        
        #now on to extracting the data of interest
        dodgey=0#this will be used as a check to make sure elements havent been overwritten
        print('Assigning element attribute IDs...')
        
        for i,key in enumerate(poly_data):
            poly_x=poly_data[key][0]#polygon x coordinates
            poly_y=poly_data[key][1]#polygon y coordinates
            for k in range(no_elms):
                if gw.isinpolygon(elm_xy[0][k],elm_xy[1][k],(poly_x,poly_y)):#then the centriod of the element must be inside region of interest
                    if material_no[k]!=0:#then we must be overwriting a previously assigned element
                        dodgey=dodgey+1 
                    material_no[k]=i+1
        
        if dodgey>0:
            warnings.warn('%i elements attributes were overwritten into previously assigned attributes, check that polygons do not overlap.'%dodgey) 
        if min(material_no)==0:
            warnings.warn('Some elements still have the default attribute of zero, which suggests they are not recognised as being part of a region and will be assigned a default value later in the workflow')                
        return material_no

                 
#%% triangle centriod 
def tri_cent(p,q,r):
    """
    #compute the centre coordinates for a 2d triangle given the x,y coordinates 
    #of the vertices.
            
    Parameters
    ----------
    #code expects points as p=(x,y) and so on (counter clockwise prefered)
            
    Returns
    ----------
    coordinates: tuple
        in the format (x,y)    
    """
    Xm=(p[0]+q[0])/2
    Ym=(p[1]+q[1])/2
    k=2/3
    Xc=r[0]+(k*(Xm-r[0]))
    Yc=r[1]+(k*(Ym-r[1]))
    return(Xc,Yc)
    
#%% import a vtk file 
def vtk_import(file_path='ask_to_open',parameter_title='default'):
    """
    #imports a 2d mesh file into the python workspace, can have triangular or quad type elements 
            
    Parameters
    ----------
    file_path: string
        file path to mesh file. note that a error will occur if the file format is not as expected
    parameter_title: string
        name of the parameter table in the vtk file, if left as default the first look up table found will be returned 
        also note that all parameters will be imported. just the title highlights which one the mesh object will use as 
        default. 
            
    Returns
    ----------
    mesh object 
    """
    if file_path=='ask_to_open':#use a dialogue box to open a file
        print("please select the vtk file to import using the pop up dialogue box. \n")
        root=tk.Tk()
        root.withdraw()
        file_path=filedialog.askopenfilename(title='Select mesh file',filetypes=(("VTK files","*.vtk"),("all files","*.*")))#
    #open the selected file for reading
    fid=open(file_path,'r')
    #print("importing vtk mesh file into python workspace...")
    
    #read in header info and perform checks to make sure things are as expected
    vtk_ver=fid.readline().strip()#read first line
    if vtk_ver.find('vtk')==-1:
        raise ImportError("Unexpected file type... ")
    elif vtk_ver.find('3.0')==-1:#not the development version for this code
        print("Warning: vtk manipulation code was developed for vtk datafile version 3.0, unexpected behaviour may occur")
    title=fid.readline().strip()#read line 2
    format_type=fid.readline().strip()#read line 3
    if format_type=='BINARY':
        raise ImportError("expected ASCII type file format, not binary")
    dataset_type=fid.readline().strip().split()#read line 4
    if dataset_type[1]!='UNSTRUCTURED_GRID':
        print("Warning: code intended to deal with an 'UNSTRUCTURED_GRID' data type not %s"%dataset_type[1])
    
    #read node data
    #print("importing mesh nodes...")
    node_info=fid.readline().strip().split()#read line 5
    try:
        no_nodes=int(node_info[1])
    except IndexError:#if we get this then there is a white space between the node info and header lines
        node_info=fid.readline().strip().split()#read line 5
        no_nodes=int(node_info[1])
    #now read in node data
    x_coord=[]#make lists for each of the relevant parameters for each node
    y_coord=[]
    z_coord=[]
    node_num=[]
    for i in range(no_nodes):
        coord_data=fid.readline().strip().split()
        x_coord.append(float(coord_data[0]))
        y_coord.append(float(coord_data[1]))
        z_coord.append(float(coord_data[2]))
        node_num.append(i)
    
    #now read in element data
    #print("importing mesh element info...")
    elm_info=fid.readline().strip().split()#read line with cell data
    try:
        no_elms=int(elm_info[1])
    except IndexError: # quick bug fix
        elm_info=fid.readline().strip().split()#read line with cell data
        no_elms=int(elm_info[1])
        
    no_pts=[]#assign lists to nodes 
    node1=[]
    node2=[]
    node3=[]
    node4=[]
    node5=[]
    node6=[]
    node7=[]
    node8=[]
    #node9=[]
    elm_num=[]
    centriod_x=[]#list will contain the centre points of elements 
    centriod_y=[]
    centriod_z=[]
    areas=[]#areas of cells (might be useful in the future)
    ignored_cells=0
    #import element data ... expects triangles or quads 
    for i in range(no_elms):
        elm_data=fid.readline().strip().split()
        if int(elm_data[0])==3:
            if i==0:
                #print("triangular elements detected")
                vert_no=3
            no_pts.append(int(elm_data[0]))
            #nodes
            node1.append(int(elm_data[1]))
            node2.append(int(elm_data[2]))
            node3.append(int(elm_data[3]))
            elm_num.append(i+1)
            #find the centriod of the element for triangles
            n1=(x_coord[int(elm_data[1])],y_coord[int(elm_data[1])])#in vtk files the 1st element id is 0 
            n2=(x_coord[int(elm_data[2])],y_coord[int(elm_data[2])])
            n3=(x_coord[int(elm_data[3])],y_coord[int(elm_data[3])])
            xy_tuple=tri_cent(n1,n2,n3)#actual calculation
            centriod_x.append(xy_tuple[0])
            centriod_y.append(xy_tuple[1])
            #find area of element (for a triangle this is 0.5*base*height)
            base=(((n1[0]-n2[0])**2) + ((n1[1]-n2[1])**2))**0.5
            mid_pt=((n1[0]+n2[0])/2,(n1[1]+n2[1])/2)
            height=(((mid_pt[0]-n3[0])**2) + ((mid_pt[1]-n3[1])**2))**0.5
            areas.append(0.5*base*height)
        elif int(elm_data[0])==4:
            if i==0:
                #print("quad elements detected")
                vert_no=4
            no_pts.append(int(elm_data[0]))
            #nodes
            node1.append(int(elm_data[1]))
            node2.append(int(elm_data[2]))
            node3.append(int(elm_data[3]))
            node4.append(int(elm_data[4]))
            elm_num.append(i+1)
            #assuming element centres are the average of the x - y coordinates for the quad
            n1=(x_coord[int(elm_data[1])],y_coord[int(elm_data[1])])#in vtk files the 1st element id is 0 
            n2=(x_coord[int(elm_data[2])],y_coord[int(elm_data[2])])
            n3=(x_coord[int(elm_data[3])],y_coord[int(elm_data[3])])
            n4=(x_coord[int(elm_data[4])],y_coord[int(elm_data[4])])
            centriod_x.append(np.mean((n1[0],n2[0],n3[0],n4[0])))
            centriod_y.append(np.mean((n1[1],n2[1],n3[1],n4[1])))
            #finding element areas, base times height.  
            elm_len=abs(n2[0]-n1[0])#element length
            elm_hgt=abs(n2[1]-n3[1])#element hieght
            areas.append(elm_len*elm_hgt)
        elif int(elm_data[0])==8: # this following code is getting silly in how long it is. Need to work on a more efficent way
            if i==0:
                #print("voxel elements detected")
                vert_no=8
            no_pts.append(int(elm_data[0]))
            #nodes
            node1.append(int(elm_data[1]))
            node2.append(int(elm_data[2]))
            node3.append(int(elm_data[3]))
            node4.append(int(elm_data[4]))
            node5.append(int(elm_data[5]))
            node6.append(int(elm_data[6]))
            node7.append(int(elm_data[7]))
            node8.append(int(elm_data[8]))
            #assuming element centres are the average of the x - y coordinates for the quad
            n1=(x_coord[int(elm_data[1])],y_coord[int(elm_data[1])],z_coord[int(elm_data[1])])#in vtk files the 1st element id is 0 
            n2=(x_coord[int(elm_data[2])],y_coord[int(elm_data[2])],z_coord[int(elm_data[2])])
            n3=(x_coord[int(elm_data[3])],y_coord[int(elm_data[3])],z_coord[int(elm_data[3])])
            n4=(x_coord[int(elm_data[4])],y_coord[int(elm_data[4])],z_coord[int(elm_data[4])])
            n5=(x_coord[int(elm_data[5])],y_coord[int(elm_data[5])],z_coord[int(elm_data[5])]) 
            n6=(x_coord[int(elm_data[6])],y_coord[int(elm_data[6])],z_coord[int(elm_data[6])])
            n7=(x_coord[int(elm_data[7])],y_coord[int(elm_data[7])],z_coord[int(elm_data[7])])
            n8=(x_coord[int(elm_data[8])],y_coord[int(elm_data[8])],z_coord[int(elm_data[8])])
            centriod_x.append(np.mean((n1[0],n2[0],n3[0],n4[0],n5[0],n6[0],n7[0],n8[0])))
            centriod_y.append(np.mean((n1[1],n2[1],n3[1],n4[1],n5[1],n6[1],n7[1],n8[1])))
            centriod_z.append(np.mean((n1[2],n2[2],n3[2],n4[2],n5[2],n6[2],n7[2],n8[2])))
            #estimate element VOLUMES, base area times height.  
            elm_len=abs(n2[0]-n1[0])#element length
            elm_width = abs(n1[1]-n3[1])
            elm_thick=abs(n5[2]-n1[2])#element hieght
            areas.append(elm_len*elm_width*elm_thick)
            
        else: 
            warnings.warn("WARNING: unkown cell type encountered!")
            ignored_cells+=1
    #compile some information        
    
    if vert_no==3:
        node_maps=(node1,node2,node3)
        centriod=(centriod_x,centriod_y)#centres of each element in form (x...,y...)
    elif vert_no==4:
        node_maps=(node1,node2,node3,node4)
        centriod=(centriod_x,centriod_y)#centres of each element in form (x...,y...)
    elif vert_no==8:
        node_maps=(node1,node2,node3,node4,node5,node6,node7,node8)
        centriod=(centriod_x,centriod_y,centriod_z)#centres of each element in form (x...,y...,z...)
        
    if ignored_cells>0:
        print("%i cells ignored in the vtk file"%ignored_cells)
    
    cell_attr_dump=fid.readlines()#reads the last portion of the file
    #finished reading the file
    
    #find cell types
    for i,line_info in enumerate(cell_attr_dump):
        if line_info.find("CELL_TYPES") == 0:
            cell_type = [int(k) for k in cell_attr_dump[i+1].strip().split()]
            break
    
    fid.close()
    #print("reading cell attributes...")
    # read through cell attributes to find the relevant parameter table?
    
    #find scalar values in the vtk file
    num_attr = 0
    attr_dict = {}
    found = False # boolian if we have found the parameter of interest
    for i,line_info in enumerate(cell_attr_dump):
        if line_info.find("SCALARS") == 0:
            attr_title = line_info.split()[1]
            #check look up table
            if cell_attr_dump[i+1].split()[1] != "default":
                warnings.warn("unrecognised lookup table type")
            values=[float(k) for k in cell_attr_dump[i+2].split()]
            attr_dict[attr_title] = values
            if num_attr ==0:# primary attribute defaults to the first attribute found
                parameter_title = attr_title
                values_oi = values
            if attr_title == parameter_title:#then its the parameter of interest that the user was trying extract
                found = True
                values_oi = values        
            num_attr += 1
    
    #put in fail safe if no attributes are found        
    if num_attr == 0:
        print("no cell attributes found")
        attr_dict = {"no attributes":float("nan")}
        values = float("nan")
        parameter_title = "n/a"
    #print("finished importing mesh.\n")
    #information in a dictionary, this is easier to debug than an object in spyder: 
    mesh_dict = {'num_nodes':no_nodes,#number of nodes
            'num_elms':no_elms,#number of elements 
            'node_x':x_coord,#x coordinates of nodes 
            'node_y':y_coord,#y coordinates of nodes
            'node_z':z_coord,#z coordinates of nodes 
            'node_id':node_num,#node id number 
            'elm_id':elm_num,#element id number 
            'num_elm_nodes':no_pts,#number of points which make an element
            'node_data':node_maps,#nodes of element vertices
            'elm_centre':centriod,#centre of elements (x,y)
            'elm_area':areas,#area of each element (or volume)
            'cell_type':cell_type,
            'parameters':values_oi,#the values of the attributes given to each cell 
            'parameter_title':parameter_title,
            'cell_attributes':attr_dict,
            'dict_type':'mesh_info',
            'original_file_path':file_path} 
    Mesh = Mesh_obj.mesh_dict2obj(mesh_dict)
    try:
        Mesh.add_sensitivity(Mesh.attr_cache['Sensitivity(log10)'])
    except:
        print('no sensitivity')
        pass
    Mesh.mesh_title = title
    return Mesh
    
#%% Read in resistivity values from R2 output 
def readR2_resdat(file_path):
    """
    reads resistivity values in f00#_res.dat file output from R2, 
            
    Parameters
    ----------
    file_path: string
        maps to the _res.dat file
            
    Returns
    ----------
    res_values: list of floats
        resistivity values returned from the .dat file 
    """
    if not isinstance (file_path,str):
        raise NameError("file_path variable is not a string, and therefore can't be parsed as a file path")
    fh=open(file_path,'r')
    dump=fh.readlines()
    fh.close()
    res_values=[]
    for i in range(len(dump)):
        line=dump[i].split()
        res_values.append(float(line[2]))
    return res_values   

#%% read in sensitivity values 
def readR2_sensdat(file_path):
    """
    reads sensitivity values in f00#_res.dat file output from R2, 
            
    Parameters
    ----------
    file_path: string
        maps to the _sens.dat file
            
    Returns
    ----------
    res_values: list of floats
        sensitivity values returned from the .dat file (not log10!)
    """
    if not isinstance (file_path,str):
        raise NameError("file_path variable is not a string, and therefore can't be parsed as a file path")
    fh=open(file_path,'r')
    dump=fh.readlines()
    fh.close()
    sens_values=[]
    for i in range(len(dump)):
        line=dump[i].split()
        sens_values.append(float(line[2]))
    return sens_values   


        
#%% build a quad mesh        
def quad_mesh(elec_x,elec_y,elemx=4, xgf=1.5, yf=1.1, ygf=1.5, doi=-1, pad=2):
    """
    creates a quaderlateral mesh given the electrode x and y positions. Function
    relies heavily on the numpy package.
            
    Parameters
    ----------
    elec_x: list, np array
        electrode x coordinates 
    elec_y: list, np array
        electrode y coordinates
    elemy: int
        number of elements in the fine y region
    yf: float
         y factor multiplier in the fine zone
    ygf: float
         y factor multiplier in the coarse zone
    doi: float (m)
         depth of investigation (if left as -1 = half survey width)
    pad:
         x padding outside the fine area (tipicaly twice the number of elements between electrodes)
            
    Returns
    ----------
    Mesh: class
        mesh object 
    meshx: np array
        mesh x locations for R2in file 
    meshy: np array
        mesh y locations for R2in file (ie node depths)
    topo: np array
        topography for R2in file
    elec_node: np array
        x columns where the electrodes are 
    """
    if elemx < 4:
        print('elemx too small, set up to 4 at least')
        elemx = 4
    elec = np.c_[elec_x, elec_y]
    pad = pad # number of padding on both side (as a multiplier of the nb of nodes between electrodes)
    # create meshx
    meshx = np.array([])
    for i in range(len(elec)-1):
        elec1 = elec[i,0]
        elec2 = elec[i+1,0]
        espacing = np.abs(elec1-elec2)
        dx = espacing/elemx # we ask for elemx nodes between electrodes
        if i == 0:
            xx2 = np.arange(elec1-espacing, elec1, dx)
            xx3 = np.ones(elemx*pad)*elec1-espacing
            dxx = espacing
            for j in range(1,elemx*pad): # padding
                xx3[j] = xx3[j-1]-dxx*xgf
                dxx = dxx*xgf
            meshx = np.r_[meshx, xx3[::-1], xx2[1:]]
        xx = np.arange(elec1, elec2, dx)
        meshx = np.r_[meshx, xx]
        if i == len(elec)-2:
            xx2 = np.arange(elec2, elec2+espacing, dx)
            xx3 = np.ones(elemx*pad)*elec2+espacing
            dxx = espacing
            for j in range(1,elemx*pad):
                xx3[j] = xx3[j-1]+dxx*xgf
                dxx = dxx*xgf
            meshx = np.r_[meshx, xx2, xx3]
    
    # create e_nodes
    elec_node = np.arange(len(xx3)+len(xx2)-1, 2*pad*(elemx-1)+(len(elec)-1)*elemx, elemx)
    #TODO make sure it's dividable by patchx and patch y
    
    # create meshy
    if doi == -1:
        doi = np.abs(elec[0,0]-elec[-1,0])/2
#    dyy = espacing/(elemx*4)
    meshy = [0]
    dyy = 0.05
    for i in range(100):
        meshy.append(meshy[-1]+dyy*yf)
        dyy = dyy*yf
        if meshy[-1] > doi:
            break
    elemy = len(meshy)
    elemy2 = int(elemy/2)
    yy = np.ones(elemy2)*meshy[-1]
    for i in range(1, elemy2):
        yy[i] = yy[i-1]+dyy*xgf
        dyy = dyy*xgf
    meshy = np.r_[meshy, yy[1:]]
    
    # create topo
    topo = np.interp(meshx, elec[:,0], elec[:,1])
    
    no_electrodes = len(elec)
    
    ###
    #find the columns relating to the electrode nodes? 
#    elec_node=[meshx.index(elec_x[i])+1 for i in range(len(elec_x))]
    
    #print some warnings for debugging 
    if len(topo)!=len(meshx):
        print("WARNING: topography vector and x coordinate arrays not the same length! ")
    elif len(elec_node)!=no_electrodes:
        print("WARNING: electrode node vector and number of electrodes mismatch! ")
     
    # what is the number of regions? (elements)
    no_elms=(len(meshx)-1)*(len(meshy)-1)
    no_nodes=len(meshx)*len(meshy)
    
    # compute node mappins 
    y_dim=len(meshy)
    fnl_node=no_nodes-1
    
    node_mappins=(np.arange(0,fnl_node-y_dim),
                  np.arange(y_dim,fnl_node),
                  np.arange(y_dim+1,fnl_node+1),
                  np.arange(1,fnl_node-y_dim+1))
    
    del_idx=np.arange(y_dim-1,len(node_mappins[0]),y_dim)
    
    node_mappins = [list(np.delete(node_mappins[i],del_idx)) for i in range(4)]#delete excess node placements
    #compute node x and y  (and z)
    node_x,node_y=np.meshgrid(meshx,meshy)
    #account for topography in the y direction 
    node_y = [topo-node_y[i,:] for i in range(y_dim)]#list comprehension to add topography to the mesh
    node_y=list(np.array(node_y).flatten(order='F'))
    node_x=list(node_x.flatten(order='F'))
    node_z=[0]*len(node_x)
    
    #compute element centres and areas
    centriod_x=[]
    centriod_y=[]
    areas=[]
    for i in range(no_elms):
        #assuming element centres are the average of the x - y coordinates for the quad
        n1=(node_x[int(node_mappins[0][i])],node_y[int(node_mappins[0][i])])#in vtk files the 1st element id is 0 
        n2=(node_x[int(node_mappins[1][i])],node_y[int(node_mappins[1][i])])
        n3=(node_x[int(node_mappins[2][i])],node_y[int(node_mappins[2][i])])
        n4=(node_x[int(node_mappins[3][i])],node_y[int(node_mappins[3][i])])
        centriod_x.append(np.mean((n1[0],n2[0],n3[0],n4[0])))
        centriod_y.append(np.mean((n1[1],n2[1],n3[1],n4[1])))
        #finding element areas, base times height.  
        elm_len=abs(n2[0]-n1[0])#element length
        elm_hgt=abs(n2[1]-n3[1])#element hieght
        areas.append(elm_len*elm_hgt)
    
    #make mesh object    
    Mesh = Mesh_obj(no_nodes,
                    no_elms,
                    node_x,
                    node_y,
                    node_z,
                    list(np.arange(0,no_nodes)),
                    list(np.arange(0,no_elms)),
                    node_mappins,
                    (centriod_x,centriod_y),
                    areas,
                    [9],
                    [0]*no_elms,
                    'no attribute')
    
    elec_node2 = elec_node*len(meshy) # because we use columns based flattening
    Mesh.add_e_nodes(elec_node2)
    
    return Mesh,meshx,meshy,topo,elec_node

#%% build a triangle mesh - using the gmsh wrapper
def tri_mesh(geom_input,keep_files=True, show_output = False, path='exe', 
             save_path='default',**kwargs):
    """ 
    Generates a triangular mesh for r2. returns mesh.dat in the Executables directory 
    this function expects the current working directory has path: exe/gmsh.exe
            
    Parameters
    ---------- 
    keep_files: boolian
        True if the gmsh input and output file is to be stored in the exe directory
    show_ouput: boolian
        True if gmsh output is to be printed to console 
    path: string
        path to exe folder (leave default unless you know what you are doing)
    save_path: string
        directory to save 'mesh.dat'
    geom_input:
        dictionary used to generate survey geometry in genGeoFile_adv (see notes there), 
    **kwargs: optional
        key word arguments to be passed to genGeoFile. 
            
    Returns
    ----------
    mesh.dat in the Executables directory
    """
    #check directories 
    if path == "exe":
        ewd = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                path)
        #print(ewd) #ewd - exe working directory 
    else:
        ewd = path
        # else its assumed a custom directory has been given to the gmsh.exe
    cwd=os.getcwd()#get current working directory 
    
    if not os.path.isfile(os.path.join(ewd,'gmsh.exe')):
        raise Exception("No gmsh.exe exists in the exe directory!")
    
    #make .geo file
    file_name="temp"
    if not isinstance(geom_input,dict):
        raise ValueError("geom_input has not been given!")
    node_pos,_ = gw.genGeoFile_adv(geom_input,file_name=file_name,path=ewd,**kwargs)
    
    # handling gmsh
    if platform.system() == "Windows":#command line input will vary slighty by system 
        cmd_line = 'gmsh.exe '+file_name+'.geo -2'
    else:
        cmd_line = ['wine', 'gmsh.exe', file_name+'.geo', '-2']
        
    os.chdir(ewd)
    
    if show_output: 
        p = Popen(cmd_line, stdout=PIPE, shell=False)#run gmsh with ouput displayed in console
        while p.poll() is None:
            line = p.stdout.readline().rstrip()
            print(line.decode('utf-8'))
    else:
        call(cmd_line)#run gmsh 
        
    #convert into mesh.dat 
    mesh_dict=gw.gmsh2R2mesh(file_path=file_name+'.msh',return_mesh=True, save_path=save_path)
    if keep_files is False: 
        os.remove("temp.geo");os.remove("temp.msh")
    #change back to orginal working directory
    os.chdir(cwd)
    
    mesh = Mesh_obj.mesh_dict2obj(mesh_dict)
    
    mesh.add_e_nodes(node_pos-1)
    
    return mesh#, mesh_dict['element_ranges']

#%% write descrete points to a vtk file 
def points2vtk (x,y,z,file_name="points.vtk",title='points'):
    """
    function makes a .vtk file for some xyz coordinates. optional argument
    renames the name of the file (needs file path also) (default is "points.vtk"). 
    title is the name of the vtk file
            
    Parameters
    ----------
    x: list, tuple, np array
        x coordinates of points
    y: list, tuple, np array
        y coordinates of points
    z: list, tuple, np array
        z coordinates of points
    file_name: string, optional
        path to saved file, defualts to 'points.vtk' in current working directory
    title: string, optional
        title of vtk file
            
    Returns
    ----------
    ~.vtk file
    """
    #error check
    if len(x) != len(y) or len(x) != len(z):
        raise ValueError('mis-match between vector lengths')
    
    fh=open(file_name,'w');#open file handle
    #add header information
    fh.write('# vtk DataFile Version 3.0\n')
    fh.write(title+'\n')
    fh.write('ASCII\n')
    fh.write('DATASET POLYDATA\n')
    #add data
    fh.write('POINTS      %i double\n'%len(x))
    [fh.write('{:<10} {:<10} {:<10}\n'.format(x[i],y[i],z[i])) for i in range(len(x))]
    fh.close()
    
#%% test code
#mesh, meshx, meshy, topo, elec_node = quad_mesh(np.arange(10), np.zeros(10), elemx=4)
#mesh.show(color_bar=False)


# testing automatic selection
#plt.ion()
#from api.SelectPoints import SelectPoints
#from matplotlib.patches import Rectangle
#fig, ax = plt.subplots()
#mesh.show(ax=ax)
#rect = Rectangle([0,0], 1,-2, alpha=0.3, color='red')
#ax.add_artist(rect)
#selector = SelectPoints(ax, np.array(mesh.elm_centre).T, typ='rect')


#mesh, meshx, meshy, topo, elec_node = quad_mesh(np.arange(10), np.zeros(10), elemx=8)
#mesh.show(color_bar=False)

#mesh = vtk_import('api/test/test.vtk')
#mesh = vtk_import('api/invdir/f001_res.vtk')
#attrs = list(mesh.attr_cache)
#fig, ax = plt.subplots()
#mesh.show(attr=attrs[0], contour=True, edge_color='none', color_map='viridis', ax=ax)
#mesh.show(attr=attrs[2])
#mesh.show(attr=attrs[0], color_map='viridis', sens=True, edge_color='none')
#fig.show()

#%%
#x = np.random.randn(100)+10
#y = np.random.randn(100)+10
#z = np.random.randn(100)
#
#triang = tri.Triangulation(x,y)
#fig, ax = plt.subplots()
#ax.tricontourf(triang, z)
#fig.show()


#%%
## First create the x and y coordinates of the points.
#n_angles = 48
#n_radii = 8
#min_radius = 0.25
#radii = np.linspace(min_radius, 0.95, n_radii)
#
#angles = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
#angles = np.repeat(angles[..., np.newaxis], n_radii, axis=1)
#angles[:, 1::2] += np.pi / n_angles
#
#x = (radii * np.cos(angles)).flatten()
#y = (radii * np.sin(angles)).flatten()
#z = (np.cos(radii) * np.cos(3 * angles)).flatten()
#
## Create the Triangulation; no triangles so Delaunay triangulation created.
#triang = tri.Triangulation(x, y)
#
## Mask off unwanted triangles.
#triang.set_mask(np.hypot(x[triang.triangles].mean(axis=1),
#                         y[triang.triangles].mean(axis=1))
#                < min_radius)
#
#fig1, ax1 = plt.subplots()
#ax1.set_aspect('equal')
#tcf = ax1.tricontourf(triang, z)
#fig1.colorbar(tcf)
#ax1.tricontour(triang, z, colors='k')
#ax1.set_title('Contour plot of Delaunay triangulation')
#fig1.show()
#


