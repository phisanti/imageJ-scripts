
"""Auto Loca Threshold explorer

    This plugin helps to explore different parameter combinations for
    the auto local threshold plugin.

    The interface takes the same input of the auto local threshold tool
    and generates a sequence of n-steps for each parameter. Then, it builds
    a montage with every combination of the parameters sequences.
    
"""

import itertools
from ij import IJ, ImageStack, ImagePlus
from ij.gui import GenericDialog
from fiji.threshold import Auto_Local_Threshold as ALT

imp = IJ.getImage()

def range_float(start, end, step):

    """Range float generator
    Helper fuction to generate sequences of float point numbers.
    """

    out = []
    increment = (end - start)/step
    
    for i in range(int(step + 1)):
        out.append((increment * i) + start) 
        
    return(out)

def range_parameters(param_set):

    """Generate range numbers for each parameter
    Helper fuction to generate sequences of parameters.
    """
    p1range = range_float(param_set['p1min'], param_set['p1max'], param_set['p1steps'])
    p2range = range_float(param_set['p2min'], param_set['p2max'], param_set['p2steps'])
    
    return [param_set['Filter'], param_set['radius'], p1range, p2range]

def getSettings(img):

    """Dialog interface
    Creates the original dialog for the local threshold explorer.
    """

    canProceed = True
    filter_names = ["Bernsen", "Contrast", "Mean", "Median", "MidGrey", "Niblack","Otsu", "Phansalkar", "Sauvola"]

    if not img:
        IJ.error("No images open.")
        canProceed = False
        
    # Get new values if at least one of the parameters is 'null'
    if canProceed:
        
        gd = GenericDialog("Filter explorer")
        gd.addChoice("Filter", filter_names, "Phansalkar")
        gd.addNumericField("Radius:", 15, 0)

        gd.addNumericField("Parameter 1, Min:", 0, 2)
        gd.addToSameRow()
        gd.addNumericField("Max:", 5, 2)
        gd.addToSameRow()
        gd.addNumericField("Steps:", 2, 0)

        gd.addNumericField("Parameter 1, Min:", 0, 2)
        gd.addToSameRow()
        gd.addNumericField("Max:", 5, 2)
        gd.addToSameRow()
        gd.addNumericField("Steps:", 2, 0)

        gd.showDialog()
        
    if gd.wasCanceled():
        return None
    
    else:
        filter_choice = gd.getNextChoice()
        radius = gd.getNextNumber()

        p1min = gd.getNextNumber()
        p1max = gd.getNextNumber()
        p1steps = gd.getNextNumber()
        p2min = gd.getNextNumber()
        p2max = gd.getNextNumber()
        p2steps = gd.getNextNumber()
        
        return {"Filter" : filter_choice, "radius" : radius, 
                "p1min" : p1min, "p1max" : p1max, "p1steps" : p1steps, 
                "p2min" : p2min, "p2max" : p2max, "p2steps" : p2steps}

def range_autolocalthr(imp, p_range):

    """Local thresholder
    Iterates over the different parameters and generates
    the thresholded images.
    """
    
    ip = imp.getProcessor()
    if ip.getBitDepth() is not 8:
    	 ip = ip.convertToByteProcessor()
    	
    radius = p_range[1]
    x, y = imp.getDimensions()[0], imp.getDimensions()[1]
    tstack = ImageStack(x, y)
    
    for p1, p2 in itertools.product(p_range[2], p_range[3]):
    
        label = "p1 = " + str(p1) + " p2 = " + str(p2)
        imp2 = ImagePlus(label, ip.duplicate())
        thimp = ALT().exec(imp2, p_range[0], int(radius), p1, p2, True)
        tstack.addSlice(label, imp2.getProcessor())
        
    montage = ImagePlus("Montage", tstack)
    IJ.run(montage, "Make Montage...", "columns=" + 
              str(len(p_range[2])) + " rows=" + 
              str(len(p_range[3])) + " scale=0.25 border=2 label")
    
    return None

parameters = getSettings(imp)
p_range = range_parameters(parameters)
i_stack = range_autolocalthr(imp, p_range)
