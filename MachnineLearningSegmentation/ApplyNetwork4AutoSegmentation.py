# -*- coding: utf-8 -*-
"""
Created on Tue May 19 14:46:49 2020

@author: Philipp
"""

import os
import cv2
import glob 
import tkinter as tk
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from PIL import Image  
from pathlib import Path
from tensorflow import keras
from tkinter.filedialog import askdirectory, askopenfilename 

# =============================================================================
# I/O Functions
# =============================================================================
# =============================================================================
# def find_ovd_thickness(mask) :
#     """
#     Evaluates the OVD thickness, based on UNets prediction of the mask 
#     """
#     dims = np.shape(mask)
#     
#     return thickness
# =============================================================================
    
# =============================================================================
# Functions for inference, i.e. apply prediction on raw scans
# =============================================================================
class AutoSegmentation() :
    
    def __init__(self, net_dims, raw_dims, output_dims) :
        self.net_dims = net_dims
        self.raw_dims = raw_dims
        self.output_dims = output_dims  
        
    def load_data_from_folder(self) :
        """
        Primitive to load *.bmp-files of OCT b-Scans generated by ZEISS RESCAN
        """
        path = askdirectory(title='Please select data for segmentation', mustexist=True)
        # check if path contains images
        assert any(fname.endswith('.bmp') for fname in os.listdir(path)), "Directory [DOES NOT CONTAIN ANY IMAGES] / *.BMP-files!"
        scan_list = glob.glob(os.path.join(path, "*.bmp"))
        # sort list after b-Scan #'s in image file names
        scan_list.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        # Load (ONLY) b-Scans (with size = IMG_HEIGHT x IMG_WIDTH)
        scans = [np.asarray(Image.open(infile)) for infile in scan_list if np.shape(np.asarray(Image.open(infile))) == (self.raw_dims[0],self.raw_dims[1])]
        
        return np.dstack(scans), path
        
    def resize_img_stack(self, images, out_dims) :
        """
        Primitive to reshape image data stack and return as a 3D numpy-array
        """
        assert images.ndim == 3, "[IMAGE RESIZING ERROR] Wrong dimensionality of image data!"
        in_dims = np.shape(images)
        #print(f"Reshaping images from {in_dims} to {out_dims}...")
        images = [cv2.resize(images[:,:,i], 
                             (out_dims[0], out_dims[1]), 
                             interpolation = cv2.INTER_AREA) for i in range(in_dims[2])]
        
        return np.dstack(images)
        
    def apply_trained_net(self, scans, apply_median_filter=True, is_fixed_path_to_network=True) :
        """
        Predict and display segmented b-Scans -> Display to user
        """
        assert scans.ndim == 3, "[PREDICTION ERROR - IMAGE SIZE] - please check image data!"
        scans = self.resize_img_stack(scans, (self.net_dims[0], self.net_dims[1], scans.shape[2]))
        if is_fixed_path_to_network:
            path = r'C:\Users\Philipp\Desktop\Network_Melli\current_best_model_version9_30602020_1413_acc9984'
        else:
            path = askopenfilename(title='Plese select file with trained net for [AUTO-SEGMENTATION]')          
        model = keras.models.load_model(path)
        predictions = np.squeeze(model.predict(np.expand_dims(np.rollaxis(scans, 2), axis=-1), verbose=1))
        
        #TODO: Write if condition to apply median-filter to probability maps
        #filtered_images = []
        
        #Threshold the masks for area-prediction
        masks = (predictions > 0.5).astype(np.uint8)
        masks = np.moveaxis(masks, 0, -1)
        
        return masks
        
    def check_predicted_masks(self, scans, masks, path) :
        """
        Sort and check if automatically segmented b-Scans were segmented correctly
        """
        
        # TODO: Add handle for start-index in loop if sorting was interrupted
        # TODO: Add handle to check if same scan was good and bad -> logic
        # TODO: Add another assertion to handle dimesionality of arrays
        #assert np.shape(scans)[2] == np.shape(masks)[2], "Number of masks does not match the number of scans"
        mask_prob = 2
        
        masks = np.moveaxis(masks, 2, -1)
        path_good = os.path.join(path, 'CorrectScans')
        Path(path_good).mkdir(parents=True, exist_ok=True)
        path_bad = os.path.join(path, 'IncorrectScans')
        Path(path_bad).mkdir(parents=True, exist_ok=True)
        print("Created paths for sorting")
        print("Please review automatically segmented images...")   
        scans = self.resize_img_stack(scans, (self.output_dims[0], self.output_dims[1]))
        masks = self.resize_img_stack(masks[:,:,:,mask_prob], (self.output_dims[0], self.output_dims[1]))        
        print(np.shape(masks))
        for im in range(np.shape(scans)[2]):
             plt.imshow(scans[:,:,im], 'gray', interpolation='none')
             plt.imshow(masks[:,:,im], 'jet', interpolation='none', alpha=0.33)
             plt.title("Overlay of predicted mask and original b-Scan")
             #mng = plt.get_current_fig_manager()
             #mng.window.showMaximized()
             plt.show()
             plt.pause(0.25)
             key = input("Please press \"y\" if scan was segmented correctly and \"n\" if not  ")
             if key == 'y':
                 plt.imsave(os.path.join(path_good, str(im) + '.png'), masks[:,:,im]) 
             elif key == 'n':
                 plt.imsave(os.path.join(path_bad, str(im) + '.png'), masks[:,:,im])
             else:
                 raise ValueError("You have hit the wrong key...")
             plt.clf()
     
        print("Done displaying images!")
        
