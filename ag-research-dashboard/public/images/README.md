# Enhanced RGB Band Images

This directory should contain the following grayscale band images for the agricultural field analysis:

## Required Files:
- `New_08_08_2025_transparent_reflectance_red.png` - Red band (grayscale)
- `New_08_08_2025_transparent_reflectance_green.png` - Green band (grayscale) 
- `New_08_08_2025_transparent_reflectance_blue.png` - Blue band (grayscale)

## Image Processing:
The MapComponent will automatically:
1. Load these three grayscale band images
2. Enhance each image with:
   - Histogram clipping (2%-98% percentiles)
   - Gamma correction (0.9)
   - Contrast adjustment (1.2x)
   - Channel-specific gains (Red: 1.25, Green: 1.10, Blue: 1.35)
3. Assign each enhanced image to its respective RGB channel
4. Display them as separate overlay layers in react-leaflet

## Enhancement Parameters:
- **CLIP_LOW**: 0.02 (2% lower percentile clip)
- **CLIP_HIGH**: 0.98 (98% upper percentile clip)
- **GAMMA**: 0.9 (gamma correction)
- **CONTRAST**: 1.2 (contrast multiplier)
- **BRIGHTNESS**: 0 (brightness offset)
- **GAINS**: 
  - Red: 1.25
  - Green: 1.10  
  - Blue: 1.35

## Field Bounds:
- **Southwest**: [38.9066667, -92.2816667]
- **Northeast**: [38.9072222, -92.2797222]

Place your actual grayscale band PNG files in this directory to replace the placeholders.