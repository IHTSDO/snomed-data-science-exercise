# Script to convert data from JSON to CSV after synthetic generation by https://github.com/IHTSDO/health-data-analytics
import json
import csv

# File paths
ndjson_file_path = 'generated-patients.ndjson'
patients_csv_path = 'patients.csv'
events_csv_path = 'events.csv'

# Initialize lists to hold patient and event data
patients_data = []
events_data = []

# Read and parse the NDJSON file
with open(ndjson_file_path, 'r') as file:
    for line in file:
        record = json.loads(line)
        # Extract patient data
        patients_data.append({
            'roleId': record['roleId'],
            'gender': record['gender'],
            'dob': record['dob']
        })
        # Extract event data if available
        if 'events' in record and record['numEvents'] > 0:
            for event in record['events']:
                events_data.append({
                    'roleId': record['roleId'],
                    'date': event['date'],
                    'conceptId': event['conceptId']
                })

# Write patients.csv
with open(patients_csv_path, 'w', newline='') as csvfile:
    fieldnames = ['roleId', 'gender', 'dob']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for patient in patients_data:
        writer.writerow(patient)

# Write events.csv
with open(events_csv_path, 'w', newline='') as csvfile:
    fieldnames = ['roleId', 'date', 'conceptId']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for event in events_data:
        writer.writerow(event)

print("CSV files have been created successfully.")
