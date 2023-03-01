""" This script changes the LUT of a stack of images to a specified LUT.
To set the script, you need to specify the path to the LUT file.
"""

from ij import IJ
from ij.plugin import LutLoader
import ij.CompositeImage
import java.awt.Color

LUTpath = "C:\Software\Fiji.app\luts\mpl-viridis.lut"
    	
def lut_change(imp, LUTpath):
	# Get image info and LUT 
   lut = LutLoader.openLut(LUTpath)
   nslices = imp.getStackSize()
   dimA = imp.getDimensions()
   
   for i in range(nslices):
   # Iterate through slices
       for ch in range(dimA[2]):
       # Iterate through channels
           imp.setSlice(i + 1)
           imp.setChannelLut(lut, ch + 1)
     
imp = IJ.getImage()
lut_change(imp, LUTpath)
imp.show()
