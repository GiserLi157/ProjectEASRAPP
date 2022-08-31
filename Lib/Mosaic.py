from osgeo.gdal import GDT_Byte, GDT_UInt16, GDT_CInt16, GDT_Float32, GDT_Float64, GetDriverByName, Open
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, messagebox
from glob import glob


class Mosaic:
    def __init__(self):
        width = 500
        height = 400
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Mosaic the images of the folder...')
        # Creates the first Label
        Label(self.root, text = "folder_path :").place(x = 100, y = 100)
        # Creates the second Label
        Label(self.root, text = " save_path :").place(x = 100, y = 200)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width = 20, textvariable = self.e1_text).place(x = 180, y = 100)
        Entry(self.root, width = 20, textvariable = self.e2_text).place(x = 180, y = 200)

        Button(self.root, text = "...", command = self.select_folder_path).place(x = 330, y = 96)
        Button(self.root, text = "...", command = self.select_save_path).place(x = 330, y = 196)
        Button(self.root, text = "Mosaic", command = self.getpath, activebackground = "pink",
               activeforeground = "blue").place(x = 145, y = 300)
        Button(self.root, text = "Cancel", command = self.root.destroy, activebackground = "pink",
               activeforeground = "blue").place(x = 290, y = 300)
        self.root.mainloop()

    def select_folder_path(self):
        imgPath = filedialog.askdirectory(title = 'Select the folder path...', initialdir = None, mustexist = True)
        self.e1_text.set(str(imgPath))

    def select_save_path(self):
        savePath = filedialog.asksaveasfilename(title = 'Select the path to save the result...', initialdir = None,
                                              filetypes = [(
                                                  "raster", ".tif"), ('All Files', ' *')], defaultextension = '.tif')
        self.e2_text.set(str(savePath))

    def getpath(self):
        self.root.destroy()
        folderPath, savePath = self.e1_text.get(), self.e2_text.get()
        self.image_mosaic(folderPath, savePath)

    def geo2pixel(self, geox, geoy, geoTrans):
        #     根据GDAL的六参数模型将给定的投影或地理坐标转为影像图上坐标（行列号）
        #     :param dataset: GDAL地理数据
        #     :param x: 投影或地理坐标x
        #     :param y: 投影或地理坐标y
        #     return: 投影坐标或地理坐标(x, y)对应的影像图上行列号(row, col)
        #     a = np.array([[geoTrans[1], geoTrans[2]], [geoTrans[4], geoTrans[5]]])
        #     b = np.array([geox - geoTrans[0],geoTrans[3] - geoy])
        #     col,row = np.linalg.solve(a, b)# 使用numpy的linalg.solve进行二元一次方程的求解
        #     row = int(row + 0.5)
        #     col = int(col +0.5)
        g0 = geoTrans[0]
        g1 = geoTrans[1]
        g2 = geoTrans[2]
        g3 = geoTrans[3]
        g4 = geoTrans[4]
        g5 = geoTrans[5]
        row = int(((geox - g0) * g4 - (geoy - g3) * g1) / (g2 * g4 - g1 * g5) + 0.5)
        col = int(((geox - g0) * g5 - (geoy - g3) * g2) / (g1 * g5 - g2 * g4) + 0.5)
        return [row, col]

    def pixel2geo(self, row, col, geoTrans):
        # 六个参数分别是：
        #     geos[0]  top left x 左上角x坐标
        #     geos[1]  w-e pixel resolution 东西方向像素分辨率
        #     geos[2]  rotation, 0 if image is "north up" 旋转角度，正北向上时为0
        #     geos[3]  top left y 左上角y坐标
        #     geos[4]  rotation, 0 if image is "north up" 旋转角度，正北向上时为0
        #     geos[5]  n-s pixel resolution 南北向像素分辨率
        #     x/y为图像的x/y坐标，geox/geoy为对应的投影坐标
        geox = geoTrans[0] + geoTrans[1] * col + geoTrans[2] * row
        geoy = geoTrans[3] + geoTrans[4] * col + geoTrans[5] * row
        return geox, geoy

    def readTif(self, path):
        ds = Open(path)
        width = ds.RasterXSize
        height = ds.RasterYSize
        geoTrans = ds.GetGeoTransform()
        projection = ds.GetProjection()

        return width, height, geoTrans, projection, ds

    # image mosaic（i.e. image splicing）
    def image_mosaic(self, folderPath, savePath):
        tifPaths = glob(folderPath + '/*.tif')
        extent_geox = []
        extent_geoy = []
        datasets = []
        geoxy = []
        row_col_min = []
        for path in tifPaths:
            width, height, geotrans, proj, ds  = self.readTif(path)
            datasets.append(ds)
            geox_min = geotrans[0]
            geoy_max = geotrans[3]
            geoxy.append([geox_min, geoy_max])
            extent_geox.append(geox_min)
            extent_geoy.append(geoy_max)
            # 确定每张影像的右下角坐标
            row_min, col_min = self.geo2pixel(geox_min, geoy_max, geotrans)
            row_max, col_max = row_min + height, col_min + width
            geox_max, geoy_min = self.pixel2geo(row_max, col_max, geotrans)
            extent_geox.append(geox_max)
            extent_geoy.append(geoy_min)

        extent_geox_min = min(extent_geox)
        extent_geox_max = max(extent_geox)
        extent_geoy_min = min(extent_geoy)
        extent_geoy_max = max(extent_geoy)

        newgeotrans = list(geotrans)
        newgeotrans[0] = extent_geox_min
        newgeotrans[3] = extent_geoy_max
        del extent_geox, extent_geoy
        row, col = self.geo2pixel(extent_geox_max, extent_geoy_min, newgeotrans)  # Calculate the (height,width)  of the stitched large image
        # 确定每个影像写入大图像时在大图像左上角的行列数
        for geo in geoxy:
            geox = geo[0]
            geoy = geo[1]
            [row_min, col_min] = self.geo2pixel(geox, geoy, newgeotrans)
            row_col_min.append([row_min, col_min])
        del geoxy

        ds = datasets[0]
        width, height, im_bands = ds.RasterXSize, ds.RasterYSize, ds.RasterCount
        img = ds.ReadAsArray(0, 0, width, height)
        del ds
        # 确定输出影像的数据类型
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

        driver = GetDriverByName('GTiff')
        out_ds = driver.Create(savePath, col, row, im_bands, dtype,
                               options=["COMPRESS=LZW"])
        root = Tk()
        root.withdraw()
        if out_ds is not None:
            out_ds.SetProjection(proj)  # 写入投影
            out_ds.SetGeoTransform(newgeotrans)  # 写入新的仿射变换参数
            if im_bands != 1:
                for i in range(im_bands):
                    band = out_ds.GetRasterBand(i + 1)
                    num = len(tifPaths)
                    for j in range(num):
                        ds = datasets[j]
                        image = ds.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
                        row_col = row_col_min[j]
                        gray = image[i, :, :]
                        band.WriteArray(gray, row_col[1], row_col[0])
                    # band.SetNoDataValue(0) # Can be set or unset
                    # # Statistical data: It can not be done when image data is large
                    # band.FlushCache()# Refresh the disk
                    # stats = band.GetStatistics(0, 1) # If the first parameter is 1, it is counted based on the pyramid

            else:
                band = out_ds.GetRasterBand(1)
                num = len(tifPaths)
                for j in range(num):
                    ds = datasets[j]
                    image = ds.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
                    row_col = row_col_min[j]
                    band.WriteArray(image, row_col[1], row_col[0])
                    # band.SetNoDataValue(0) # Can be set or unset
                    # # Statistical data: It can not be done when image data is large
                    # band.FlushCache()# Refresh the disk
                    # stats = band.GetStatistics(0, 1) # If the first parameter is 1, it is counted based on the pyramid.
        else:
            messagebox.showerror("Error", 'Failed to create the output dataset!')
        # Create a pyramid of output images. It may not be done when the image data is large,
        # otherwise the output will be even larger.
        # gdal.SetConfigOption('HFA_USE_RRD', 'YES')
        # out_ds.BuildOverviews(overviewlist = [2,4,8,16,32]) # 4 floors
        del out_ds, ds, datasets
        messagebox.showinfo("Prompt", 'Successful to mosaic the images to a big image!')
        root.destroy()
        root.mainloop()

if __name__ == "__main__":
    Mosaic()