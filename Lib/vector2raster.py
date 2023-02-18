from osgeo.ogr import Open as ogrOpen
from osgeo.gdal import GetDriverByName, GA_ReadOnly, Open as gdalOpen, SetConfigOption, RasterizeLayer, GDT_Byte, \
    GDT_Float32
from os import path
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, messagebox
from tkinter.ttk import Combobox


class vector2raster:
    def __init__(self):
        self.referRaster = None
        width = 500
        height = 600
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Vector to raster...')
        # Creates the first Label
        Label(self.root, text="vector_paths:").place(x=100, y=100)
        # Creates the second Label
        Label(self.root, text="save_folder:").place(x=100, y=200)
        # Creates the second Label
        Label(self.root, text="field2value :").place(x=100, y=300)
        # Creates the third Label
        Label(self.root, text="resolution :").place(x=100, y=400)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        self.e3_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e1_text).place(x=180, y=100)
        Entry(self.root, width=20, textvariable=self.e2_text).place(x=180, y=200)
        # Define drop-down list: Combobox
        self.combobox = Combobox(self.root, font=('宋体', 10), width=20, state='readonly')
        # Placing drop-down list box controls
        self.combobox.place(x=180, y=300)
        # Set the default value of the drop-down list
        self.combobox.set("None")
        Entry(self.root, width=20, textvariable=self.e3_text).place(x=180, y=400)

        Button(self.root, text="...", command=self.select_vector_path).place(x=330, y=96)
        Button(self.root, text="...", command=self.select_save_folder).place(x=330, y=196)
        Button(self.root, text="...", command=self.set_resolution).place(x=330, y=396)
        Button(self.root, text="Convert", command=self.getpath, activebackground="pink",
               activeforeground="blue").place(x=145, y=500)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=290, y=500)
        self.root.mainloop()

    def set_resolution(self):
        self.referRaster = filedialog.askopenfilename(title='Select the reference raster path...', initialdir=None,
                                                      filetypes=[(
                                                          "raster", ".tif"), ('All Files', ' *')],
                                                      defaultextension='.tif')
        if self.referRaster:
            refer_ds = gdalOpen(self.referRaster)
            geotrans = refer_ds.GetGeoTransform()
            resolution_w = geotrans[1]
            resolution_h = geotrans[5]
            res_seq = (str(resolution_w), str(resolution_h))
            resolution = ",".join(res_seq)
            self.e3_text.set(resolution)

    def select_save_folder(self):
        savePath = filedialog.askdirectory(title='Select the save folder...', initialdir=None, mustexist=True)
        self.e2_text.set(str(savePath))

    def select_vector_path(self):
        vectorPath = filedialog.askopenfilenames(title='Select the vector paths...', initialdir=None,
                                                 filetypes=[(
                                                     "vector", ".shp"), ('All Files', ' *')], defaultextension='.shp')
        vPath = vectorPath[0]
        vectorPath = ";".join(vectorPath)
        self.e1_text.set(str(vectorPath))
        vector_ds = ogrOpen(vPath)
        layer = vector_ds.GetLayer()
        # Define the set of drop-down list option values
        attribute_names = []
        for feat in layer.schema:
            attribute_name = feat.GetName()  # acquire field name
            attribute_names.append(attribute_name)
        attribute_names.append("None")
        self.combobox['values'] = attribute_names
        del vector_ds
        del layer

    def getpath(self):
        res = self.e3_text.get()
        shpPath, rasterPath, resolution, field = self.e1_text.get(), self.e2_text.get(), \
                                                 res.split(","), self.combobox.get()
        self.root.destroy()
        self.vector_to_raster(shpPath, rasterPath, resolution, field)

    def vector_to_raster(self, shapefiles, savePath, res_size, field):
        # ALL_TOUCHED=TRUE means that all image elements intersecting the vector are assigned values
        # "ATTRIBUTE=%s"%field means the value of the raster is the value of the field field, if not add this means
        # the vector is converted to a value
        root = Tk()
        root.withdraw()
        shapefiles = shapefiles.split(";")
        for shapefile in shapefiles:
            (_, filename) = path.split(shapefile)
            name = filename.split(".")[0] + ".tif"
            rasterfile = savePath + '/' + name
            ds = ogrOpen(shapefile)
            if ds is None:
                messagebox.showerror("Error", 'Failed to read {0}'.format(shapefile))
            layer = ds.GetLayer()
            x_min, x_max, y_min, y_max = layer.GetExtent()
            prj = layer.GetSpatialRef().ExportToWkt()

            res_size_w, res_size_h = abs(float(res_size[0])), abs(float(res_size[1]))
            width = int((x_max - x_min) / res_size_w + 0.5)
            height = int((y_max - y_min) / res_size_h + 0.5)
            if field == "None":
                targetDataset = GetDriverByName('GTiff').Create(rasterfile, width, height, 1, GDT_Byte,
                                                                options=["COMPRESS=LZW", "BIGTIFF=YES"])
            else:
                targetDataset = GetDriverByName('GTiff').Create(rasterfile, width, height, 1, GDT_Float32,
                                                                options=["COMPRESS=LZW", "BIGTIFF=YES"])

            if targetDataset is None:
                messagebox.showerror("Error", 'Failed to create raster datasource {0}'.format(targetDataset))
            geotrans = (x_min, res_size_w, 0, y_max, 0, -res_size_h)
            targetDataset.SetGeoTransform(geotrans)
            targetDataset.SetProjection(prj)
            band = targetDataset.GetRasterBand(1)
            # Whether to set NoDataValue of raster
            # NoData_value = 0
            # band.SetNoDataValue(NoData_value)
            band.FlushCache()  #
            if field == "None":
                RasterizeLayer(targetDataset, [1], layer, options=['ALL_TOUCHED=TRUE'])
            else:
                RasterizeLayer(targetDataset, [1], layer,
                               options=["ATTRIBUTE=%s" % field, 'ALL_TOUCHED=TRUE'])
            del targetDataset
            del ds
        messagebox.showinfo("Prompt", "Vector_to_raster conversion is successful!")
        root.destroy()
        root.mainloop()


if __name__ == "__main__":
    vector2raster()
