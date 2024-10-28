import os
import pandas as pd
from tqdm import tqdm
tqdm.pandas()

from NISTADS.commons.utils.datamaker.properties import GuestProperties, HostProperties
from NISTADS.commons.constants import CONFIG, DATA_PATH
from NISTADS.commons.logger import logger


# [DATASET OPERATIONS]
###############################################################################
class BuildMaterialsDataset:

    def __init__(self):        
        self.guest_props = GuestProperties()
        self.host_props = GuestProperties()
        self.extractor = GetSpeciesFromExperiments() 
        self.drop_cols = ['InChIKey', 'InChICode', 'formula'] 

    #--------------------------------------------------------------------------           
    def drop_excluded_columns(self, dataframe : pd.DataFrame):
        df_drop = dataframe.drop(columns=self.drop_cols, axis=1)

        return df_drop
    
    #--------------------------------------------------------------------------
    def add_guest_properties(self, guest_data : pd.DataFrame):              

        guest_names = guest_data['name'].to_list()
        guest_synonims = guest_data['synonyms'].to_list()
        # fetch compounds names from the adsorption dataset, and extend the current
        # list of species, then leave only unique names
        extra_compounds = self.extractor.extract_species_names()
        guest_names.extend(extra_compounds)
        guest_synonims.extend([[] for x in range(len(extra_compounds))])
        guest_names = list(set(guest_names))          
        
        guest_properties = self.guest_props.get_properties_for_multiple_guests(guest_names, guest_synonims)
        df_guest_properties = pd.DataFrame.from_dict(guest_properties)

        # Merging the new guest properties DataFrame with the original guest_data DataFrame
        guest_data['name'] = guest_data['name'].apply(lambda x : x.lower())
        df_guest_properties['name'] = df_guest_properties['name'].apply(lambda x : x.lower())
        merged_data = guest_data.merge(df_guest_properties, on='name', how='outer')

        return merged_data
    
    #--------------------------------------------------------------------------
    def add_host_properties(self, host_data : pd.DataFrame):

        # currently not implemented!
        host_data['name'] = host_data['name'].apply(lambda x : x.lower())
        return host_data
        
 

