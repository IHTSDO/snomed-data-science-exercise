from fhir_terminology_client import FhirTerminologyClient
import pandas as pd
from GraphDifferenceClustering import GraphDifferenceClustering

# Run Snowstorm Lite locally
# https://github.com/IHTSDO/snowstorm-lite
tx = FhirTerminologyClient("http://localhost:8080/fhir")

# Load clinical event data
# Columns are patient_id, date, snomedCode
all_events = pd.read_csv('synthetic-data/events.csv')
print(f'Total event count: {len(all_events):,}')
unique_patient_ids = all_events['patient_id'].unique()
print(f'Total patient count: {len(unique_patient_ids):,}')

# Create cohort of patients with COVID detected
# SNOMED CT code: 1240581000000104 |Severe acute respiratory syndrome coronavirus 2 detected (finding)|
# http://snomed.info/id/1240581000000104
covid_detected = 1240581000000104
covid_detected_snomed_codes = tx.expand_vs_as_codes(f'http://snomed.info/sct?fhir_vs=isa/{covid_detected}')
patient_ids_with_covid_detected = all_events.query('snomedCode in @covid_detected_snomed_codes')['patient_id'].unique()
events_from_covid_detected_cases = all_events.query('patient_id in @patient_ids_with_covid_detected')
print(f'COVID Detected patients: {len(patient_ids_with_covid_detected):,}')

# Count patients in cohort with Pneumonia caused by COVID
# SNOMED CT code: 882784691000119100 |Pneumonia caused by severe acute respiratory syndrome coronavirus 2 (disorder)|
covid_pneumonia_snomed_code = 882784691000119100
all_covid_pneumonia_snomed_codes = tx.expand_vs_as_codes(f'http://snomed.info/sct?fhir_vs=isa/{covid_pneumonia_snomed_code}')
patient_ids_with_covid_pneumonia = events_from_covid_detected_cases.query('snomedCode in @all_covid_pneumonia_snomed_codes')['patient_id'].unique()
covid_pneumonia_percentage = (len(patient_ids_with_covid_pneumonia) / len(patient_ids_with_covid_detected)) * 100
print(f'COVID Pneumonia percentage: {covid_pneumonia_percentage}')

# Count patient records with dead
# SNOMED CT code: 419099009 |Dead (finding)|
dead_code = 419099009
all_dead_snomed_codes = tx.expand_vs_as_codes(f'http://snomed.info/sct?fhir_vs=isa/{dead_code}')
patient_ids_with_dead = events_from_covid_detected_cases.query('snomedCode in @all_dead_snomed_codes')['patient_id'].unique()
dead_percentage = (len(patient_ids_with_dead) / len(patient_ids_with_covid_detected)) * 100
print(f'Dead percentage: {dead_percentage}')
print()


##
# Experimental clustering
##

# Analyse using sample of events from covid cases, first half of available data
first_half_covid_events = events_from_covid_detected_cases[0:int(len(events_from_covid_detected_cases) / 2)]

group_a_events = first_half_covid_events.query('patient_id not in @patient_ids_with_dead')
group_b_events = first_half_covid_events.query('patient_id in @patient_ids_with_dead')

# Set up and run the clustering tool
graph_clustering = GraphDifferenceClustering(group_a_events, group_b_events, tx, 0.1, 0.05, 10)
best_differentiating_concepts = graph_clustering.run_clustering()
