"""Generator of a training set stack

Tool aiming to generate a subset stack from a group of movies for
further training on WEKA, TF, or iLastik. The script creates a random sample of images
and saves them as separate stack to train on.

"""

#@ File(label="Output directory", description="Select the output directory", style="directory") filesFolder

import random
from ij import IJ

def sample_slices(imp, stack_size, n_samples, imp_out, last_count):

	"""Sample N slices from a ImagePlus

	imp: reference imagePlus
	stack_size: number of slices in the stack
	n_samples: total number of slices to subset
	imp_out: imagePlus to collect the output
	last_count: number of iterations in the loop
	"""

	sample_slices = [random.randrange(1, stack_size) for x in range(n_samples)]
	n = 1 + last_count
	for i in sample_slices:
		print("Paste Slice: " + str(i))
		imp.setSlice(i)
		IJ.run("Select None")
		imp.copy()
		imp_out.setSlice(n)
		IJ.run("Select None")
		imp_out.paste()
		n += 1

	return True

def process_folder(folder, n_samples, dimx = 512, dimy = 512):
	
	"""Folder iterator
	folder: folder list from ImageJ
	n_samples: total number of slices to subset, argument passed onto sample_slices
	dimx: X-axis image dimension
	dimy: Y-axis image dimension
	"""

	# Filter movies with target extension
	fil_list = [l for l in filesFolder.listFiles() if ".tif" in str(l)]
	n_movies = len(fil_list)

	# Set variables (imagePlus out and last slice counter)
	imp_out = IJ.createImage("training_set", "8-bit black", dimx, dimy, n_samples * n_movies)	
	n = 0
	
	for file_i in fil_list:
		last_count = n * n_samples
		imp0 = IJ.openImage(file_i.getAbsolutePath())
		imp_dim = imp0.getDimensions()	
		stack_size = imp_dim[4]
		sample_slices(imp0, stack_size, n_samples, imp_out, last_count)
		imp0.close()
		imp_out.show()
		n += 1
	return True

process_folder(filesFolder, 15)