# [DATASET OPERATIONS]
###############################################################################
class BuildAdsorptionDataset:

    def __init__(self):

        self.drop_cols = ['DOI', 'category', 'tabular_data', 'digitizer', 'isotherm_type', 
                          'articleSource', 'concentrationUnits', 'compositionType']
        self.explode_cols = ['pressure', 'adsorbed_amount']

    #--------------------------------------------------------------------------           
    def drop_excluded_columns(self, dataframe : pd.DataFrame):

        df_drop = dataframe.drop(columns=self.drop_cols, axis=1)

        return df_drop

    #--------------------------------------------------------------------------           
    def split_by_mixture_complexity(self, dataframe : pd.DataFrame):   

        '''
        Splits the dataframe into two groups based on the number of adsorbates.
        
        Keywords arguments:
            dataframe (DataFrame): the raw adsorption dataset to be processed.

        Returns:
            tuple: A tuple containing two dataframes, one for each group (single_compound, binary_mixture)
        '''

        dataframe['numGuests'] = dataframe['adsorbates'].apply(lambda x : len(x))          
        df_grouped = dataframe.groupby('numGuests')
        single_compound = df_grouped.get_group(1)
        binary_mixture = df_grouped.get_group(2)                
        
        return single_compound, binary_mixture   

    #--------------------------------------------------------------------------
    def extract_nested_data(self, dataframe : pd.DataFrame): 

        '''
        Processes the experimental data contained in the given DataFrame.
        
        This function processes the experimental adsorption data, extracting and 
        transforming relevant information for single-component and binary mixture 
        datasets. Specifically, it extracts adsorbent and adsorbate details, 
        pressure, and adsorption data. The function handles different structures 
        of data based on the number of guest species present.

        Keywords arguments:
            dataframe (DataFrame): The input DataFrame containing experimental data.

        Returns:
            DataFrame: The processed DataFrame with expanded columns for further analysis.

        '''  
        dataframe['adsorbent_ID'] = dataframe['adsorbent'].apply(lambda x : x['hashkey'])      
        dataframe['adsorbent_name'] = dataframe['adsorbent'].apply(lambda x : x['name'].lower())           
        dataframe['adsorbates_ID'] = dataframe['adsorbates'].apply(lambda x : [f['InChIKey'] for f in x])            
        dataframe['adsorbate_name'] = dataframe['adsorbates'].apply(lambda x : [f['name'].lower() for f in x])

        # check if the number of guest species is one (single component dataset)
        if (dataframe['numGuests'] == 1).all():
            dataframe['pressure'] = dataframe['isotherm_data'].apply(lambda x : [f['pressure'] for f in x])                
            dataframe['adsorbed_amount'] = dataframe['isotherm_data'].apply(lambda x : [f['total_adsorption'] for f in x])
            dataframe['adsorbate_name'] = dataframe['adsorbates'].apply(lambda x : [f['name'].lower() for f in x][0])
            dataframe['composition'] = 1.0 

        # check if the number of guest species is two (binary mixture dataset)
        elif (dataframe['numGuests'] == 2).all():
            data_placeholder = {'composition' : 1.0, 'adsorption': 1.0}
            dataframe['total_pressure'] = dataframe['isotherm_data'].apply(lambda x : [f['pressure'] for f in x])                
            dataframe['all_species_data'] = dataframe['isotherm_data'].apply(lambda x : [f['species_data'] for f in x])
            dataframe['compound_1'] = dataframe['adsorbate_name'].apply(lambda x : x[0].lower())        
            dataframe['compound_2'] = dataframe['adsorbate_name'].apply(lambda x : x[1].lower() if len(x) > 1 else None)              
            dataframe['compound_1_data'] = dataframe['all_species_data'].apply(lambda x : [f[0] for f in x])               
            dataframe['compound_2_data'] = dataframe['all_species_data'].apply(lambda x : [f[1] if len(f) > 1 else data_placeholder for f in x])
            dataframe['compound_1_composition'] = dataframe['compound_1_data'].apply(lambda x : [f['composition'] for f in x])              
            dataframe['compound_2_composition'] = dataframe['compound_2_data'].apply(lambda x : [f['composition'] for f in x])            
            dataframe['compound_1_pressure'] = dataframe.apply(lambda x: [a * b for a, b in zip(x['compound_1_composition'], x['total_pressure'])], axis=1)             
            dataframe['compound_2_pressure'] = dataframe.apply(lambda x: [a * b for a, b in zip(x['compound_2_composition'], x['total_pressure'])], axis=1)                
            dataframe['compound_1_adsorption'] = dataframe['compound_1_data'].apply(lambda x : [f['adsorption'] for f in x])               
            dataframe['compound_2_adsorption'] = dataframe['compound_2_data'].apply(lambda x : [f['adsorption'] for f in x])

        return dataframe           
    
    #--------------------------------------------------------------------------
    def expand_dataset(self, single_component : pd.DataFrame, binary_mixture : pd.DataFrame):

        '''
        Expands the datasets by exploding and dropping columns.

        Keywords arguments:
            single_component (DataFrame): The single-component dataset to be processed.
            binary_mixture (DataFrame): The binary-component dataset to be processed.

        Returns:
            SC_exploded_dataset (DataFrame): The expanded single-component dataset.
            BN_exploded_dataset (DataFrame): The expanded binary-component dataset.
            
        '''       
        # processing and exploding data for single component dataset
        explode_cols = ['pressure', 'adsorbed_amount']
        drop_columns = ['date', 'adsorbent', 'adsorbates', 
                        'isotherm_data', 'adsorbent_ID', 'adsorbates_ID']
                
        SC_dataset = single_component.explode(explode_cols)
        SC_dataset[explode_cols] = SC_dataset[explode_cols].astype('float32')
        SC_dataset.reset_index(inplace=True, drop=True)       
        SC_dataset = SC_dataset.drop(columns=drop_columns, axis=1)
        SC_dataset.dropna(inplace=True)
                 
        # processing and exploding data for binary mixture dataset
        explode_cols = ['compound_1_pressure', 'compound_2_pressure',
                        'compound_1_adsorption', 'compound_2_adsorption',
                        'compound_1_composition', 'compound_2_composition']
        drop_columns.extend(['adsorbate_name', 'all_species_data', 'compound_1_data', 
                             'compound_2_data', 'adsorbent_ID', 'adsorbates_ID'])        

        BM_dataset = binary_mixture.explode(explode_cols)
        BM_dataset[explode_cols] = BM_dataset[explode_cols].astype('float32')       
        BM_dataset.reset_index(inplace=True, drop=True)        
        BM_dataset = BM_dataset.drop(columns = drop_columns)
        BM_dataset.dropna(inplace=True)    
        
        return SC_dataset, BM_dataset
 
    
# [DATASET OPERATIONS]
###############################################################################
class GetSpeciesFromExperiments:

    def __init__(self):

        self.single_component_path = os.path.join(DATA_PATH, 'single_component_adsorption.csv')        
        self.binary_mixture_path = os.path.join(DATA_PATH, 'binary_mixture_adsorption.csv') 
        self.single_component_col = 'adsorbate_name'
        self.binary_mixture_cols = ['compound_1', 'compound_2']
        

    #--------------------------------------------------------------------------
    def check_if_dataset_exist(self):

        single_component_exists = os.path.exists(self.single_component_path)
        binary_mixture_exists = os.path.exists(self.binary_mixture_path)

        return {'single_component': single_component_exists,
                'binary_mixture': binary_mixture_exists}

    #--------------------------------------------------------------------------
    def extract_species_names(self):

        check_existence = self.check_if_dataset_exist()

        species_names = set()
        if check_existence['single_component']:
            single_component = pd.read_csv(self.single_component_path, encoding='utf-8', sep=';')  
            species_names.update(single_component[self.single_component_col].dropna().unique())
        if check_existence['binary_mixture']:            
            binary_mixture = pd.read_csv(self.binary_mixture_path, encoding='utf-8', sep=';') 
            for col in self.binary_mixture_cols:
                species_names.update(binary_mixture[col].dropna().unique())
        else:
            logger.info('Adsorption experiments dataset has not been found. Species names will not be retrieved')

        return sorted(list(species_names))
     




       

