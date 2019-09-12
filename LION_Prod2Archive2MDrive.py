import os, re, traceback, sys, datetime, arcpy, ConfigParser

try:
    # Set configuration file paths

    config = ConfigParser.ConfigParser()
    config.read(r"LION_config_sample.ini")
    log_path = config.get('PATHS', 'Log_Path')
    log = open(log_path, "a")
    StartTime = datetime.datetime.now().replace(microsecond = 0)
    print("Import complete")
    print("ArcMap Version: " + str(arcpy.GetInstallInfo()['Version']))

    # Set paths to sde archive and lion/dist folder.

    sde_prod_env = config.get('PATHS', 'PROD_SDE_Path')
    archive_sde_path = config.get('PATHS', 'Archive_SDE_Path')
    m_path = config.get('PATHS', 'M_Path')
    mxd_path = config.get('PATHS', 'MXD_Path')

    # Disconnect users from Production SDE to prohibit any schema locks if necessary

    arcpy.AcceptConnections(sde_prod_env, False)
    arcpy.DisconnectUser(sde_prod_env, "ALL")

    print("Setting workspace environment to SDE Production")
    arcpy.env.workspace = sde_prod_env
    print("Environment established")

    current_version = '19B'

    # Define variable as a list of all Feature Class objects in production SDE

    print("Beginning to parse workspace feature classes")
    prod_feature_list = arcpy.ListFeatureClasses()
    print("Feature classes parsed")

    # Define variable as list holding only LION/District Feature Classes in Production directory

    lion_list = []
    for fc in prod_feature_list:
        if "LION" in fc:
            print("Moving {} to list of FCs to archive").format(fc)
            lion_list.append(fc)

    # Parse Production SDE for all available Feature Classes

    print("Selecting only desired feature classes from Production directory based on LION_FCs_4_Archive.txt file")
    lion_features_file = config.get('PATHS', 'LION_Features_List')
    lion_features = open(lion_features_file, 'r')

    # Define list of desired LION/District Feature Classes from Production

    desired_fcs_list = [line.split(',') for line in lion_features.readlines()]

    desired_fcs_list = desired_fcs_list[0]
    desired_fcs_set = set()

    for item in lion_list:
        for fc in desired_fcs_list:
            if (fc in item) or ("GISPROD.SDE.LION" == item):
                desired_fcs_set.add(item)

    print("The feature classes to be archived from production are as follows:")

    for item in desired_fcs_set:
        print(item)

    # Copy selection of desired LION/District Features to SDE Archive

    for fc in desired_fcs_set:
        if arcpy.Exists(os.path.join(archive_sde_path, fc)):
            print("The following FC already exists in the archive and will be skipped:")
            print(fc, os.path.join(archive_sde_path, fc))
        else:
            print(fc, os.path.join(archive_sde_path, fc))
            arcpy.Copy_management(fc, os.path.join(archive_sde_path, fc))

    # Connect to SDE Archive dir and define variable as list of all LION/District Feature Classes within the archive

    print("Establishing environment connection to Archive SDE.")
    arcpy.env.workspace = archive_sde_path
    print("Environment established")

    print("Beginning to crawl workspace feature classes")
    feature_list = arcpy.ListFeatureClasses()

    lion_list = []
    for fc in feature_list:
        # Check list of SDE feature classes for those that contain LION keyword
        if "LION" in fc:
            print("Appending {} to lion list").format(fc)
            lion_list.append(fc)

    # From previous Archive list, create new list, but only retain those lacking a version number.
    # Feature classes with a missing version number are those that have just been archived.

    new_lion_list = [fc for fc in lion_list if not re.match('^.{20}\d', fc)]
    print(new_lion_list)

    # Rename archived LION datasets to include appropriate version number

    for item in new_lion_list:
        # Check if feature class is a LION sub-dataset (not stand-alone). Use specific naming conventions based on check
        if "LION_" in item:
            print("Replacing " + str(item) + " with: "
                  + str(item.replace("LION_", "LION_" + str(current_version) + "_")))
            arcpy.Rename_management(item, item.replace("LION_", "LION_" + str(current_version) + "_"))
        # Check if feature class is LION stand-alone. Use specific naming conventions based on check
        elif "LION_" not in item:
            print("Replacing " + str(item) + " with: "
                  + str(item.replace("LION", "LION_" + str(current_version))))
            arcpy.Rename_management(item, item.replace("LION", "LION_" + str(current_version)))

    # Begin process for moving Feature Classes from SDE Archive to M: Drive Archive
    # Set list of acceptable version numbers

    accepted_version = ['B', 'C', 'D']

    lion_version_desired = current_version

    # If LION version is within the list of acceptable version numbers, assign previous version letter
    if lion_version_desired[2] in accepted_version:
        prev_letter = chr(ord(lion_version_desired[2]) - 1)
        lion_version_prev = lion_version_desired.replace(lion_version_desired[2], prev_letter)
    else:
    # If LION version is not within the list of acceptable version numbers, assign a previous version letter of 'D'
        version_yr = lion_version_desired[:2]
        prev_version_yr = int(version_yr) - 1
        lion_version_prev = str(prev_version_yr) + 'D'

    # Set paths for previously archived files
    sde_source_new = 'GISARCHIVE.SDE.LION_' + lion_version_desired
    print("Paths Set. You will be Archiving LION/Districts version {}").format(lion_version_desired)
    print("Previous Version -> {}".format(lion_version_prev))

    # Search SDE Archive for previously archived files from production
    print("Beginning to crawl Archive SDE")
    arcpy.env.workspace = archive_sde_path
    fc_list = arcpy.ListFeatureClasses()
    print("Crawl complete")

    # Select only desired version of LION and Districts
    lion_version_list = []
    try:
        for feature in fc_list:
            if "LION" in feature:
                lion_version_actual = feature.split("_")[-2]
                if len(lion_version_actual) == 3:
                    if lion_version_actual == lion_version_desired:
                        lion_version_list.append(feature)
                else:
                    lion_version_actual = feature.split("_")[-1]
                    if lion_version_actual == lion_version_desired:
                        lion_version_list.append(feature)
                    else:
                        continue
    except Exception:
        raise

    # Define dictionary for M: drive layer naming conventions using SDE feature class titles.

    lion_name_dict = {"node": "LION - Nodes",
                      "nyad": "NYAD - New York State Assembly Districts",
                      "nyadwi": "NYADWI - New York State Assembly Districts - Water Included",
                      "nyap": "NYAP - Atomic Polygons",
                      "nybb": "NYBB - Borough Boundaries",
                      "nybbwi": "NYBBWI - Borough Boundaries - Water Included",
                      "nycb2000": "NYCB2000 - 2000 Census Blocks",
                      "nycb2000wi": "NYCB2000WI - 2000 Census Blocks - Water Included",
                      "nycb2010": "NYCB2010 - 2010 Census Blocks",
                      "nycb2010wi": "NYCB2010WI - 2010 Census Blocks - Water Included",
                      "nycc": "NYCC - City Council Districts",
                      "nyccwi": "NYCCWI - New York City Council Districts - Water Included",
                      "nycd": "NYCD - Community Districts",
                      "nycdwi": "NYCDWI - Community Districts - Water Included",
                      "nycg": "NYCG - Congressional Districts",
                      "nycgwi": "NYCGWI - Congressional Districts - Water Included",
                      "nyct2000": "NYCT2000 - 2000 Census Tracts",
                      "nyct2000wi": "NYCT2000WI - 2000 Census Tracts - Water Included",
                      "nyct2010": "NYCT2010 - 2010 Census Tracts",
                      "nyct2010wi": "NYCT2010WI - 2010 Census Tracts - Water Included",
                      "nyed": "NYED - Election Districts",
                      "nyedwi": "NYEDWI - Election Districts - Water Included",
                      "nyfb": "NYFB - Fire Battalions",
                      "nyfc": "NYFC - Fire Companies",
                      "nyfd": "NYFD - Fire Divisions",
                      "nyha": "NYHA - Health Areas",
                      "nyhc": "NYHC - Health Center Districts",
                      "nyhez": "NYHEZ - Hurricane Evacuation Zone",
                      "nymc": "NYMC - Municipal Court Districts",
                      "nymcwi": "NYMCWI - Municipal Court Districts - Water Included",
                      "nynta": "NYNTA - Neighborhood Tabulation Area",
                      "nypp": "NYPP - Police Precints",
                      "nypuma": "NYPUMA - PUMAs",
                      "nysd": "NYSD - School Districts",
                      "nyss": "NYSS - New York State Senate Districts",
                      "nysswi": "NYSSWI - New York State Senate Districts - Water Included"}

    # Define layers with special cases. The layers in sym_layers need to be symbolized appropriately using
    # ApplySymbologyFromLayer. The Symbology is derived from the previous version's layer symbology.
    # E.g. special case 18B layers get symbolized using 18A for each unique layer or 19A by 18D symbology.

    sym_layers = ['LION - Generic.lyr', 'LION - Roadbeds.lyr', 'LION - Street Name Labels.lyr',
                  'LION Streets - Generic.lyr', 'LION Streets - Roadbeds.lyr']

    # Export layer files from SDE to M Drive for specified LION/Districts version. Special case layers that require
    # specific symbology are handled by len(fc_comp) == 2 conditional logic. All others are handle with subsequent logic


    # Set path to translation file used for metadata transfer
    Arcdir = arcpy.GetInstallInfo("desktop")["InstallDir"]
    translator = Arcdir + "Metadata/Translator/ARCGIS2FGDC.xml"

    # Set path to MXD document for export of layer files
    mxd = arcpy.mapping.MapDocument(mxd_path)

    # Set MXD dataframe variable for layer feature export
    df = arcpy.mapping.ListDataFrames(mxd, "*")[0]

    # Checking for existence of current version directory
    print("Checking if necessary directory exists")
    if os.path.exists(os.path.join(m_path, lion_version_desired)):
        print("{} directory exists. Continuing".format(os.path.join(m_path, lion_version_desired)))
    else:
        print("{} directory does no exist. Creating now".format(os.path.join(m_path, lion_version_desired)))
        os.mkdir(os.path.join(m_path, lion_version_desired))

    for fc in lion_version_list:
        print(fc)
        fc_comp = fc.split("_")
        if len(fc_comp) == 2:
            print("Archiving special case SDE files to M Drive")
            for item in sym_layers:
                special_case = os.path.join(m_path, lion_version_desired, item)
                if os.path.isfile(special_case):
                    print("Layer Already Exists. Please delete layer and associated xml if you wish to re-generate it.")
                else:
                    print(special_case)
                    arcpy.MakeFeatureLayer_management(os.path.join(m_path, lion_version_prev, item), item)
                    arcpy.SaveToLayerFile_management(item, os.path.join(m_path, lion_version_desired, item))
                    special_case_old = special_case.replace(lion_version_desired, lion_version_prev)
                    arcpy.ExportMetadata_conversion(os.path.join(archive_sde_path, fc), translator, special_case + '.xml')
                    addLayer = arcpy.mapping.Layer(os.path.join(m_path, lion_version_desired, item))
                    arcpy.mapping.AddLayer(df, addLayer, "BOTTOM")
                    lyrs = arcpy.mapping.ListLayers(mxd)
                    for lyr in lyrs:
                        print(lyr, lyr.name)
                        if lyr.supports("DATASOURCE"):
                            print("Setting new Data Source for layer. Previous: ")
                            print(lyr, lyr.dataSource)
                            lyr.replaceDataSource(archive_sde_path, 'SDE_WORKSPACE', sde_source_new, True)
                            lyr.saveACopy(os.path.join(m_path, lion_version_desired, item))
                            print("New Data Source set. New: ")
                            print(lyr, lyr.dataSource)
                        if "Labels" in lyr.name:
                            if lyr.supports("LABELCLASSES"):
                                lc = lyr.labelClasses
                                print(lc)
                                lyr.labelClasses[0].expression = '[Street]'
                                lyr.showLabels = True
                                lyr.saveACopy(os.path.join(m_path, lion_version_desired, item))

                    # Convert new layer symbology from old layers.

                    arcpy.ApplySymbologyFromLayer_management(special_case, special_case_old)

                    print("Feature archived")
        else:
            print("Archiving regular case SDE file to M Drive")
            regular_case = os.path.join(m_path, lion_version_desired, lion_name_dict[fc_comp[2]])
            regular_case = regular_case + '.lyr'
            if os.path.isfile(regular_case):
                print("Layer Already Exists. Please delete layer and associated xml if you wish to re-generate it.")
            else:
                regular_case_old = regular_case.replace(lion_version_desired, lion_version_prev)
                if os.path.isfile(regular_case_old):
                    print(regular_case)
                    arcpy.MakeFeatureLayer_management(os.path.join(archive_sde_path, fc), fc)
                    arcpy.SaveToLayerFile_management(fc, regular_case)
                    arcpy.ExportMetadata_conversion(os.path.join(archive_sde_path, fc), translator, regular_case + '.xml')
                    arcpy.ApplySymbologyFromLayer_management(regular_case, regular_case_old)
                    print("Feature archived")
                else:
                    print("{} does not exist. Please check previous version export".format(regular_case))

    EndTime = datetime.datetime.now().replace(microsecond = 0)
    print("Script runtime: {}".format(EndTime - StartTime))
    log.write(str(StartTime) + "\t" + str(EndTime) + "\t" + str(EndTime - StartTime) + "\t" + str(lion_version_desired)
              + "\n")
    log.close()

    arcpy.AcceptConnections(sde_prod_env, True)

except:
    arcpy.AcceptConnections(sde_prod_env, True)
    print("error")
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages() + "\n"

    print(pymsg)
    print(msgs)

    log.write("" + pymsg + "\n")
    log.write("" + msgs + "")
    log.write("\n")
    log.close()