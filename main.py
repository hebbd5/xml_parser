import pandas as pd
import regex as re
import argparse
from bs4 import BeautifulSoup


## Convert XML soup to JSON format
def xml_to_json(element):
    
    """
    Recursively parses XML soup, returning as JSON format 
    """
    
    if isinstance(element, str):
        return element
    
    if not element.contents:
        return element.string
    
    result = {}
    
    for child in element.children:
        
        if isinstance(child, str):
            continue
        
        if child.name not in result:
            result[child.name] = xml_to_json(child)
            
        else:
            if not isinstance(result[child.name], list):
                result[child.name] = [result[child.name]]
            result[child.name].append(xml_to_json(child))
            
    ### Directly capture text nodes without 'text' key
    if element.string and element.string.strip():
        return element.string.strip()
    
    return result



def find_relationships(entity):
    
    """
    Given a JSON entity, return all available relationship information
    """
    
    ## Confirm entity icludes relationship information
    if "relationships" not in entity.keys(): return 
    if entity["relationships"] == None: return
    
    
    ## Collect entity name
    name_ele = entity["names"]["name"]
    
    ### if name_ele is a dict, only one name entry exists
    if type(name_ele) == dict:
        
        #### Find Latin translation if more than one translation is present
        translation_element = name_ele["translations"]["translation"]
        
        if type(translation_element) == dict:
                entity_name = translation_element["formattedFullName"]

        elif type(translation_element) == list:
            for trans in translation_element:
                if trans["script"] == "Latin":
                    entity_name = trans["formattedFullName"]

    ### If name element is a list, aliases are present. Collect only primary name
    elif type(name_ele) == list:
        
        #### Find the primary name 
        for name in name_ele:
            if name["isPrimary"] == "true":
                translation_element = name["translations"]["translation"] 

                ##### Find Latin translation if more than one translation is present
                if type(translation_element) == dict:
                    entity_name = translation_element["formattedFullName"]
                                   
                elif type(translation_element) == list:
                    for trans in translation_element:
                        if trans["script"] == "Latin":
                            entity_name = trans["formattedFullName"]


    ## Collect relationship information
    relationships = entity["relationships"]["relationship"]
    rel_list = []
    
    ### if relationships is a dict, only one relationship is present
    if type(relationships) == dict:
        
        rel_type = relationships["type"]
        rel_entity = relationships["relatedEntity"]
        
        if rel_entity != None:
            rel_list = [entity_name, rel_type, rel_entity]
    
    ### If relationships is a list, multiple relationships are present 
    elif type(relationships) == list: 
        
        for rel in relationships:
            
            rel_type = rel["type"]
            rel_entity = rel["relatedEntity"]
            
            if rel_entity != None:
                rel_list.append([entity_name, rel_type, rel_entity]) 
            
    return rel_list



def format_name(entity_name):
    
    """
    Standardize the format for entity names retrieved from "formattedFullName"  
    """
    
    # Arrange name based on comma location, if present
    if ", " in entity_name:
        name_parts = entity_name.split(", ")
        entity_name = f"{name_parts[1]} {name_parts[0]}"
    
    # Apply title-case formatting
    entity_name = entity_name.title()
    
    # Capitalize any parenthetical text
    def capitalize(match):
        return match.group(1) + match.group(2).upper() + match.group(3)
    
    pattern = r'(\()([^\)]+)(\))'
    entity_name = re.sub(pattern, capitalize, entity_name)
    
    return entity_name



def main():
    
    """
    Accepts an XML of US OFAC sanctions information, returning a csv of relationship nodes and edges 
    """
    
    parser = argparse.ArgumentParser(description = "Process an XML file and extract relationship data.")
    
    parser.add_argument("input_file", 
                        help = "Path to the input XML file.")
    
    parser.add_argument("-o", 
                        "--output_file", 
                        default = "relationship_data.csv", 
                        help = "Path to the output CSV file (default: relationship_data.csv)")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, "r") as file:
            xml_data = file.read()

    except FileNotFoundError:
        logging.error(f"Input file not found: {input_file}")
        
    except XMLSyntaxError as e:
        logging.error(f"Error parsing XML: {e}")
        
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}"
        
        
    ## Convert XML to JSON format, isolate entity data 
    soup = BeautifulSoup(xml_data, features='xml')
    
    entity_json = xml_to_json(soup)
    entity_data = entity_json['sanctionsData']["entities"]["entity"]
    entity_data = [entity for entity in entity_data if entity["generalInfo"]["entityType"] in ["Individual", "Entity"]]
    
    
    ## Extract entity relationship information
    relationships = []
    
    for entity in entity_data:
        
        rel_search = find_relationships(entity)
        
        if rel_search:
            if type(rel_search[0]) == str:
                relationships.append(rel_search)
            
            elif type(rel_search == list):
                for rel in rel_search:
                    relationships.append(rel)
                
    
    ## Convert relationships into a dataframe, apply formatting  
    df = pd.DataFrame(relationships, columns=['entity_1', 'relationship', 'entity_2'])       
    df["entity_1"] = df["entity_1"].apply(format_name)
    df["entity_2"] = df["entity_2"].apply(format_name)
    
    ## Save dataframe as csv
    df.to_csv(args.output_file, index = False)
    
    ## Or return DF if desired  
    # return df
    
    
if __name__ == "__main__":
    main()