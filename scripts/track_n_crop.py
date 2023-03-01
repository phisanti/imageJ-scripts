""" This script is used to track cells in a time series of images and create crops of the cells for further analysis.
    This is useful when tracking more than one object per cell, as it is the case with periplasmic fluorescence.
    The script uses a mask image that feeds into TrackMate to track the cells.
"""

#@ File(label="Input directory", description="Select the directory with input images", style="directory") inputDir
#@ File(label="Output directory", description="Select the output directory", style="directory") outputFolder
#@ File(label="LUT", description="Select the LUT for the image", style="file") LUTpath
#@ Integer(label="Crop width", value=17) crop_width
#@ Integer(label="Crop height", value=37) crop_height

import sys
import csv
import os
from ij import IJ, ImagePlus
from ij.plugin import ChannelSplitter, RGBStackMerge
from ij.io import FileSaver
from ij.gui import WaitForUserDialog, GenericDialog, NonBlockingGenericDialog
from ij.plugin import LutLoader
from fiji.plugin.trackmate import Model
from fiji.plugin.trackmate import Settings
from fiji.plugin.trackmate import TrackMate
from fiji.plugin.trackmate import SelectionModel
from fiji.plugin.trackmate import Logger
from fiji.plugin.trackmate.detection import LogDetectorFactory
from fiji.plugin.trackmate.tracking.sparselap import SparseLAPTrackerFactory
from fiji.plugin.trackmate.tracking import LAPUtils
from fiji.plugin.trackmate.action import CaptureOverlayAction as CaptureOverlayAction
import fiji.plugin.trackmate.features.spot.SpotContrastAndSNRAnalyzerFactory as SpotContrastAndSNRAnalyzerFactory
import fiji.plugin.trackmate.features.spot.SpotIntensityMultiCAnalyzerFactory as SpotIntensityMultiCAnalyzerFactory
import fiji.plugin.trackmate.visualization.hyperstack.HyperStackDisplayer as HyperStackDisplayer
import fiji.plugin.trackmate.features.track.TrackDurationAnalyzer as TrackDurationAnalyzer
import fiji.plugin.trackmate.features.FeatureFilter as FeatureFilter
import fiji.plugin.trackmate.features.track.TrackIndexAnalyzer as TrackIndexAnalyzer
import fiji.plugin.trackmate.features.FeatureFilter as FeatureFilter
import fiji.plugin.trackmate.gui.displaysettings.DisplaySettingsIO as DisplaySettingsIO
from fiji.plugin.trackmate.gui.displaysettings.DisplaySettings import TrackMateObject
from fiji.plugin.trackmate.gui.displaysettings.DisplaySettings import TrackDisplayMode


def grep_file_filter(filesFolder, grep):

    """ Filter mask and files from the source folder
    :param filesFolder: source folder
    :param grep: string to grep in the file name
    :return: list of files and list of masks"""

    files_mask, files_raw = [], []
    for i in filesFolder.listFiles():
            
        if ".tif" in i.getName():
         
            if grep in i.getName():

                files_mask.append(i)
            else:
                files_raw.append(i)
    return files_raw, files_mask

def create_crop_for_a_track(imp, model, tid, w, h, lut):

    """ Create a crop hyperstack from the cource image and the tracking model
    :param imp: source image
    :param model: tracking model
    :param tid: track id
    :param w, h: width and height of the crop
    :param lut: LUT for the crop"""
    
    track = model.getTrackModel().trackSpots(tid)
    track_len = int(model.getFeatureModel().getTrackFeature(tid, 'TRACK_DURATION'))
    n_channels = imp.getDimensions()[2]
    n_slices = imp.getDimensions()[3]
    n_frames = imp.getDimensions()[4]
    crop = IJ.createImage("Celln", "16-bit grayscale-mode", w, h, n_channels, n_slices, n_frames)
    
    cal = imp.getCalibration()
    crop.setCalibration(cal)
    crop.setLut(lut)
    #crop.show()
    
    # first time point of this track
    pos_t0 = min([int(spot.getFeature('POSITION_T')) for spot in track])
    for spot in track:
        pos_x = int(spot.getFeature('POSITION_X') / cal.pixelWidth)
        pos_y = int(spot.getFeature('POSITION_Y') / cal.pixelHeight)
        pos_t = int(spot.getFeature('POSITION_T'))
        frame = int(spot.getFeature('FRAME'))
        IJ.log("FRAME:" + str(frame) + "/" + str(n_frames) + " (x:" +str(pos_x) + ",y:" + str(pos_y)+",t:"+ str(pos_t)+")")
        copy_roi_allzc(imp, crop, pos_x, pos_y, frame, pos_t0, w, h)
        
    return crop
    
