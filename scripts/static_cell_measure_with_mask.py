""" This script is used to measure the fluorescence intensity of a set of ROIs in a set of images."""

#@ File(label="Input directory", description="Select the directory with input images", style="directory") inputDir
#@ File(label="Output directory", description="Select the output directory", style="directory") outputFolder
#@ File(label="LUT", description="Select the LUT for the image", style="file") LUTpath

# Load libraries

import os
from ij import IJ
from ij.plugin import , LutLoader
from ij import IJ, WindowManager as WM
from ij.gui import WaitForUserDialog
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable


def lut_change(imp, LUTpath):
    
    """ Change LUT of image"""
    
    # Get image info and LUT 
    lut = LutLoader.openLut(LUTpath.getCanonicalPath())
    nslices = imp.getStackSize()
    nCh = imp.getDimensions()[2]
    
    if nCh == 1:
        # Iterate through slices
        for i in range(nslices):
            imp.setSlice(i + 1)
            imp.setLut(lut)

    else:
        for i in range(nslices):
            # Iterate through slices
            for ch in range(nCh):
            # Iterate through channels
                imp.setSlice(i + 1)
                imp.setChannelLut(lut, ch + 1)
    
    return 0

def grep_file_filter(filesFolder, grep):

    """ Filter mask and files from the source folder
    :param filesFolder: Folder with files
    :param grep: String to grep"""

    files_mask, files_raw = [], []
    for i in filesFolder.listFiles():
            
        if ".tif" in i.getName():
         
            if grep in i.getName():

                files_mask.append(i)
            else:
                files_raw.append(i)
    return files_raw, files_mask

def analyse_movie(image_file, mask_file, rm, outputFolder):
    
    """ Analyse movie
    :param image_file: Image file
    :param mask_file: Mask file
    :param rm: Roi manager
    :param outputFolder: Output folder
    """

    # Open image and ref.
    ref_image = IJ.openImage(mask_file.getCanonicalPath())
    imp = IJ.openImage(image_file.getCanonicalPath())
    
    # Prepare image
    lut_change(imp, LUTpath)
    IJ.run("Set Measurements...", "area mean median standard min centroid stack redirect=None decimal=3")
    IJ.run("Collect Garbage", "")
    IJ.run("Clear Results", "")
    IJ.run(imp, "Subtract Background...", "rolling=15 stack") 
    
    # Generate ROIs
    
    IJ.setThreshold(ref_image, 2, 65535)
    ref_image.createThresholdMask()
    IJ.run(ref_image, "Analyze Particles...", "size=0.5-Infinity circularity=0.10-0.95 add")
    ref_image.close()
    
    
    # Measure ROIs
    rt = ResultsTable.getResultsTable()
    IJ.run("Clear Results", "")
    #ref_image.show()
    imp.show()
    rm.runCommand(imp,"Show All")
    rm.runCommand(imp,"Deselect")
    myWait = WaitForUserDialog ("Are ROIs Ok?", "Add or remove ROIs")
    myWait. show()
    rm.getRoisAsArray()
    rt = rm.multiMeasure(imp)
        
    # Export data
    outputFileName = image_file.getName().replace(".tif", ".csv")
    rt.saveAs(outputFolder.getPath() + "/"+ outputFileName)
       
       # Clean up!
    rm.runCommand(imp,"Deselect")
    rm.runCommand(imp,"Delete")
    IJ.run(imp, "Close All", "")
    imp.close()
    del imp, ref_image, rt
    
    return 0
    
    #----------------------------
    # Loop over images
    #----------------------------

def file_iterator(inputDir, outputFolder):
    
    """ Iterate over files in a folder"""

    files_raw, files_mask = grep_file_filter(inputDir, grep = "MASK")
    
    rm = RoiManager.getInstance()
    
    for image_i, mask_i in zip(files_raw, files_mask):
        IJ.log("# ----------------")
        IJ.log(image_i.getName())
        analyse_movie(image_i, mask_i, rm, outputFolder)
        IJ.log("# ----------------")
    
    return True


file_iterator(inputDir, outputFolder)
