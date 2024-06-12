from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo
import os
import pandas as pd

class Subsystem(GeomBase):
    height = Input(10)
    mass = Input(0.01)
    power = Input(0.01)
    cost = Input(0.01) #implement specific range for mass, power, cost (rating on 3?)

    # we force width and length to be always equal to 100 mm to adhere to CubeSat form factor!
    width = 100
    length = 100

    def read_subsystems_from_csv(self, subsystem_file_name):
        """Read subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', subsystem_file_name)
        obc_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(obc_info_path)

    def component_selection(self,component, filter_key, filter_value, comparator='greater',is_comm=False, tgs=None):
        """Filter components and select the best component based on the score."""
        filtered_list = []

        # calculate mean and standard deviation of Mass Cost and Power
        mass_mean = component['Mass'].mean()
        mass_std = component['Mass'].std()
        cost_mean = component['Cost'].mean()
        cost_std = component['Cost'].std()

        # For communication subsystem, calculate a combined power value
        if is_comm and tgs is not None:
            power_combined = component['Power_DL'] * (tgs / 24) + component['Power_Nom'] * (1 - (tgs / 24))
            power_mean = power_combined.mean()
            power_std = power_combined.std()
        else:
            power_mean = component['Power'].mean()
            power_std = component['Power'].std()
         
        for index, row in component.iterrows():
            if comparator == 'greater':
                FILTER_CONDITION = row[filter_key] > filter_value
            else:
                FILTER_CONDITION = row[filter_key] < filter_value

            if FILTER_CONDITION:
                norm_mass = ( row['Mass'] - mass_mean ) / mass_std
                # norm_power = ( row['Power'] - power_mean) / power_std
                norm_cost = ( row['Cost'] - cost_mean) / cost_std

                if is_comm and tgs is not None:
                    norm_power = (row['Power_DL'] * (tgs / 24) + row['Power_Nom'] * (1 - (tgs / 24)) - power_mean) / power_std
                else:
                    norm_power = (row['Power'] - power_mean) / power_std

                score = (
                    norm_mass * self.parent.mass_factor +
                    norm_cost * self.parent.cost_factor +
                    norm_power * self.parent.power_factor
                )
                filtered_list.append({
                    'index': index,
                    'Company': row.get('Company',None),
                    'Data_Rate': row.get('Data_Rate', None), 
                    'Pointing_Accuracy': row.get('Pointing_Accuracy', None),
                    'Storage': row.get('Storage', None),
                    'Form_factor': row.get('Form_factor', None),
                    'Type': row.get('Type', None),
                    'Power': row.get('Power',None),
                    'Power_DL': row.get('Power_DL', None),
                    'Power_Nom': row.get('Power_Nom', None),
                    'Mass': row['Mass'],
                    'Height': row.get('Height'),
                    'Cost': row['Cost'],
                    'Min_Temp':row.get('Min_Temp', None),
                    'Max_Temp':row.get('Max_Temp', None),
                    'Score': score
                })
        
        if len(filtered_list) == 0:
            raise ValueError("No suitable component found based on the criteria.")
        
        selected = min(filtered_list, key=lambda x: x['Score'])
        self.mass = selected["Mass"]
        self.power = selected["Power"]
        self.cost = selected["Cost"]

        return selected

    
    
    @Attribute
    def CoM(self):
        return Point(x=0.5*self.width, y=0.5*self.length, z=0.5*self.height)
    
    @Part
    def bounding_box(self):
        """
        Example of dynamic type chosen from type_dict, based on user input dyn_input_key
        :return: DynamicType
        input must be provided for all classes. DynamicType will automatically select those
        necessary to the selected class
        """
        return Box(length=self.length, 
                   width=self.width, 
                   height=self.height)
    

if __name__ == "__main__":
    from parapy.gui import display
    obj = Subsystem(height=1, width=1, length=1, diameter=1, shape="box")
    display(obj)