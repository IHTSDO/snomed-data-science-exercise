import requests


class FhirTerminologyClient:

    def __init__(self, api_url, logging=False):
        self.api_url = api_url
        self.logging = logging

    def expand_vs_as_codes(self, vs_url):
        return self._expand_vs(vs_url, False)

    def expand_vs_as_codes_with_labels(self, vs_url):
        return self._expand_vs(vs_url, True)

    def _expand_vs(self, vs_url, include_labels):
        codes = []
        offset = 0
        count = 10000
        more_results = True
        total = 0
        while more_results:
            full_url = f'{self.api_url}/ValueSet/$expand?count={count}&offset={offset}&url={vs_url}'
            if self.logging and offset == 0:
                print(f'>  Fetching ValueSet {vs_url} from FHIR Terminology Server - {full_url}')
            response = requests.get(full_url)
            json = response.json()
            total = json['expansion']['total']
            more_results = total > offset + count
            if 'contains' in json['expansion']:
                for coding in json['expansion']['contains']:
                    if include_labels:
                        codes.append({'code': int(coding['code']), 'label': coding['display']})
                    else:
                        codes.append(int(coding['code']))
            offset += count
            if self.logging & total > (count * 3):
                print('.', end='')
        if self.logging & total > (count * 3):
            print()
        return codes
