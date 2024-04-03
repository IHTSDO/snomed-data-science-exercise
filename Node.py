class Node:

    def __init__(self, code):
        self.code = code
        self.label = ""
        self.parents = set()
        self.children = set()
        self.group_a_patient_ids = set()
        self.group_b_patient_ids = set()
        self.aggregateGroupDifference = -2
        self.aggregateGroupDifferenceBackup = 0
        self.boostedAggregateGroupDifference = 0
        self.boostedAggregateGroupDifferenceBackup = 0
        self.depth = 100000

    def add_child(self, child_node):
        self.children.add(child_node)
        child_node.parents.add(self)
        return child_node

    def add_group_a_patient(self, patient_id):
        self.group_a_patient_ids.add(patient_id)

    def add_group_b_patient(self, patient_id):
        self.group_b_patient_ids.add(patient_id)

    def record_depth(self, depth):
        if self.depth > depth:
            self.depth = depth
        for child in self.children:
            child.record_depth(depth + 1)

    def get_code(self):
        return self.code

    def get_parents(self):
        return self.parents

    def get_ancestors(self):
        def _collect_ancestors(node, _ancestors):
            for parent in node.parents:
                _ancestors.add(parent)
                _collect_ancestors(parent, _ancestors)

        ancestors = set()
        _collect_ancestors(self, ancestors)
        return ancestors

    def get_code_and_descendant_codes(self, codes):
        codes.add(self.code)
        for child in self.children:
            child.get_code_and_descendant_codes(codes)
        return codes

    def calculate_group_difference_with_subtypes(self, group_a_size, group_b_size, force_zero):
        if force_zero:
            self.aggregateGroupDifference = 0
            self.boostedAggregateGroupDifference = 0
        else:
            # Count unique patients for this concept and all descendants, in each group
            concept_and_descendants_instance_count_in_group_a = self.count_unique_group_a_patients_including_subtypes()
            concept_and_descendants_instance_count_in_group_b = self.count_unique_group_b_patients_including_subtypes()

            a_strength = concept_and_descendants_instance_count_in_group_a / group_a_size
            b_strength = concept_and_descendants_instance_count_in_group_b / group_b_size
            self.aggregateGroupDifference = b_strength - a_strength
            self.update_all_diff_variables()
        pass

    def count_unique_group_a_patients_including_subtypes(self):
        return len(self.collect_unique_group_a_patients_including_subtypes(set()))

    unique_group_a_patients_including_subtypes = None

    def collect_unique_group_a_patients_including_subtypes(self, patient_ids):
        if self.unique_group_a_patients_including_subtypes is None:
            node_ids = set(self.group_a_patient_ids)
            for child in self.children:
                child.collect_unique_group_a_patients_including_subtypes(node_ids)
            self.unique_group_a_patients_including_subtypes = node_ids
        patient_ids.update(self.unique_group_a_patients_including_subtypes)
        return patient_ids

    def count_unique_group_b_patients_including_subtypes(self):
        return len(self.collect_unique_group_b_patients_including_subtypes(set()))

    unique_group_b_patients_including_subtypes = None

    def collect_unique_group_b_patients_including_subtypes(self, patient_ids):
        if self.unique_group_b_patients_including_subtypes is None:
            node_ids = set(self.group_b_patient_ids)
            for child in self.children:
                child.collect_unique_group_b_patients_including_subtypes(node_ids)
            self.unique_group_b_patients_including_subtypes = node_ids
        patient_ids.update(self.unique_group_b_patients_including_subtypes)
        return patient_ids

    def update_all_diff_variables(self):
        from GraphDifferenceClustering import GraphDifferenceClustering
        self.boostedAggregateGroupDifference = self.aggregateGroupDifference * (
                    1 + (self.depth * GraphDifferenceClustering.depthMultiplier))
        if self.boostedAggregateGroupDifferenceBackup == 0:
            self.aggregateGroupDifferenceBackup = self.aggregateGroupDifference
            self.boostedAggregateGroupDifferenceBackup = self.boostedAggregateGroupDifference
        pass

    def get_depth_boosted_aggregate_group_difference(self):
        return self.boostedAggregateGroupDifference

    def get_aggregate_group_difference(self):
        return self.aggregateGroupDifference

    def get_depth(self):
        return self.depth

    def set_label(self, label):
        self.label = label

    def __str__(self):
        return f"Node(code: {self.code}, depth_boosted_score: {self.boostedAggregateGroupDifferenceBackup}, label: {self.label})"

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.code == other.code
        return False

    def __hash__(self):
        return hash(self.code)