def copy_roi_allzc(src, dst, x, y, t, t0, w, h):
    
    """ copy ZC planes from src to dst 
    :param src: source image
    :param dst: destination image
    :param x, y, t: x, y, t coordinate of the ROI
    :param t0: first time point of the track
    :param w, h: width and height of the ROI
    """
    
    IJ.run("Select None")
    nc = src.getNChannels()
    nz = src.getNSlices()
    for z in range(nz):
        for c in range(nc):
            src.setPosition(c+1, z+1, t + 1)
            src.setRoi(x-w/2, y-h/2, w, h)
            src.copy()
            dst.setPosition(c+1, z+1, t + 1)
            IJ.run("Select None")
            dst.paste()
            
    IJ.run("Select None")

def dialog_size_thr(title='Select images for processing', size = 1, thr = 10, df = 500, dist1 = 1, dist2 = 1):

    """ Display a dialog for tracking parameters """
    
    # Defining the dialog
    gd = GenericDialog(title)
    gd.addNumericField("Cell size: ", size, 1)
    gd.addNumericField("Threshold: ", thr, 0)
    gd.addNumericField("Duration filter: ", df, 0)
    gd.addNumericField("LINKING MAX DISTANCE: ", dist1, 0)
    gd.addNumericField("GAP CLOSING MAX DISTANCE: ", dist2, 0)
    gd.showDialog()
    
    if gd.wasCanceled():
        return None
        
    # Extract input values
    
    size = gd.getNextNumber()
    thr = gd.getNextNumber()
    duration = gd.getNextNumber()
    dist1 = gd.getNextNumber()
    dist2 = gd.getNextNumber()

    return [size, thr, duration, dist1, dist2]

def dialog_TrackCheck(title='Repeat tracking analysis?'):

    """ Display a dialog for checking the cell tracks"""

    # Define dialog
    gd = NonBlockingGenericDialog(title)
    gd.enableYesNoCancel("Repeat tracking", "No")
    gd.showDialog()

    # Extract input values

    if gd.wasCanceled():
        sys.exit(0)
    if gd.wasOKed():
        return True
    else:
        return False

def lut_change(imp, lut):

    """ set LUT for improved visualisation 
    :param imp: image to be processed
    :param lut: LUT for visualisation
    """
    nslices = imp.getStackSize()
    dimA = imp.getDimensions()
    
    for i in range(nslices):
        # Iterate through slices
        
        if dimA[2] > 1:
            for ch in range(dimA[2]):
            
            # Iterate through channels
                imp.setSlice(i + 1)
                imp.setChannelLut(lut, ch + 1)
            else:
                imp.getProcessor().setLut (lut)    