if __name__ == '__main__' :
    AS = AutoSegmentation((512,512), (1024,512), (1024,1024))
    scans, path = AS.load_data_from_folder()
    masks = AS.apply_trained_net(scans)
    AS.check_predicted_masks(scans, masks, path)
    
    
# =============================================================================
# TBD if deprecated - functions based on 1-channel UNet segmenation
# =============================================================================
# Thickness evaluation
def find_boundaries_in_mask(mask, w):
    """
    Primitive to find the boundaries of the OVD area in a binary mask
    >>> returns 3-element tuple containing the boundary spots
    """
    # add logic to move from bin-entries to (0,1)
    # TODO: write a function for conversion: like, convert_to_uint8()
    boundary_tuple = []
    for i in range(w):
        start_cornea = np.where(mask[:,i]==255)
        start_cornea = np.squeeze(np.dstack(start_cornea))
        if start_cornea.size != 0:
            start_cornea = np.amin(start_cornea)
            spots = np.squeeze(np.stack(np.argwhere(mask[:,i]==0)))
            spots = np.split(spots, np.where(np.diff(spots) != 1)[0]+1)
            assert np.size(spots) == 2, "No second layer detected"
            end_cornea = spots[1][0]
            start_ovd = spots[1][-1]
            boundary_tuple.append([start_cornea, end_cornea, start_ovd])
        else: 
            boundary_tuple.append([0, 0, 0])
            
    return np.asarray(np.squeeze(np.dstack(boundary_tuple)))

def calculate_thicknes_of_OVD(mask):
    """
    Primitive to calculate the thickness of a b-Scans'/masks' OVD-layer
    - applys logic on a a-Scan basis (i.e. column-wise)
    >>> returns the thickness of the OVD-layer in pixels, 
    1023 if no OVD was marked in mask, i.e. MAX PNT or MAX THICKNESS
    and -1 if invalid point, i.e. if no structure/cornea was visible in a-Scan
    """
    height, width = np.shape(mask)[0], np.shape(mask)[1] #[h,w]
    boundary_tuple = find_boundaries_in_mask(mask, width)
    thickness = []
    for i in range(width):
        if boundary_tuple[2,i] == 0: #invalid thickness
            thickness.append(-1)
        elif boundary_tuple[2,i] == (height-1): # max thickness
            thickness.append(1023)
        else: # regular thickness
            thickness.append(boundary_tuple[2,i]-boundary_tuple[1,i])        
    
    return np.asarray(thickness)

def generate_thickness_maps(volume, path=r'C:\Users\Philipp\Desktop\MaskTestPython'):
    #TODO: change path to were you loaded the data from
    size = np.size(volume)
    thickness_map = [calculate_thicknes_of_OVD[:,:,i] for i in size[2]]
    full_path = os.path.join(path,'thickness_map.mat')
    sio.savemat(full_path, {'thickness_map':thickness_map})
    print(f"Created and saved OVD-thickness-map to *.matfile >>{full_path}<<")  