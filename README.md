<a href="https://info.flagcounter.com/qu3g"><img src="https://s11.flagcounter.com/count2/qu3g/bg_FFFFFF/txt_000000/border_CCCCCC/columns_2/maxflags_10/viewers_0/labels_0/pageviews_0/flags_0/percent_0/" alt="Flag Counter" border="0"></a>

# Attention please
- Test data that are larger than 100M are difficult to be uploaded on GitHub.   However, the test data could be downloaded at https://drive.google.com/drive/folders/1Q00JZYo-gopVuN2g-epeXTxP0y_tYwrT?usp=sharing.
    
# Welcome to EASRAPP (An Open-Source Semi-Automatic Python GUI-Based Application for Extraction and Analysis of Surface Ruptures in a large earthquake)  

- EASRAPP, written in Python, is a free, open-source system with simplified interactive interfaces tailed to the rapid extraction and analysis of surface ruptures. 
- It facilitates the user to obtain the region of interest quickly using a custom cropping routine to crop the raw image; allows the user to reference the raw image to extract surface ruptures semi-automatically; supports manual adjustment of extraction results if required; helps to extract lengths, widths, and strikes of all surface ruptures; provides the user with some processing tools for vector and raster; also offers the necessary prompts or error messages to the user during the runtime; and uses a new algorithm to extract the widths of the surface rupture zone at optional distance intervals, while generating a bar graph of the surface rupture widths with a fitted curve and a rose diagram of angles between surface ruptures and fault trace.
- This application is easily applied and has the functions to zoom in, zoom out and move for helping to extract surface ruptures in larger images (e.g., 5000 X 5000 pixels in dimension).
- It will provide a convenient tool for the rapid extraction of coseismic surface ruptures, and will help understand detailed information about the seismogenic fault of a large earthquake.
- the part modules of EASRAPP(e.g., the RoughSeg_FineExt, EditVector and WidthAndStrike modules) require the input image to be a three-channel optical image with the projection coordinate system, a pixel type of ‘unsigned integer’ and a pixel depth of ‘8 Bit’ (i.e., "0-255" for the pixel value extent of each channel). 

## Citation
Ariticle Here: https://pubs.geoscienceworld.org/ssa/srl/article-abstract/doi/10.1785/0220220313/620895/EASRAPP-An-Open-Source-Semiautomatic-Python-GUI

Please cite this article as:  

*Li, D., and J. Ren (2023). EASRAPP: An Open-Source Semiautomatic Python GUI-Based Application for Extraction and Analysis of Surface Ruptures in a Large Earthquake,*  *Seismological Research Letters XX, 1–16, doi: https://doi.org/10.1785/0220220313.*

## Cooperation: Develop together, Progress together  
- I also encourage the user to work together to develop new functionalities and share these developments with the geoscientific community under the GNU General Public  License v3.0 to create an open-source software for the extraction and analysis of some terrain features. My code is developed using Python, I have also tried to package it as a lightweight exe for users to download and use without having to install their own packages, but due to Python's own reasons and my ability to limit, the packaging results are so large that it is not easy for everyone to download and use. If any of you are able to package a lightweight exe, please work with me to improve EASRAPP. For ideas, suggestions or code improvements, please contact my email at lidongchen20@mails.ucas.ac.cn.

## Run the Software
Python and the Python packages requested in the file 'requirement.txt' need to be installed. Please refer to the user manual for specific usage.

## CustomCrop module
### Crop the remote sensing image according to the individual need.
- The **CustomCrop** module allows the user to crop images quickly according to his own concrete need. This is to say, the application can automatically crop remote sensing images to any shape drawn interactively by the user. 
- The module has implemented several functions as follows. Please see the **User Manual** for specific steps.
  - The user can move and zoom in or out of the image at any time to view the image.
  - The user can select the inflection point of the area of interest (i.e. the cropping range of the image) .
  - The user can undelete the wrong inflection point.
  - the user can save the result in the GeoTIFF format using the **‘ctrl+s’** shortcut.
  - The cropping operation can be repeated several times to crop multiple images of appropriate size from one large image.

### RoughSeg_FineExt module
- The **RoughSeg_FineExt** module provides a quick, convenient and exact way to extract surface ruptures and related geometric parameters from high-resolution remote sensing images semi-automatically. 
- The module has implemented several functions as follows. Please see the **User Manual** for specific steps.
  - The user can perform color segmentation based on color information in the image to roughly extract desired features such as water, surface ruptures and buildings.

  - The "fine extraction" process: The user can further filter out the noise based on the shape information of each object to get the extracted objects.
  - The user may adjust thresholds with sliders realizing the semi-automatic color segmentation and semi-automatic "fine extraction" process in real-time.
  - The user can move and zoom the image at any time to see the extraction effect. 

## EditVector module
- The design of the **EditVector** module is dedicated to manually editing the extraction result to obtain a more accurate result and calculating the lengths, widths, and strikes of surface ruptures which finally are stored in the property table of the vector result.
- The module has implemented several functions as follows. Please see the **User Manual** for specific steps.

  - The user can delete, undelete, and digitize the vector objects repeatedly.
  - The user may move, zoom in or out of the image at any time via the mouse wheel to easily edit the vector objects.

  - The user can use this module to calculate the lengths, widths, and strikes of surface ruptures which
    finally are stored in the property table of the vector result.
  - The results are output in .shp and the GeoTIFF formats.

