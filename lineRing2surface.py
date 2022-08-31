from osgeo.ogr import Open, wkbPolygon, Feature, wkbLinearRing, Geometry, FieldDefn
from os import path
from osgeo.gdal import SetConfigOption
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, messagebox, Scrollbar, RIGHT, Listbox, Y, ACTIVE, \
    END


class LineRing2surface:
    def __init__(self):
        width = 500
        height = 700
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('LineRing vector to surface vector...')
        # Creates the first Label
        Label(self.root, text="lineRing_paths").place(x=93, y=100)
        # Creates the second Label
        Label(self.root, text="save_folder").place(x=100, y=200)
        # Creates the third Label
        Label(self.root, text="delete_field:").place(x=100, y=395)
        self.list_str = StringVar()
        scroll = Scrollbar(self.root)
        scroll.pack(side=RIGHT, fill=Y)
        # height Default display 10 data; listBox = Listbox(root, height=11)
        self.listBox = Listbox(self.root, listvariable=self.list_str, yscrollcommand=scroll.set)
        self.listBox.place(x=180, y=300)
        # listBox.see(0)  # Adjust the position of the list box so that the options specified by the
        # index parameter are visible

        # Linkage with listbox
        scroll.config(command=self.listBox.yview)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        Entry(self.root, width=20, textvariable=self.e1_text).place(x=180, y=100)
        Entry(self.root, width=20, textvariable=self.e2_text).place(x=180, y=200)

        Button(self.root, text="...", command=self.select_line_paths).place(x=330, y=96)
        Button(self.root, text="...", command=self.select_save_folder).place(x=330, y=196)
        Button(self.root, text="delete", command=self.delete).place(x=330, y=395)
        Button(self.root, text="Convert", command=self.getpath, activebackground="pink",
               activeforeground="blue").place(x=145, y=595)
        Button(self.root, text="Cancel", command=self.root.destroy, activebackground="pink",
               activeforeground="blue").place(x=290, y=595)
        self.root.mainloop()

    def delete(self):
        self.listBox.delete(ACTIVE)  # Delete the selected

    def select_save_folder(self):
        savePath = filedialog.askdirectory(title='Select the surface vector save folder...', initialdir=None,
                                          mustexist=True)
        self.e2_text.set(str(savePath))

    def select_line_paths(self):
        linePaths = filedialog.askopenfilenames(title='Select the lineRing vector paths...', initialdir=None,
                                                filetypes=[(
                                                    "vector", ".shp"), ('All Files', ' *')], defaultextension='.shp')
        fields_types = []
        for linePath in linePaths:
            [_, vfilename] = path.split(linePath)
            name = path.splitext(vfilename)[0]
            in_ds = Open(linePath, 0)
            in_layer = in_ds.GetLayer(0)
            # Get field definitions
            defn = in_layer.GetLayerDefn()
            for i in range(defn.GetFieldCount()):
                field = defn.GetFieldDefn(i).GetName()
                typecode = defn.GetFieldDefn(i).GetType()
                type = defn.GetFieldDefn(i).GetFieldTypeName(typecode)
                fields_types.append(name + "." + field + ";type: " + str(type) + ";typecode:" + str(typecode))

        linePaths = ";".join(linePaths)

        for field_type in fields_types:
            self.listBox.insert(END, field_type)  # Add data to listbox

        self.e1_text.set(str(linePaths))

    def getpath(self):
        size = self.listBox.size()
        fields_types = self.listBox.get(0, size - 1)
        self.root.destroy()
        linePaths, savePath = self.e1_text.get(), self.e2_text.get()
        self.line2surface(savePath, linePaths, fields_types)

    def line2surface(self, savePath, linePaths, fieldsTypes):
        root = Tk()
        root.withdraw()
        linePaths = linePaths.split(";")
        for linePath in linePaths:
            SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
            SetConfigOption("SHAPE_ENCODING", "GBK")
            (_, filename) = path.split(linePath)
            ds = Open(linePath)
            driver = ds.GetDriver()
            layer = ds.GetLayer()
            in_srs = layer.GetSpatialRef()

            name = path.splitext(filename)[0]
            # driver = GetDriverByName('ESRI Shapefile')
            if driver is None:
                messagebox.showerror("Error", "{0} driver is not available！\n".format("ESRI Shapefile"))

            fullPath = savePath + '\\' + filename
            if path.exists(fullPath):
                driver.DeleteDataSource(fullPath)

            # Create output datasource
            sfds = driver.CreateDataSource(savePath)

            if sfds is None:
                messagebox.showerror("Error", "Failed to create surface vector data source!")

            sflayer = sfds.CreateLayer(name, in_srs, geom_type=wkbPolygon)
            if sflayer is None:
                messagebox.showerror("Error", "Failed to create surface vector layer!")
            fields = []
            typecodes = []
            for fieldType in fieldsTypes:
                fname = fieldType.split(".")[0]
                field_type = fieldType.split(".")[-1]
                fieldName = field_type.split(";")[0]
                if fname == name:
                    fields.append(fieldName)
                    typecode = int(fieldType.split(":")[-1])
                    typecodes.append(typecode)
                    defn = FieldDefn(fieldName, typecode)
                    sflayer.CreateField(defn)

            defn = sflayer.GetLayerDefn()
            if defn is None:
                messagebox.showerror("Error", "Failed to obtain the definition of the output layer!")

            for feat in layer:
                box = Geometry(wkbLinearRing)
                geom = feat.GetGeometryRef()
                for i in range(geom.GetPointCount()):
                    x = geom.GetX(i)
                    y = geom.GetY(i)
                    box.AddPoint(x, y)
                polygon = Geometry(wkbPolygon)
                polygon.AddGeometry(box)
                feature = Feature(defn)
                feature.SetGeometry(polygon)
                for field in fields:
                    value = feat.GetField(field)
                    feature.SetField(field, value)

                sflayer.CreateFeature(feature)
                del feature

            sfds.Destroy()
            del ds

        messagebox.showinfo("Prompt", "LineRing-to-surface conversion is successful!")
        root.destroy()
        root.mainloop()


if __name__ == "__main__":
    LineRing2surface()
