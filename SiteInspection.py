import os
import arcpy

inFC = arcpy.GetParameterAsText(0)
buffAmt = arcpy.GetParameterAsText(1)
#arcpy doesn't return values from a choice list as a list, but a string using ; to seperate values instead so this converts it to a list
#We need the scales to be a list since we want to iterate over them and export an image for each of the scales that the user selects.
#If you want to add more scales to the tool you just need to go into the tool parameters and edit the choices available for this parameter.
scales = arcpy.GetParameterAsText(2).split(';') 
outDir = arcpy.GetParameterAsText(3)
nameField = arcpy.GetParameterAsText(4)

# The user can potentially put in a value that is not compatible for the buffer tool so this checks to see if the value provided
# can be converted to an integer and if it can't the buffer will be set to 1,000 metres -> uses American spelling though.
try:
    buffAmt = int(buffAmt)
except:
    buffAmt = 1000

# In order for this script to run the map document that you want to use as your output must be in the same
# directory as this .py file AND MUST BE NAMED 'SiteInspectionMap.mxd'
mxd = arcpy.mapping.MapDocument(os.path.join(os.path.dirname(__file__),'SiteInspectionMap.mxd'))
df = arcpy.mapping.ListDataFrames(mxd)[0]
arcpy.env.overwriteOutput = True

# Need to get the name of the ObjectID field since that's the only real way to ensure you get one image per feature
oidField = arcpy.Describe(inFC).OIDFieldName

with arcpy.da.SearchCursor(inFC,[oidField,nameField]) as cursor:
    for row in cursor:
        #Make a layer that is a single feature in the feature class
        arcpy.MakeFeatureLayer_management(inFC,'SelectedPoint',where_clause="{} = {}".format(oidField,row[0]))
        #Add the buffer to the feature
        arcpy.Buffer_analysis('SelectedPoint','TempBuff_{}'.format(row[0]),buffer_distance_or_field='{} meters'.format(buffAmt))
        #Get the extent of the buffer since we will want to change the dataframe's extent to this
        pointExtent = arcpy.Describe('TempBuff_{}'.format(row[0])).extent
        #Create a layer object out of the buffered point since this format is the only way to add it to a map document
        pointLayer = arcpy.mapping.Layer('TempBuff_{}'.format(row[0]))
        #Adding the actual point to the mxd's dataframe in the TOP position.
        arcpy.mapping.AddLayer(df,pointLayer,'TOP')
        # Create a new variable that is the layer as it sits in the mxd/dataframe.
        addedLayer = arcpy.mapping.ListLayers(mxd,data_frame=df)[0]
        # The default symbology given to polygon features is a completely opaque fill so you can't really see any of the imagery below.
        # If we set the layer visibility to off (unchecked) we can still zoom to it, the shape just wont be visible.
        addedLayer.visible = False
        # Set the dataframe's extent to the extent of the buffered point that was created on line 39.
        df.extent = pointExtent
        #Refresh the table of contents and the active view.
        arcpy.RefreshActiveView()
        arcpy.RefreshTOC()
        #Now we need to iterate over all of the scales that were provided and map a map for each of them.
        for s in scales:
            #Set the scale of the actual dataframe
            df.scale = int(s)
            arcpy.RefreshActiveView()
            arcpy.mapping.ExportToPNG(mxd,os.path.join(outDir,'{}_Scale{}'.format(row[1],s)))
            #The line above this looks pretty confusing but it basically does what is below.
            #For each of the features in the inFC feature class there will be multiple PNGs created at various scales
            #The names of the created files are below:
                #<nameField value for feature 1>_<scale 1 value>.png
                #<nameField value for feature 1>_<scale 2 value>.png
                #<nameField value for feature 2>_<scale 1 value>.png
                #<nameField value for feature 2>_<scale 2 value>.png
            #This pattern continues for each of the features in the feature class provided.
            #The number of images that will be created = (Number of features in inFC) X (Number of selected scale values in the script tool)
        
arcpy.AddMessage('PNG files were added to the following folder: {}\n Verify that their are accurate.'.format(outDir))
