"""Combine and merge Zeiss 780 CIP movies

This code gets a group of movies to extract the CIP channel,
then, run a Z-projection, stack aligment and finally concatenate 
all the movies.

"""

#@ File(label="Output directory", description="Select the output directory", style="directory") outputFolder

import os
from ij import IJ, WindowManager
from ij.io import FileSaver
from ij.gui import GenericDialog
from ij.plugin import Concatenator, ChannelSplitter, ZProjector

def sort_imges(section_filter = "part0"):
    
    """Sort images by section number
    :param section_filter: string to filter the images by section"""
    
    image_titles = WindowManager.getImageTitles()
    n_images = len(image_titles)

    if n_images > 1:
        sorted_titles = []
        
        for i in range(1, n_images + 1):
            if i < 10:
                target = section_filter + str(i)
            else:
                target = section_filter[:-1] + str(i)
            
            image_i = filter(lambda x: target in x, image_titles)
            
            sorted_titles.append(image_i[0])
    else:
        sorted_titles = image_titles
    return sorted_titles

def create_title(images_list, section_filter = "part"):
    
    """Create a title for the final image"""
    
    title = images_list[0]
    replace_string = "_" + section_filter + ".czi"
    title = title.replace(replace_string, "")
    return title

def concat_commad(images_list, show_image = False):
    
    """Concatenate images in a list
    :param images_list: list of images to concatenate
    :param show_image: boolean to show the final image
    """

    image_title = create_title(images_list)
    n = len(images_list)
    security_count = 0
    while len(images_list) > 0 and n > 1 and security_count < (n + 5):
        security_count = security_count + 1
        if len(images_list) == n:
            print("Concat:" + images_list[0][-9:] + " and " + images_list[1][-9:])
            imp1 = WindowManager.getImage(images_list[0])
            imp2 = WindowManager.getImage(images_list[1])
            final_image = Concatenator.run(imp1, imp2)
            images_list.remove(images_list[0])
            images_list.remove(images_list[0])

        else:
            print("Concat:" + images_list[0][-9:])
            imp2 = WindowManager.getImage(images_list[0])
            final_image = Concatenator.run(final_image, imp2)
            images_list.remove(images_list[0])

    if len(images_list) == 1:
        final_image = IJ.getImage()
    
    final_image.setTitle(image_title)

    if show_image:
        final_image.show()
    return final_image

def split_and_project(imp, show_image = False):

    """Split and project the image"""

    c_cip, c_dic = ChannelSplitter.split(concat_image)
    c_cip = ZProjector.run(c_cip, "max all")
    n = c_cip.getStack().getSize()
    #IJ.run(c_cip, "Align slices in stack...", "method=5 windowsizex=1650 windowsizey=198 x0=250 y0=133 swindow=0 subpixel=true itpmethod=1 ref.slice=" + str(n) +" show=false")

    if show_image:
        
        c_cip.show()
    return c_cip

def imagep_tifsaver(imp, outputFolder):

    """Save the image as a tif file"""
    
    title = imp.getTitle()
    title = title.replace("MAX_C1-", "")
    outputFileName = title.replace("CIP100", "CIP100_maxZ.tif")
    oname = str(os.path.join(outputFolder.getPath(), outputFileName))
    print("Saving file " + oname)
    FileSaver(imp).saveAsTiff(oname)

concat_image = concat_commad(sort_imges(section_filter = "part0"), show_image = False)
final = split_and_project(concat_image, show_image = True)
imagep_tifsaver(final, outputFolder)
IJ.run("Collect Garbage", "")
