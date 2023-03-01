""" This script is used to classify bacteria in a stack of images using a Weka Machine Learning model.
"""
#@ File(label="Input directory", description="Select the directory with input images", style="directory") inputDir
#@ File(label="Output directory", description="Select the output directory", style="directory") outputFolder
#@ File(label="Weka model", description="Select the Weka model to apply") modelPath

# Load libraries

from loci.plugins import BF
from ij import IJ
from ij.plugin import Duplicator, ZProjector, ImageCalculator
from ij import ImagePlus, IJ, io, plugin, ImageStack, WindowManager as WM
from trainableSegmentation import WekaSegmentation
from ij.gui import WaitForUserDialog
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable
from ij.io import FileSaver 

# Load variables

listOfFiles = inputDir.listFiles()
weka = WekaSegmentation()
weka.loadClassifier( modelPath.getCanonicalPath() )

for i in range(0, len(listOfFiles)):  # Loop over files

    files = listOfFiles[i].getCanonicalPath()
    imps = BF.openImagePlus(files) # Open images
    print(listOfFiles[i].getName()) # indicate current image in analysis

    for image in imps:
    
        IJ.run(image, "Subtract Background...", "rolling=15 stack") # Remove background
        IJ.run(image, "Align HyperStack", "max=50")
        inputStack = image.getImageStack() 
        dupStack = inputStack.duplicate()
        
        dupStack = ImagePlus("Reference_image", dupStack)
        
        # Generate Z-Project
        
        project = ZProjector()
        project.setMethod(ZProjector.MAX_METHOD)
        project.setImage(dupStack)
        project.doProjection()
        impout = project.getProjection()
        IJ.run(impout, "Subtract Background...", "rolling=15 stack") # Remove background

        # Find edges
        
        IJ.run(impout, "8-bit", "")
        IJ.run(impout, "Sharpen", "")
        IJ.run(impout, "Enhance Contrast...", "saturated=0.1")
        edges = impout.duplicate()
        IJ.run(edges, "Canny Edge Detector", "gaussian=1 low=2.5 high=7.5")
        IJ.run(edges, "Divide...", "value=2")
        
        # Combine images in one for classification
        
        impout = ImageCalculator().run("Add create", impout, edges)
        result = weka.applyClassifier( impout, 0, True)
        result = result.getProcessor().duplicate()
        result = ImagePlus("Bacteria_Prob_map", result)

        # Transform in binary
        
        IJ.run(result, "8-bit", "")
        result.getProcessor().threshold(130)
        result.updateAndDraw()
        
        project.setImage(dupStack)
        project.doProjection()
        impout = project.getProjection()
        IJ.run(result, "Set Scale...", "distance=6.3802 known=1 unit=micron")

        
        image.show()
        impout.show()
        result.show()
        IJ.run(result, "Invert", "")
        IJ.run(result, "Analyze Particles...", "size=1.50-5.00 circularity=0.40-0.90 
        myWait = WaitForUserDialog ("Select ROIS", "Click Ok when all ROIS are selected")
        myWait.show()

        # Measure ROIs
        
        rm = RoiManager.getInstance()
        rt = ResultsTable.getResultsTable()
        IJ.run("Clear Results", "")
        rm = RoiManager.getInstance()
        rt = rm.multiMeasure(image)
        
        # Generate mask with measured cells
        IJ.run(result, "Invert", "")
        ip = result.getProcessor()
        index = 0
        for roi in RoiManager.getInstance().getRoisAsArray():
                index = index + 1
                ip.setRoi(roi)  
                ip.setColor(index)
                ip.fill(roi)
        ip.resetMinAndMax()
        result.updateAndDraw()
        IJ.run(result, "glasbey", "")
        result = result.flatten()
        result.show()

        # Save results
        outputFileName = "Mask_" + listOfFiles[ i ].getName() + ".tif"  
        FileSaver(result).saveAsTiff(outputFolder.getPath() + "/"+ outputFileName)
        
        outputFileName = listOfFiles[ i ].getName() + ".txt"
        rt.saveAs(outputFolder.getPath() + "/"+ outputFileName)
        # Clean up!
        del index, impout, dupStack, edges, imps, result, rm, rt, roi
        IJ.run(image, "Close All", "")
