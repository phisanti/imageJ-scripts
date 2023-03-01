""""This script will divide each slice of a stack by the mean of that slice.
It will then apply a colormap to the image. This is useful for normalising
signal intensity in a stack of images. 
"""

from ij.gui import NewImage
from ij.plugin import LutLoader
from ij import IJ

imp = IJ.getImage()

def fl_normaliser(imp):
    """This function will divide each slice of a stack by the mean of that slice."""

    # Load the colormap and get stack
    lut = LutLoader.openLut ("D:\Desktop\Fiji.app\luts\mpl-magma.lut")
    stack = imp.getStack()
    
    # Iterate through each slice and divide by the mean
    n =stack.size()
    for i in range(n):
        stats = imp.getStack().getProcessor(i + 1).getStatistics()
        imp.setSlice(i + 1)
        imp.getProcessor().setLut (lut)
        IJ.run(imp, "Divide...", "value=" + str(stats.mean) )

    imp.show()

    return True
