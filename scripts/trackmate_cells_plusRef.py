""" This script is used to track cells in a time-lapse image series. The script is based on the TrackMate plugin for ImageJ/Fiji.
    The script requires an input mask where the cells have been cleaned up and the original image to measure fluorescence intensity
    and other variables. The script will show track the cells with the provided parameters and allow to check the tracks are correct.
    If so, the output will be a csv file with the tracks and the fluorescence intensity of the cells.
    NOTE: THIS SCRIPT USES TRACKMATE 7.5. THE CHANGES INTRODUCED IN THIS VERSION BROKE THE PREVIOUS SCRIPT.
"""

#@ File(label="Input directory", description="Select the directory with input images", style="directory") inputDir
#@ File(label="Output directory", description="Select the output directory", style="directory") outputFolder
#@ File(label="LUT", description="Select the LUT for the image", style="file") LUTpath

import sys
import csv
from ij import IJ
from ij.plugin import Zoom
from ij.gui import WaitForUserDialog, GenericDialog, NonBlockingGenericDialog
from ij.plugin import LutLoader
from ij.plugin.frame import RoiManager
from fiji.plugin.trackmate import Model
from fiji.plugin.trackmate import Settings
from fiji.plugin.trackmate import TrackMate
from fiji.plugin.trackmate import SelectionModel
from fiji.plugin.trackmate import Logger
from fiji.plugin.trackmate.detection import LogDetectorFactory
from fiji.plugin.trackmate.tracking import LAPUtils
from fiji.plugin.trackmate.tracking.sparselap import SparseLAPTrackerFactory
from fiji.plugin.trackmate.gui.displaysettings import DisplaySettingsIO
import fiji.plugin.trackmate.visualization.hyperstack.HyperStackDisplayer as HyperStackDisplayer
import fiji.plugin.trackmate.features.FeatureFilter as FeatureFilter
import fiji.plugin.trackmate.features.track.TrackDurationAnalyzer as TrackDurationAnalyzer
import fiji.plugin.trackmate.features.track.TrackIndexAnalyzer as TrackIndexAnalyzer
import fiji.plugin.trackmate.features.spot.SpotContrastAndSNRAnalyzerFactory as SpotContrastAndSNRAnalyzerFactory
import fiji.plugin.trackmate.features.spot.SpotIntensityMultiCAnalyzerFactory as SpotIntensityMultiCAnalyzerFactory
import fiji.plugin.trackmate.gui.displaysettings.DisplaySettingsIO as DisplaySettingsIO
from fiji.plugin.trackmate.gui.displaysettings.DisplaySettings import TrackMateObject
from fiji.plugin.trackmate.gui.displaysettings.DisplaySettings import TrackDisplayMode

    #----------------------------
    # Define interactive dialogs
    #----------------------------
def dialog_size_thr(title='Select images for processing', size = 1, thr = 10, df = 500, dist1 = 1, dist2 = 1):

    """ Display a dialog for tracking parameters
    :param title: title of the dialog
    :param size: cell size in units.
    :param thr: threshold
    :param df: duration filter to remove short tracks
    :param dist1: linking max distance
    :param dist2: gap closing max distance
    :return: tracking_settings: dictionary with tracking parameters"""
    
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

    tracking_settings = {'size' : size,
                         'thr' : thr, 
                         'duration' : duration, 
                         'dist1' : dist1,
                         'dist2' : dist2}
    
    return tracking_settings

def dialog_TrackCheck(title='Repeat tracking analysis?'):

    """ Display a dialog to check tracks are correct """
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
        
def lut_change(imp, LUTpath):

    """ Change LUT to improve visibility 
    :param imp: image to change LUT
    :param LUTpath: path to LUT
    """

    # Get image info and LUT 
    lut = LutLoader.openLut(LUTpath.getCanonicalPath())
    nslices = imp.getStackSize()
    dimA = imp.getDimensions()
    
    for i in range(nslices):
        # Iterate through slices
        for ch in range(dimA[2]):
            # Iterate through channels
            imp.setSlice(i + 1)
            imp.setChannelLut(lut, ch + 1)
            
    return True

def zoom_image(imp, n_times):

    """ Zoom image for improve visibility
    :param imp: image to zoom
    :param n_times: number of times to zoom
    """
    z = Zoom()
    for i in range(n_times):
        z.in(imp)

    return True

