from fhir_terminology_client import *
import pandas as pd

# Run Snowstorm Lite locally
# https://github.com/IHTSDO/snowstorm-lite
tx = fhir_terminology_client("http://localhost:8080/fhir")

# Load clinical event data
all_events = pd.read_csv('synthetic-data/events.csv')
print(f'All events: {len(all_events):,}')

# Create cohort of patients with COVID detected
# SNOMED CT code: 1240581000000104 |Severe acute respiratory syndrome coronavirus 2 detected (finding)|
# http://snomed.info/id/1240581000000104
covid_detected = 1240581000000104
covid_detected_codes = tx.expand_vs_as_codes(f'http://snomed.info/sct?fhir_vs=isa/{covid_detected}')
covid_detected_cases = all_events.query('conceptId in @covid_detected_codes')['roleId'].unique()
covid_detected_events = all_events.query('roleId in @covid_detected_cases')
print(f'COVID Detected patients: {len(covid_detected_cases):,}')

# Count patients in cohort with Pneumonia caused by COVID
# SNOMED CT code: 882784691000119100 |Pneumonia caused by severe acute respiratory syndrome coronavirus 2 (disorder)|
covid_pneumonia = 882784691000119100
covid_pneumonia_codes = tx.expand_vs_as_codes(f'http://snomed.info/sct?fhir_vs=isa/{covid_pneumonia}')
covid_pneumonia_cases = covid_detected_events.query('conceptId in @covid_pneumonia_codes')['roleId'].unique()
covid_pneumonia_percentage = (len(covid_pneumonia_cases) / len(covid_detected_cases)) * 100
print(f'COVID Pneumonia percentage: {covid_pneumonia_percentage}')

# Count patient records with dead
# SNOMED CT code: 419099009 |Dead (finding)|
dead_code = 419099009
dead_codes = tx.expand_vs_as_codes(f'http://snomed.info/sct?fhir_vs=isa/{dead_code}')
dead_cases = covid_detected_events.query('conceptId in @dead_codes')['roleId'].unique()
dead_percentage = (len(dead_cases) / len(covid_detected_cases)) * 100
print(f'Dead percentage: {dead_percentage}')
