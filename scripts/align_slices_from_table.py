#@ ImagePlus imp

from ij import IJ
from ij.measure import ResultsTable

def align_slices(imp):
	
    """Aligns slices of a stack to the first slice using the results of the
    :param imp: ImagePlus object of the stack to be aligned"""

	results = ResultsTable.getResultsTable()
	table_size = results.size()

	for i in range(table_size):
		sl = results.getColumn(0)[i]
		dx = results.getColumn(1)[i]
		dy = results.getColumn(2)[i]
		imp.setSlice(int(sl))
		IJ.run(imp, "Translate...", "x=" + str(dx) + " y=" + str(dy) + " interpolation=None slice")
	
	return True
