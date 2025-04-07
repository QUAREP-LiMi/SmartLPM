"""    
@author: Nasser Darwish, Institute of Science and Technology Austria

This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import csv, os
# from datetime import datetime

class TSVAccess():

    def fieldValuesFromTSV(fields, fullFilePath):
        
        fieldValues = []
        with open(fullFilePath) as tsv_file:
            tsvReader = csv.reader(tsv_file, delimiter='\t')
            for row in tsvReader:
                if len(row)>1:
                    name, value = row
                    #print("name: ", name, " - value: ", value)
                    if name in fields:                        
                        if ',' in value and '[' in value and ']' in value:                            
                            strVal = value[1:-1].split(',')
                            value = []
                            for element in strVal: value.append(int(element))                            
                        else:
                            try:
                                value = int(value)                                
                            except ValueError:
                                # If conversion fails, treat it as a string
                                # In case there are quote signs we remove them:
                                if '\'' in value or '\"' in value:
                                    # remove the first and last chars
                                    value = value[1:-1]
                                
                        print(row, value)
                        fieldValues.append(value)
        return fieldValues

    def overwriteFieldValueTSV(field, newValue, fullFilePath):

        temp_file_path = fullFilePath + '.tmp'
        field_found = False
        with open(fullFilePath, 'r', newline='') as tsv_file, open(temp_file_path, 'w', newline='') as temp_file:
            tsvReader = csv.reader(tsv_file, delimiter='\t')
            tsvWriter = csv.writer(temp_file, delimiter='\t')

            for row in tsvReader:
                if len(row) > 1 and row[0] == field:
                    row[1] = str(newValue)
                    field_found = True
                tsvWriter.writerow(row)
        if not field_found:
            raise ValueError(f"Field '{field}' not found in the TSV file.")
        os.replace(temp_file_path, fullFilePath)


def main():

    fieldNames = [
        "wavelengths",
        "setPowers",
        "measurementInterval",
        "averageInterval",
        "readoutInterval",
        "duration",
        "signaturePause",
        "order"]                 

    settingsFilePath = os.path.dirname(__file__)+"/Config/process.tsv"
    parameterValues = TSVAccess.fieldValuesFromTSV(fieldNames, settingsFilePath)  
    print(parameterValues)



if __name__ == "__main__":   
    main()