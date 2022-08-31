from math import ceil
from osgeo.gdal import Open, GetDriverByName, GDT_Byte, GDT_CInt16, GDT_UInt16, GDT_Float32, GDT_Float64
from rasterio import open
from rasterio.windows import Window
from os import path, makedirs, listdir
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, Checkbutton, IntVar, messagebox
from tkinter.ttk import Combobox


class SlidingCrop:
    def __init__(self):
        width = 500
        height = 600
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Crop multiple large images into multiple regular shaped small images...')
        # Creates the first Label
        Label(self.root, text = "bigImg_paths").place(x = 96, y = 100)
        # Creates the second Label
        Label(self.root, text = "folder_path").place(x = 100, y = 200)
        # Creates the third Label
        Label(self.root, text = "crop_width").place(x = 100, y = 300)
        # Creates the fouth Label
        Label(self.root, text = "crop_height").place(x = 227, y = 300)
        # Creates the fifth Label
        Label(self.root, text = "crop_repetitionRate").place(x = 80, y = 400)

        self.e1_text = StringVar()
        self.e2_text = StringVar()
        self.e3_num = IntVar()
        Entry(self.root, width = 20, textvariable = self.e1_text).place(x = 180, y = 100)
        Entry(self.root, width = 20, textvariable = self.e2_text).place(x = 180, y = 200)
        # Define drop-down list: Combobox
        self.crop_width = Combobox(self.root, font = ('宋体', 10), width = 5)
        self.crop_height = Combobox(self.root, font = ('宋体', 10), width = 5)
        self.crop_repetitionRate = Combobox(self.root, font = ('宋体', 10), width = 5)
        Checkbutton(self.root, text = "Create datasets?", variable = self.e3_num, \
                    onvalue = 1, offvalue = 0,\
                    width = 13).place(x = 275, y = 396)
        # Placing drop-down list box controls
        self.crop_width.place(x = 167, y = 300)
        self.crop_height.place(x = 300, y = 300)
        self.crop_repetitionRate.place(x = 200, y = 400)
        # Set value list of combobox
        self.crop_width['values'] = ["128", "256", "512", "1024"]
        self.crop_height['values'] = ["128", "256", "512", "1024"]
        self.crop_repetitionRate['values'] = ["0", "0.001", "0.01", "0.1"]
        # Set the default value of the drop-down list
        self.crop_width.set("128")
        self.crop_height.set("128")
        self.crop_repetitionRate.set("0")

        Button(self.root, text = "...", command = self.select_bigImg_paths).place(x = 330, y = 96)
        Button(self.root, text = "...", command = self.select_save_folder).place(x = 330, y = 196)
        Button(self.root, text = "Crop", command = self.getpath, activebackground = "pink",
               activeforeground = "blue").place(x = 145, y = 500)
        Button(self.root, text = "Cancel", command = self.root.destroy, activebackground = "pink",
               activeforeground = "blue").place(x = 290, y = 500)
        self.root.mainloop()

    def readTif(self, path):
        ds = Open(path)
        width = ds.RasterXSize
        height = ds.RasterYSize
        geoTrans = ds.GetGeoTransform()
        projection = ds.GetProjection()

        return width, height, geoTrans, projection

    def writeTif(self, path, img, im_geotrans, im_proj, nodata=None):
        data_type = img.dtype.name
        if 'uint8' in data_type:
            dtype = GDT_Byte
        elif 'uint16' in data_type:
            dtype = GDT_UInt16
        elif 'int16' in data_type:
            dtype = GDT_CInt16
        elif 'float32' in data_type:
            dtype = GDT_Float32
        else:
            dtype = GDT_Float64

        im_bands = 1
        if len(img.shape) == 2:
            im_height, im_width = img.shape
        else:
            im_bands, im_height, im_width = img.shape

        # 创建输出tif
        gTiffDriver = GetDriverByName("GTiff")
        ds = gTiffDriver.Create(path, im_width, im_height, im_bands, dtype, options=["COMPRESS=LZW", "BIGTIFF=YES"])
        if (ds != None):
            ds.SetGeoTransform(im_geotrans)  # 写入仿射变换参数
            ds.SetProjection(im_proj)  # 写入投影
            if im_bands != 1:
                for i in range(im_bands):
                    band = ds.GetRasterBand(i + 1)
                    band.WriteArray(img[i, :, :])
                    if nodata != None:
                        band.SetNoDataValue(nodata)  # 可设置可不设置
            else:
                band = ds.GetRasterBand(1)
                band.WriteArray(img)
                if nodata != None:
                    band.SetNoDataValue(nodata)  # 可设置可不设置
        else:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Error", 'The dataset was not created successfully  when outputing the tif image!')
            root.mainloop()
        del gTiffDriver
        del ds

    def pixel2geo(self, row, col, geoTrans):
        # 六个参数分别是：
        #     geos[0]  top left x
        #     geos[1]  w-e pixel resolution
        #     geos[2]  rotation, 0 if image is "north up"
        #     geos[3]  top left y 左上角y坐标
        #     geos[4]  rotation, 0 if image is "north up"
        #     geos[5]  n-s pixel resolution
        #     col/row为图像的x/y坐标，geox/geoy为对应的投影坐标
        geox = geoTrans[0] + geoTrans[1] * col + geoTrans[2] * row
        geoy = geoTrans[3] + geoTrans[4] * col + geoTrans[5] * row
        return geox, geoy

    def select_bigImg_paths(self):
        imgPaths = filedialog.askopenfilenames(title = 'Select multiple big images to be cropped...', initialdir = None,
                                             filetypes = [(
                                                 "image", ".tif"), ('All Files', ' *')], defaultextension = '.tif')
        imgPaths = ";".join(imgPaths)
        self.e1_text.set(str(imgPaths))

    def select_save_folder(self):
        savePath = filedialog.askdirectory(title = 'Select the save folder...', initialdir = None, mustexist = True)
        self.e2_text.set(str(savePath))

    def getpath(self):
        imgPaths, folderPath, crop_w, crop_h, re_rate, val_bool = self.e1_text.get(), self.e2_text.get(), \
                                                                 int(self.crop_width.get()),\
                                                                 int(self.crop_height.get()), \
                                                                 float(self.crop_repetitionRate.get()), \
                                                                 self.e3_num.get()

        self.root.destroy()
        self.crop(imgPaths, folderPath, crop_h, crop_w, re_rate, val_bool)

    def crop(self, imgPaths, savePath, size_h, size_w, repetitionRate, val_bool):
        imgPaths = imgPaths.split(";")
        for imgPath in imgPaths:
            width, height, geotrans, proj = self.readTif(imgPath)

            # Get the number of files in the current folder "len", and name the image to be cropped with "len+1".
            if not path.exists(savePath):
                makedirs(savePath)
            new_name = len(listdir(savePath)) + 1

            src = open(imgPath)
            #  Crop the image, the repetition rate is repetitionRate
            for i in range(ceil((height - size_h * repetitionRate) / (size_h * (1 - repetitionRate)))):
                for j in range(ceil((width - size_w * repetitionRate) / (size_w * (1 - repetitionRate)))):
                    # Calculate the pixel coordinate range "extent"
                    pixel_Y0 = int(i * size_h * (1 - repetitionRate) + 0.5)
                    pixel_Y1 = int(i * size_h * (1 - repetitionRate) + 0.5) + size_h
                    pixel_X0 = int(j * size_w * (1 - repetitionRate) + 0.5)
                    pixel_X1 = int(j * size_w * (1 - repetitionRate) + 0.5) + size_w
                    # Calculate the top-left geographic coordinates to update the affine matrix
                    min_geox, max_geoy = self.pixel2geo(pixel_Y0, pixel_X0, geotrans)
                    if (pixel_X1 <=  width) and (pixel_Y1 <= height):
                        crop = src.read(window = Window(pixel_X0, pixel_Y0, size_w, size_h))
                    elif (pixel_X1 <=  width) and (pixel_Y1 > height):
                        if val_bool:
                            min_geox, max_geoy = self.pixel2geo(pixel_Y0  - (pixel_Y1 - height), pixel_X0, geotrans)
                            crop = src.read(window = Window(pixel_X0, pixel_Y0 - (pixel_Y1 - height), size_w, size_h))
                        else:
                            crop = src.read(window = Window(pixel_X0, pixel_Y0, size_w, size_h - (pixel_Y1 - height)))
                    elif (pixel_X1 > width) and (pixel_Y1 <= height):
                        if val_bool:
                            min_geox, max_geoy = self.pixel2geo(pixel_Y0, pixel_X0 - (pixel_X1 - width), geotrans)
                            crop = src.read(window = Window(pixel_X0 - (pixel_X1 - width), pixel_Y0, size_w, size_h))
                        else:
                            crop = src.read(window = Window(pixel_X0, pixel_Y0, size_w - (pixel_X1 - width), size_h))
                    else:
                        if val_bool:
                            min_geox, max_geoy = self.pixel2geo(pixel_Y0  - (pixel_Y1 - height), pixel_X0 - (pixel_X1 - width), geotrans)
                            crop = src.read(window = Window(pixel_X0 - (pixel_X1 - width), pixel_Y0  - (pixel_Y1 - height), size_w, size_h))
                        else:
                            crop = src.read(window = Window(pixel_X0, pixel_Y0, size_w - (pixel_X1 - width), size_h - (pixel_Y1 - height)))

                    # Update the affine matrix
                    newgeotrans = list(geotrans)
                    newgeotrans[0] = min_geox
                    newgeotrans[3] = max_geoy
                    # Write to image
                    self.writeTif(savePath + "/%d.tif" % new_name, crop, newgeotrans, proj)
                    # Update the file name
                    new_name = new_name + 1
        root = Tk()
        root.withdraw()
        messagebox.showinfo("Prompt", "Image cropping has finished!")
        root.mainloop()


if __name__ == "__main__":
    SlidingCrop()