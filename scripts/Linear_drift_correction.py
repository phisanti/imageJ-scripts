from ij.gui import NewImage
from ij import IJ

def drift_correction(imp):
	
    """Drift correction for images stack where the object displace linearly in one direction.
    :param imp: ImagePlus object
    """

	stack = imp.getStack()
	n =stack.size()
	for i in range(n):
		x = -i * 0.01
		y = -i * 0.01
		imp.setSlice(i + 1)
		IJ.run(imp, "Translate...", "x=" + str(x) +" y=" + str(y) + " interpolation=None slice");

	imp.show()

	return True

imp = IJ.getImage()
drift_correction(imp)