## **WidthAndStrike module**
- The module is used to perform the extraction of the widths of surface ruptures at optional intervals and the generation of a rose diagram of angles between surface ruptures and the dominant direction of the fault.
- The module has implemented several functions as follows. Please see the **User Manual** for specific steps.
  - This module can generate a schematic diagram indicating the location of the calculated widths of the surface rupture zone at different distance intervals along the dominant direction of the fault(i.e., the fault trace). 
  - This module can generate a bar graph(with a fitted curve of width) of the width of the surface rupture zone.
  - This module can also generate a rose map of angles between surface ruptures and the fault trace input or drawn. 
  - The user can repeat the distance interval modification or the drawing of the new dominant direction of the fault to generate new results if the results are unsatisfactory. 
  - The user can also zoom in or out and move the layer to view the features of the vector or the result.

## Auxiliary tools available

- EASRAPP includes seven tools: **Data structure conversion**(the vector to raster**,** the raster to vector**,** the lineRing to surface and the surface to lineRing), **Merge**, **SlidingCrop**, **Mosaic**.

- EASRAPP has implemented seven tools as follows. Please see the **User Manual** for specific steps.
  - The lineRing to surface tool is dedicated to batch converting line ring vectors to surface vectors.
  - The user may also convert surface vectors to line loop vectors in batches using the surface to
    lineRing tool.
  - The vector to raster tool and raster to vector tool are used to perform interconversions between
    raster and vector. The vector to raster tool can convert the line loop vectors in bulk to black and white binary raster images, serving as a dataset for machine learning or deep learning.
  - The **Merge** tool is aimed at merging the features of multiple vector files to the same layer
  - The **slidingCrop** tool allows the user to batch crop multiple large images to many small images with a sliding window of selectable size. The user can also select whether to create a sample dataset for machine learning or deep learning.
  - The **Mosaic** tool is dedicated to mosaicing several remote sensing images into a large image.

## Test Data
- We have categorized the test data (names are consistent with the description in the user manual) according to each module and tool. In addition, the test data for both the **‘CustomCrop’** module and the **‘SlidingCrop’** tool is the image named '0525-0.01mDOM.tif '  (see the folder named **'CustomCrop&SlidingCrop'** under the **‘test_data’** zip). Also, the test data of the **'Mosaic'** tool is the cropping result of the **‘SlidingCrop’** tool.

# Extraction effect and partial functions demonstration
- # Comparison of the extraction result with the result of visual interpretation
  - a drone image with a resolution of about 2 cm derived from the 2021 Maduo Ms7.4 earthquake in Qinghai Province was tested.
  - Notes: Figure 1. The comparison of extraction results and manual mapping results, in which the red is the contour of the extraction result and the bottom image is the raw image; (a) the extracted result; (b) the result of the visual interpretation in Liu-Zeng et al. (2022), in which the thick line in green is the primary rupture they drew, and the thin line is the secondary rupture; (c)-(e) the local comparison with main ruptures; (f)-(h) the local comparison with secondary ruptures. The geographical coordinates of the black star (the center of the map) in (a) and (b) are (35.8619N, 92.3879E). 
  - ![Figure 7](https://github.com/GiserLi157/ProjectEASRAPP/assets/84237176/67411fbb-b4dd-45a0-8a8a-b0e3f095a2b4)
 
- # Extraction results of surface fractures based on small images
  - From Figure 1, we find that the partially reconstructed surface ruptures are poorly extracted. To verify the reliability of the method and to visualize the usage of the technique, the poorly extracted parts (i.e., the bottom images in Fig. 2a and c) are cropped out from the large image for surface rupture extraction using local thresholding.
  - Notes: Figure 2. Extraction results of small images clipped from the large image, in which bottom images are the data used for the semi-automatic extraction algorithm; (a) and (c) the original extraction results of Figure 7e and Figure 7g; (b) and (d) Extraction results after image chunking. The green is the visual representation result of surface ruptures by Liu-Zeng et al. (2022).
  - ![Figure 8](https://github.com/GiserLi157/ProjectEASRAPP/assets/84237176/dbf02674-18ff-4628-b9e1-80f37165b1f5)

- # Effect of application to the fractures in the satellite image of historical earthquakes
  - To demonstrate that historic surface ruptures in the satellite image can be identified and extracted using the EASRAPP, the Mapbox satellite image with a resolution of approximately 7.5 cm is tested. Figure 3 shows the extraction results of fractures caused by the 2001 Kunlun Ms8.1 earthquake, and observes the extraction effect by overlaying the contours of the result on the original optical image.
  - Notes: Figure 3. The extraction result of ruptures in the historical earthquake, in which the red line ring is the outline of the surface rupture. (a) Results of surface rupture extraction, with the original optical image in the bottom image; (b)-(d) Detail structures of surface rupture contours. The geographical coordinates of the black star in Figure 9a are (35.8619N, 92.3879E).
  - ![Figure 9](https://github.com/GiserLi157/ProjectEASRAPP/assets/84237176/29437d9c-67b4-45ec-94fd-cb4b95fae191)

- # Functions of WidthAndStrike module
  - EASRAPP includes a module to perform the extraction of the widths of the surface rupture zone at optional intervals and the generation of a rose diagram of angles between surface ruptures and the dominant direction of the fault.
  - Notes: Figure 4. (a) The bar graph of the width of the surface rupture zone; (b) the rose map of angles; (c) the slider used to interactively adjust the equivalent length threshold; (d) the schematic diagram of widths of the surface rupture, where the red arrow indicates the dominant direction of the fault.
  - ![Figure 5](https://github.com/GiserLi157/ProjectEASRAPP/assets/84237176/abee5dfb-6750-4511-8401-c02f367c1afb)

