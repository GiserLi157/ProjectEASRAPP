from osgeo.ogr import Open, Feature, FieldDefn
from osgeo.osr import CoordinateTransformation
from osgeo.gdal import SetConfigOption
from os import path
from tkinter import FIRST, LAST, Tk, Label, Entry, Button, StringVar, filedialog, Scrollbar, RIGHT, Y, Listbox, ACTIVE, END


class Merge:
    def __init__(self):
        width = 500
        height = 800
        self.root = Tk()
        size_align = '%dx%d+%d+%d' % (
            width, height, (self.root.winfo_screenwidth() - width) / 2, (self.root.winfo_screenheight() - height) / 2)
        self.root.geometry(size_align)
        self.root.title('Merge the vectors to the same layer...')
        # Creates the first Label
        Label(self.root, text = "vectors_path:").place(x = 100, y = 100)
        # Creates the second Label
        Label(self.root, text = "  save_path:").place(x = 100, y = 200)
        # Creates the third Label
        Label(self.root, text = "temp_optional:").place(x = 100, y = 300)
        # Creates the fourth Label
        Label(self.root, text = "delete_field:").place(x = 100, y = 495)
        self.list_str = StringVar()
        scroll = Scrollbar(self.root)
        scroll.pack(side = RIGHT, fill = Y)
        # height Default display 10 data; listBox = Listbox(root, height=11)
        self.listBox = Listbox(self.root, listvariable = self.list_str, yscrollcommand = scroll.set)
        self.listBox.place(x = 180, y = 400)
        # listBox.see(0)  # Adjust the position of the list box so that the options specified by the
        # index parameter are visible

        # Linkage with listbox
        scroll.config(command = self.listBox.yview)

        Button(self.root, text = "delete", command = self.delete).place(x = 330, y = 495)
        self.e1_text = StringVar()
        self.e2_text = StringVar()
        self.e3_text = StringVar(value = "None")
        Entry(self.root, width = 20, textvariable = self.e1_text).place(x = 180, y = 100)
        Entry(self.root, width = 20, textvariable = self.e2_text).place(x = 180, y = 200)
        Entry(self.root, width = 19, textvariable = self.e3_text).place(x = 190, y = 300)
        Button(self.root, text = "...", command = self.select_vectors_path).place(x = 330, y = 96)
        Button(self.root, text = "...", command = self.select_save_path).place(x = 330, y = 196)
        Button(self.root, text = "...", command = self.select_temp_path).place(x = 330, y = 296)
        Button(self.root, text = "Merge", command = self.getpath, activebackground = "pink",
               activeforeground = "blue").place(x = 145, y = 700)
        Button(self.root, text = "Cancel", command = self.root.destroy, activebackground = "pink",
               activeforeground = "blue").place(x = 290, y = 700)
        self.root.mainloop()

    def delete(self):
        self.listBox.delete(ACTIVE)  # Delete the selected

    def select_vectors_path(self):
        vectorPath = filedialog.askopenfilenames(title = 'Select the vectors to be merged...', initialdir = None,
                                             filetypes = [(
                                                 "vector", ".shp"), ('All Files', ' *')], defaultextension = '.shp')
        fields_types = []
        for vpath in vectorPath:
            [_, vfilename] = path.split(vpath)
            name = path.splitext(vfilename)[0]
            in_ds = Open(vpath, 0)
            in_layer = in_ds.GetLayer(0)
            # Get field definitions
            defn = in_layer.GetLayerDefn()
            for i in range(defn.GetFieldCount()):
                field = defn.GetFieldDefn(i).GetName()
                typecode = defn.GetFieldDefn(i).GetType()
                type = defn.GetFieldDefn(i).GetFieldTypeName(typecode)
                fields_types.append(name + "." +  field + ";type: " + str(type) + ";typecode:" + str(typecode))

        for field_type in fields_types:
            self.listBox.insert(END, field_type)  # Adding data to a ListBox

        vectorPath = ";".join(vectorPath)
        self.e1_text.set(str(vectorPath))

    def select_save_path(self):
        savePath = filedialog.asksaveasfilename(title = 'Select the path to save merging result...', initialdir = None,
                                              filetypes = [(
                                                  "vector", ".shp"), ('All Files', ' *')], defaultextension = '.shp')
        self.e2_text.set(str(savePath))

    def select_temp_path(self):
        tempPath = filedialog.askopenfilename(title = 'Select the reference projection template path to save merging result...', initialdir = None,
                                              filetypes = [(
                                                  "vector", ".shp"), ('All Files', ' *')], defaultextension = '.shp')
        self.e3_text.set(str(tempPath))

    def getpath(self):
        size = self.listBox.size()
        vectorPath, savePath, tempPath, fields_types = self.e1_text.get(), self.e2_text.get(), self.e3_text.get(), self.listBox.get(0,size - 1)
        self.root.destroy()
        self.mergeshp(vectorPath, savePath, tempPath, fields_types)

    def mergeshp(self, added_paths, dest_path, temp_path, fieldsTypes):
        if added_paths and dest_path:
            added_paths = added_paths.split(";")
            if temp_path == "None":
                temp = added_paths[0]
                temp_ds = Open(temp, 0)
                temp_layer = temp_ds.GetLayer(0)
                geom_type = temp_layer.GetGeomType()
                ft = temp_layer.GetFeature(0)
                temp_geom = ft.GetGeometryRef()
                out_srs = temp_geom.GetSpatialReference()
            else:
                temp_ds = Open(temp_path, 0)
                temp_layer = temp_ds.GetLayer(0)
                geom_type = temp_layer.GetGeomType()
                ft = temp_layer.GetFeature(0)
                temp_geom = ft.GetGeometryRef()
                out_srs = temp_geom.GetSpatialReference()

            [filepath, filename] = path.split(dest_path)
            name = path.splitext(filename)[0]

            SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
            SetConfigOption("SHAPE_ENCODING", "GBK")

            driver = temp_ds.GetDriver()
            del temp_ds, temp_layer
            # driver = GetDriverByName('ESRI Shapefile')

            if driver == None:
                print('Drive is not created successfully!')

            if path.exists(dest_path):
                driver.DeleteDataSource(dest_path)
            ds = driver.CreateDataSource(filepath)  # Create datasource
            if ds == None:
                print('Data source is not created successfully')

            dest_layer = ds.CreateLayer(name, srs = out_srs, geom_type = geom_type)
            fields = []
            typecodes = []
            for fieldType in fieldsTypes:
                field_type = fieldType.split(".")[-1]
                fieldName = field_type.split(";")[0]
                if fieldName in fields:
                    pass
                else:
                    fields.append(fieldName)
                    typecode = int(fieldType.split(":")[-1])
                    typecodes.append(typecode)
                    defn = FieldDefn(fieldName, typecode)
                    dest_layer.CreateField(defn)

            for added_path in added_paths:
                in_ds = Open(added_path, 0)
                if in_ds == None:
                    print("Failed to open the vector datasource {0} to be merged".format(added_path))
                in_layer = in_ds.GetLayer(0)
                if in_layer == None:
                    print("Failed to open the vector layer {0} to be merged.".format(added_path))

                for feature in in_layer:
                    geom = feature.GetGeometryRef()
                    in_srs = geom.GetSpatialReference()
                    # Creating a coordinate transformation
                    coordTrans = CoordinateTransformation(in_srs, out_srs)
                    # Get geometric elements
                    geom = feature.GetGeometryRef()
                    # Determine whether the spatial reference is consistent
                    if in_srs.IsSame(out_srs):
                        pass
                    else:
                        # reprojective geometry
                        geom.Transform(coordTrans)
                    # Create element layers
                    outFeature = Feature(dest_layer.GetLayerDefn())
                    # Set geometry, properties for feature layers
                    outFeature.SetGeometry(geom)

                    for field in fields:
                        try:
                            value = feature.GetField(field)
                            outFeature.SetField(field, value)
                        except:
                            typecode = typecodes[fields.index(field)]
                            if typecode == 0:
                                value = 12821
                            if typecode == 4:
                                value = "Null"
                            if typecode == 2:
                                value = -12821
                            outFeature.SetField(field, value)
                            # pass
                    dest_layer.CreateFeature(outFeature)
                    # Cancel quote. Reduced memory usage.
                    del outFeature
                #  Write to disk.
                in_ds.Destroy()
            ds.Destroy()
            print('Vector_merge is successful!')
        else:
            print("You did not select the vectors to be merged and the output path correctly!")


if __name__ == "__main__":
    Merge()