def process_image(imp, ref_channel = 3, outputFolder = outputFolder, tracking_settings = {}):

    """ Process image to track cells and measure fluorescence intensity
    :param imp: image to process
    :param ref_channel: channel to use as reference
    :param outputFolder: output folder
    :param tracking_settings: dictionary with tracking parameters"""

    # Create file with results
    experiment = imp.getTitle()[:-4]
    outpath = outputFolder.getPath() + "/"+ experiment + ".csv"
    with open(outpath, 'wb') as resultFile:

        row_headings = ['TRACK_ID','QUALITY','POSITION_X','POSITION_Y', 'POSITION_T','FRAME', 'MEAN_MASK',
                            'MEAN_INTENSITY', 'STANDARD_DEVIATION','CONTRAST','SNR', 'REF']

        csvWriter = csv.DictWriter(resultFile, row_headings, delimiter=',', quotechar='|')
        csvWriter.writeheader()
        
        # Sharpen borders
        
        IJ.run(imp, "Subtract Background...", "rolling=20 stack")
        rm = RoiManager.getRoiManager()
        imp.show()   
        zoom_image(imp, 10)

        
        lut_change(imp, LUTpath)
        IJ.run(imp, "Enhance Contrast", "saturated=0.35")
        if rm.getCount() == 0:
            IJ.run(imp, "Select All", "")
            rm.addRoi(imp.getRoi())
            
        ra = rm.getRoisAsArray()[0]
        IJ.run("Select None", "")
    
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
        
        nSlices = imp.getDimensions()[4]
        if len(tracking_settings) == 0:
            
            tracking_settings = {'size' : 1.2, 
                                 'thr' : 100, 
                                 'duration' : nSlices/2, 
                                 'dist1' : 2,
                                 'dist2' : 2}
        
        run_tracker = True
        while run_tracker:
                        
            tracking_settings = dialog_size_thr(size = tracking_settings['size'],
            thr = tracking_settings['thr'], 
            df = tracking_settings['duration'], 
            dist1 = tracking_settings['dist1'], 
            dist2 = tracking_settings['dist2'])
            
            settings = Settings(imp)
        
            # Configure detector - We use the Strings for the keys
            
            settings.detectorFactory = LogDetectorFactory()
            settings.detectorSettings = { 
                'DO_SUBPIXEL_LOCALIZATION' : True,
                'RADIUS' : tracking_settings['size'],
                'TARGET_CHANNEL' : 3,
                'THRESHOLD' : tracking_settings['thr'],
                'DO_MEDIAN_FILTERING' : True,
                }  
        
            # Configure tracker - We want to allow merges and fusions
        
            settings.trackerFactory = SparseLAPTrackerFactory()
            settings.trackerSettings = LAPUtils.getDefaultLAPSettingsMap() # almost good enough
            settings.trackerSettings['LINKING_MAX_DISTANCE'] = tracking_settings['dist1']
            settings.trackerSettings['GAP_CLOSING_MAX_DISTANCE'] = tracking_settings['dist2']
            settings.trackerSettings['MAX_FRAME_GAP'] = nSlices/20
            settings.trackerSettings['ALLOW_TRACK_SPLITTING'] = False
            settings.trackerSettings['ALLOW_TRACK_MERGING'] = False
        
            # Configure track analyzers - Later on we want to filter out tracks 
            # based on their displacement, so we need to state that we want 
            # track displacement to be calculated. By default, out of the GUI, 
            # not features are calculated. 
        
            # The displacement feature is provided by the TrackDurationAnalyzer.
            # Spot analyzer: we want the multi-C intensity analyzer.
            
            spotIntensityAnalyzer = SpotIntensityMultiCAnalyzerFactory()
            spotIntensityAnalyzer.setNChannels( imp.getNChannels() )
            settings.addSpotAnalyzerFactory( spotIntensityAnalyzer )
            settings.addTrackAnalyzer(TrackDurationAnalyzer())
            settings.addTrackAnalyzer( TrackIndexAnalyzer() )
            snrAnalyzer = SpotContrastAndSNRAnalyzerFactory()
            snrAnalyzer.setNChannels( imp.getNChannels() )
            settings.addSpotAnalyzerFactory( snrAnalyzer )
            
            # Filter out short tracks
    
            dur_filter = FeatureFilter('TRACK_DURATION', tracking_settings['duration'], True)
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
            ds.setTrackMinMax(tracking_settings['duration'], nSlices) 
            ds.setFadeTrackRange(nSlices)
            
            displayer =  HyperStackDisplayer(model, selectionModel, imp, ds)
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
        for id in trackIDs:
            
            # Fetch the track feature from the feature model.
            
            track = model.getTrackModel().trackSpots(id)
            for spot in track:
                sid = spot.ID()
                # Fetch spot features directly from spot. 
                x = spot.getFeature('POSITION_X')
                y = spot.getFeature('POSITION_Y') 
                pos_t = spot.getFeature('POSITION_T')
        
                t = spot.getFeature('FRAME')
                q = spot.getFeature('QUALITY')
                mean = spot.getFeature('MEAN_INTENSITY_CH1')
                mean_mask = spot.getFeature('MEAN_INTENSITY_CH2')
                    
                std = spot.getFeature('STD_INTENSITY_CH1')
                contrast = spot.getFeature('CONTRAST_CH1')
                snr = spot.getFeature('SNR_CH1')
                imp.setPosition(1, 1, int(t))
                processor = 2 * (t) + 1
                ip = imp.getProcessor()
                ip.setRoi(ra)
                stats = ip.getStatistics()

                # Write results
                row = {'TRACK_ID' : id,
                        'QUALITY' : q,
                        'POSITION_X' : x,
                        'POSITION_Y' : y, 
                        'POSITION_T' : pos_t,
                        'FRAME' : t, 
                        'MEAN_MASK' : mean_mask,
                        'MEAN_INTENSITY' : mean, 
                        'STANDARD_DEVIATION' : std, 
                        'CONTRAST' : contrast,
                        'SNR' : snr, 
                        'REF' : stats.mean}
                csvWriter.writerow(row)

        resultFile.close()
        IJ.run("Close All", "")
        rm.runCommand("Delete")
        imp.close()

        return tracking_settings

def process_forlder(inputDir, outputFolder):

    """Process all images in a folder.
    :param inputDir: the input folder.
    :param outputFolder: the output folder.
    """
    
    tracking_settings = {}
    for file_i in inputDir.listFiles():
        
        if '.tif' in file_i.getCanonicalPath():
            imp = IJ.openImage(file_i.getCanonicalPath())
            experiment = file_i.getName()
        
            print("#--------------------- Start analysing movie: ")
            print("\n original: " +experiment)
        
            tracking_settings = process_image(imp, 
                                          ref_channel = 3, 
                                          outputFolder = outputFolder, 
                                          tracking_settings = tracking_settings)

    return True

process_forlder(inputDir, outputFolder)
