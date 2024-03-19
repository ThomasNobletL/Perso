# -*- coding: utf-8 -*-
"""
Created on Sat Feb 10 22:46:56 2024

@author: Thomas
"""
import numpy as np

def normalize (Raw_Image):
    """

    Parameters
    ----------
    Raw_Image : Raw Data Array 

    Returns
    -------
    Raw_Image : Normalized Data Array in grey values.

    """
    min_val = Raw_Image.min()
    max_val = Raw_Image.max()
    if max_val > min_val:
        Raw_Image = ((Raw_Image - min_val) / (max_val - min_val)) * 255
        Raw_Image = Raw_Image.astype(np.uint8)
    
    return Raw_Image 

def triangle_scanning (Image, Pixel_Size):
    """
    In case of a triangle scanning, this function invert one line over 2 to
    obtain the right Image.
    
    Parameters
    ----------
    Image : Data Array of the Image
    Pixel_Size : Size of the Image 

    Returns
    -------
    Image : Corrected Data Array

    """
    for i in range(Pixel_Size):
        if i % 2 == 1:
            Image[i]=Image[i][::-1]
        
    return Image

    