def process_image(image, mask, lut, crop_width, crop_height):

    """ Apply track and crop to a single image + mask 
    :param image: image to be processed
    :param mask: mask to be used for tracking
    :param lut: LUT for visualisation
    :param crop_width: width of the crop
    :param crop_height: height of the crop
    :return: True if successful
    """

	# Load images
    experiment = image.getName()[:-4]
    IJ.log("#--------------------- Start analysing movie: ")
    IJ.log("\n original: " + experiment)

    imp0 = IJ.openImage(image.getCanonicalPath())
    imp1 = IJ.openImage(mask.getCanonicalPath())

    #----------------------------
    # Image preparation
    #----------------------------
    
    c1, c2, c3 = ChannelSplitter.split(imp1)
    c3.close()
    
    IJ.run(c1, "16-bit", "")
    IJ.run(c2, "16-bit", "")
    imp_merger = RGBStackMerge()
    Final = imp_merger.mergeChannels([imp0, c1, c2], True)
    n = Final.getNSlices()

    # Transfer image calibration
    
    imp_cal = imp0.getCalibration().copy()
    Final.setCalibration(imp_cal)

    Final.setDisplayMode(IJ.GRAYSCALE)
    IJ.run(Final, "Subtract Background...", "rolling=15 stack")
    imp0.close()
    Final.show()
    lut_change(Final, lut)

    #----------------------------
    # Create the model object now
    #----------------------------

    # Some of the parameters we configure below need to have
    # a reference to the model at creation. So we create an
    # empty model now.
    
    model = Model()

    # Send all messages to ImageJ log window.
    model.setLogger(Logger.IJ_LOGGER)
    logger = Logger.IJ_LOGGER

    #------------------------
    # Prepare settings object
    #------------------------

    run_tracker = True
    while run_tracker:
            
        # Get cell size and pixel threshold
        if 'cell_size' not in locals():
            cell_size = 1 
            threshold = 10
            duration = Final.getStackSize()/(2 * Final.getNChannels() * Final.getNSlices())
            dist1 = 1
            dist2 = 1
            
        cell_size, threshold, duration, dist1, dist2 = dialog_size_thr(size = cell_size,
        thr = threshold, 
        df = duration, 
        dist1 = dist1, 
        dist2 = dist2)
        settings = Settings(Final)
    
        # Configure detector - We use the Strings for the keys
        
        settings.detectorFactory = LogDetectorFactory()
        settings.detectorSettings = { 
            'DO_SUBPIXEL_LOCALIZATION' : True,
            'RADIUS' : cell_size,
            'TARGET_CHANNEL' : 2,
            'THRESHOLD' : threshold,
            'DO_MEDIAN_FILTERING' : True,
            }  
    
        # Configure tracker - We want to allow merges and fusions

        allow_cell_split = False
        settings.trackerFactory = SparseLAPTrackerFactory()
        settings.trackerSettings = LAPUtils.getDefaultLAPSettingsMap() # almost good enough
        settings.trackerSettings['LINKING_MAX_DISTANCE'] = dist1
        settings.trackerSettings['GAP_CLOSING_MAX_DISTANCE'] = dist2
        settings.trackerSettings['MAX_FRAME_GAP'] = 5 #n_slices/10
        settings.trackerSettings['ALLOW_TRACK_SPLITTING'] = allow_cell_split
        settings.trackerSettings['ALLOW_TRACK_MERGING'] = False

        if allow_cell_split:
            settings.trackerSettings['SPLITTING_MAX_DISTANCE'] = 0.25
            
        # Configure track analyzers - Later on we want to filter out tracks 
        # based on their displacement, so we need to state that we want 
        # track displacement to be calculated. By default, out of the GUI, 
        # not features are calculated. 
    
        # The displacement feature is provided by the TrackDurationAnalyzer.
        # Spot analyzer: we want the multi-C intensity analyzer.

        spotIntensityAnalyzer = SpotIntensityMultiCAnalyzerFactory()
        spotIntensityAnalyzer.setNChannels( Final.getNChannels() )
        settings.addSpotAnalyzerFactory( spotIntensityAnalyzer )
        settings.addTrackAnalyzer(TrackDurationAnalyzer())
        settings.addTrackAnalyzer( TrackIndexAnalyzer() )
        snrAnalyzer = SpotContrastAndSNRAnalyzerFactory()
        snrAnalyzer.setNChannels( Final.getNChannels() )
        settings.addSpotAnalyzerFactory( snrAnalyzer )
        
        # Filter out short tracks

        dur_filter = FeatureFilter('TRACK_DURATION', duration, True)
        settings.addTrackFilter(dur_filter)
        
        #-------------------
        # Instantiate plugin
        #-------------------
    
        trackmate = TrackMate(model, settings)

        
        #--------
        # Process
        #--------
    
        ok = trackmate.checkInput()
        if not ok:
            sys.exit(str(trackmate.getErrorMessage()))
        
        ok = trackmate.process()
        if not ok:
            sys.exit(str(trackmate.getErrorMessage()))
        
        #----------------
        # Display results
        #----------------

        selectionModel = SelectionModel(model)
        ds = DisplaySettingsIO.readUserDefault()
        ds.setTrackColorBy(TrackMateObject.TRACKS, 'TRACK_DURATION' )
        ds.setTrackDisplayMode(TrackDisplayMode.LOCAL_BACKWARD)
        ds.setTrackMinMax(duration, n) 
        ds.setFadeTrackRange(n)
        
        displayer =  HyperStackDisplayer(model, selectionModel, Final, ds)
        displayer.render()
        displayer.refresh()
        trackIDs = model.getTrackModel().trackIDs(True)
        t_analyzer = TrackDurationAnalyzer()
        for tid in trackIDs:
            dur = model.getFeatureModel().getTrackFeature( tid, TrackDurationAnalyzer.TRACK_DURATION )
            IJ.log("TRACK_D: " + str(tid) + " TRACK_DURATION: " + str(dur))
                
        run_tracker = dialog_TrackCheck()
    
    # The feature model, that stores edge and track features.
    model.getLogger().log(str(model))
    trackIDs = model.getTrackModel().trackIDs(True) # only filtered out ones

    ndiv = 0
    for tid in trackIDs:

        ndiv += 1
        crop = create_crop_for_a_track(Final, model, tid, crop_width, crop_height, lut)
        lut_change(crop, lut)
               
        outputFileName = experiment + "_celln_" + str(tid) + "_path0" + str(ndiv) + ".tif"
        oname = str(os.path.join(outputFolder.getPath(), outputFileName))
        IJ.log("Saving file " + oname)
        FileSaver(crop).saveAsTiff(oname)
        IJ.saveAs(crop, "Tiff", oname)
        crop.changes = False
        crop.close()

    return True

def process_folder(inputDir, outputFolder, LUTpath, crop_width, crop_height):

    """ Iterate track_n_crop over a folder 
    :param inputDir: input folder
    :param outputFolder: output folder
    :param LUTpath: path to LUT
    :param crop_width: width of the crop
    :param crop_height: height of the crop
    :return: True if successful
    """

    image_list, masks_list = grep_file_filter(inputDir, "_MASK")
    lut = LutLoader.openLut(LUTpath.getCanonicalPath())
    
    for image_i, mask_i in zip(image_list, masks_list):
        
        process_image(image_i, mask_i, lut, crop_width, crop_height)
        image_i.close()
        mask_i.close()
        
    return True

process_folder(inputDir, outputFolder, LUTpath, crop_width, crop_height)

