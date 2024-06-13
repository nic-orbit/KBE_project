from parapy.core import *
from parapy.geom import *
from parapy.exchange.step import STEPReader
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance
from parapy.core.widgets import (
    Button, CheckBox, ColorPicker, Dropdown, FilePicker, MultiCheckBox,
    ObjectPicker, SingleSelection, TextField)
import pandas as pd
import numpy as np
import os
import pykep as pk
from cubesat_configurator import constants

class Structure(GeomBase):

    def read_struct_from_csv(self):
        """Read subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', 'Structure.csv')
        obc_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(obc_info_path)

    @Attribute
    def form_factor(self):
        "Calculate form factor for cubesat"
        obc_selection_list = self.parent.obc.obc_selection
        adcs_selection_list = self.parent.adcs.adcs_selection
        bat_selection_list = self.parent.power.battery_selection
        comm_selection_list = self.parent.communication.comm_selection
        total_height = obc_selection_list['Height'] + adcs_selection_list['Height'] + self.parent.payload.instrument_height + bat_selection_list['Height'] + comm_selection_list['Height']
        height_factor = total_height / 100
        
        if height_factor < 1:
            form_factor = 1
        elif height_factor < 1.5:
            form_factor = 1.5
        elif height_factor < 2:
            form_factor = 2
        elif height_factor < 3:
            form_factor = 3
        else:
            form_factor = "No available Cubesat sizes found"
        self.height = form_factor*100
        return form_factor

    @Attribute
    def _read_step_file(self):
        "Choose STEP File based on the form factor"
        form_factor = self.form_factor
        script_dir = os.path.dirname(__file__)
        
        # Map form_factor to corresponding STEP file name
        if form_factor == 1:
            subsystem_file_name = "1U.step"
        elif form_factor == 1.5:
            subsystem_file_name = "1_5U.step"
        elif form_factor == 2:
            subsystem_file_name = "2U.step"
        elif form_factor == 3:
            subsystem_file_name = "3U.step"
        else:
            raise ValueError("No STEP file available for the calculated form factor.")
        
        relative_path = os.path.join('STEP_files', subsystem_file_name)
        struct_info_path = os.path.join(script_dir, relative_path)
        return struct_info_path

    @Part
    def structure_representation(self):
        "Display STEP File"
        return STEPReader(filename=self._read_step_file)
    
    @Attribute
    def structure(self):
        form_factor_req = self.form_factor
        struct = self.read_struct_from_csv()
        struct_selection = []

        for index, row in struct.iterrows():
            # Compare the required Form Factor value with the requirements from the CSV 
            if row['Form_Factor'] == form_factor_req:
                struct_selection.append({
                    'index': index,
                    'Form_Factor': row['Form_Factor'],
                    'Mass': row['Mass'],
                    'Cost': row['Cost']
                })
        if len(struct_selection) == 0:
            raise ValueError("No suitable component found based on the criteria.") 
        
        selected_structure = struct_selection[0]
        self.mass = selected_structure['Mass']
        self.cost = selected_structure['Cost']
        
        return selected_structure