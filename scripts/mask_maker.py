""" This script is used to clean the image for the segmentation.
    It should help to sharpen the image and remove the background for the segmentation and further tracking"""

from ij import IJ
from ij.plugin import ZProjector, ImageCalculator
imp = IJ.getImage()

def clean_image(imp):
    
    """"Clean the image for the segmentation."""

    # Create duplicates
    IJ.run(imp, "Select None", "")
    img = imp.duplicate()
    img2 = imp.duplicate()

    # Clear image for Zproj
    IJ.run(img, "Subtract...", "value=2000 stack")
    IJ.run(img, "Subtract Background...", "rolling=12.5 stack")
    IJ.run(img, "Despeckle", "stack")
    IJ.run(img, "Enhance Contrast", "saturated=0.35")
    IJ.run(img, "8-bit", "")

    # Zproj and binary
    img_Zave = ZProjector.run(img,"avg")
    IJ.run(img_Zave, "Auto Local Threshold", "method=Phansalkar radius=0.7 parameter_1=0.2 parameter_2=0.1 white stack")
    IJ.run(img, "Remove Outliers...", "radius=5 threshold=50 which=Bright stack")
    IJ.run(img_Zave, "Erode", "")
    ip_Zave = img_Zave.getProcessor()
    ip_Zave.add(-254)

    # Clear image 2
    IJ.run(img2, "Subtract Background...", "rolling=12.5 stack")
    IJ.run(img2, "Gaussian Blur...", "sigma=2 stack")
    ImageCalculator().run( "Multiply  stack", img2, img_Zave)

    # Title and show
    title = imp.getTitle()
    title = title.replace(".tif", "_MASK.tif")
    img2.setTitle(title)
    img2.show()

    return True
      
clean_image(imp)
