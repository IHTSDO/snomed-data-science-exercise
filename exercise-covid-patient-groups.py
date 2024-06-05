from fhir_terminology_client import FhirTerminologyClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Run Snowstorm Lite locally
# Quick start guide: https://github.com/IHTSDO/snowstorm-lite

# Option 1. Local Snowstorm Lite
tx = FhirTerminologyClient("http://localhost:8080/fhir")
# Option 2. Online Demo Snowstorm Lite
# tx = FhirTerminologyClient("https://snowstorm-lite.nw.r.appspot.com/fhir")

# Load clinical event data
# Columns are patient_id, date, snomedCode
all_events = pd.read_csv('synthetic-data/events.csv')
print(f'Total event count: {len(all_events):,}')
unique_patient_ids = all_events['patient_id'].unique()
print(f'Total patient count: {len(unique_patient_ids):,}')


def filter_patients(events, ecl):
    # Use SNOMED ECL Query to fetch the codes - run Terminology Server ValueSet $expand operation
    codes = tx.expand_ecl(ecl)

    # Get patient ids of matching events
    patient_ids = events.query('snomedCode in @codes')['patient_id'].unique()

    # Get subset of events, matching by patient id
    return events.query('patient_id in @patient_ids')


# Create cohort of patients with COVID detected
# SNOMED CT code: 1240581000000104 |Severe acute respiratory syndrome coronavirus 2 detected (finding)|
cohort_events = filter_patients(all_events, '<< 1240581000000104')
print(f'COVID Detected patients: {len(cohort_events["patient_id"].unique()):,}')

# Example SNOMED CT Browser, Concept URL: http://snomed.info/id/1240581000000104
# ECL guide: http://snomed.org/ecl


# Create patient group with hypertension
# Code: 38341003 |Hypertensive disorder, systemic arterial (disorder)|
print(f'cohort_events count: {len(cohort_events):}')
hypertension_events = filter_patients(cohort_events, '<< 38341003')
print(f'hypertension_events count: {len(hypertension_events):}')

# Create patient group with hypertension + pneumonia
# Code: 882784691000119100 |COVID-19 pneumonia (disorder)|
hypertension_and_pne_events = filter_patients(hypertension_events, '<< 882784691000119100')

# Create patient group with hypertension + dead
# Code: 419099009 |Dead (finding)|
hypertension_and_dead_events = filter_patients(hypertension_events, '<< 419099009')


# Create "All other patients" group. The set of patients not in any of the more specific groups.
other_events = cohort_events[~cohort_events['patient_id'].isin(hypertension_events['patient_id'])]

# Create patient group of "other" + pneumonia
# Code: 882784691000119100 |COVID-19 pneumonia (disorder)|
other_and_pne_events = filter_patients(other_events, '<< 882784691000119100')
# Create patient group of "other" + dead
# Code: 419099009 |Dead (finding)|
other_and_dead_events = filter_patients(other_events, '<< 419099009')


def patient_count(events):
    return len(events['patient_id'].unique())


#
# Create graph
#
categories = ['Hypertension', 'All other patients']
pneumonia_percent = [round((patient_count(hypertension_and_pne_events) / patient_count(hypertension_events)) * 100, 1),
                     round((patient_count(other_and_pne_events) / patient_count(other_events)) * 100, 1)]

death_percent = [round((patient_count(hypertension_and_dead_events) / patient_count(hypertension_events)) * 100, 1),
                 round((patient_count(other_and_dead_events) / patient_count(other_events)) * 100, 1)]

categories = list(reversed(categories))
pneumonia_percent = list(reversed(pneumonia_percent))
death_percent = list(reversed(death_percent))

bar_width = 0.35
index = np.arange(len(categories))

fig, ax = plt.subplots(figsize=(10, 6))

# Bars for Pneumonia caused by SARS-CoV-2
bars1 = ax.barh(index + bar_width, pneumonia_percent, bar_width, label='Pneumonia caused by SARS-CoV-2', color='salmon')

# Bars for Dead
bars2 = ax.barh(index, death_percent, bar_width, label='Dead', color='orange')

# Adding annotations
for bar in bars1:
    ax.text(bar.get_width() / 2, bar.get_y() + bar.get_height()/2,
            f'{bar.get_width():.1f}', ha='center', va='center', color='white', fontweight='bold')

for bar in bars2:
    ax.text(bar.get_width() / 2, bar.get_y() + bar.get_height()/2,
            f'{bar.get_width():.1f}', ha='center', va='center', color='white', fontweight='bold')

# Labels and title
ax.set_title('Correlation of Conditions with Outcomes')
ax.set_xlabel('Correlation Percent')
ax.set_yticks(index + bar_width / 2)
ax.set_yticklabels(categories)
ax.set_xlim(0, 100)
ax.legend()

# Show plot
plt.tight_layout()
plt.show()
