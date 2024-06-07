import sys
import time
import pandas as pd

from GraphBuilder import GraphBuilder
from Node import Node
from fhir_terminology_client import FhirTerminologyClient


class GraphDifferenceClustering:
    depthMultiplier = 0.1
    minDiff = 0.05
    maxClusters = 10

    def __init__(self, group_a_event_data, group_b_event_data, tx: FhirTerminologyClient, depth_multiplier, min_diff, max_clusters):
        self.assert_df_columns(group_a_event_data, ['patient_id', 'snomedCode'])
        self.assert_df_columns(group_b_event_data, ['patient_id', 'snomedCode'])
        self.group_a = group_a_event_data
        self.group_b = group_b_event_data
        self.tx = tx
        self.depthMultiplier = depth_multiplier
        self.minDiff = min_diff
        self.maxClusters = max_clusters

    @staticmethod
    def assert_df_columns(df, columns):
        for column in columns:
            assert column in df.columns, f"Missing column: {column}"
        pass

    def rank_nodes_by_difference_and_gain(self, knowledge_graph, all_codes_used, group_a_size, group_b_size):
        candidate_nodes = self.calculate_node_differences(knowledge_graph, all_codes_used, group_a_size, group_b_size,
                                                          False)

        best_nodes_with_positive_score = list()
        candidate_nodes_for_positive = set(candidate_nodes)
        print("Finding best nodes with positive difference")
        while len(best_nodes_with_positive_score) < self.maxClusters and len(candidate_nodes_for_positive) > 0:
            sorted_nodes = sorted(candidate_nodes_for_positive,
                                  key=lambda node: (node.get_depth_boosted_aggregate_group_difference(), node.get_depth()),
                                  reverse=True)
            candidate_node = sorted_nodes[0]
            if candidate_node.get_depth_boosted_aggregate_group_difference() < self.minDiff:
                break
            if not self.any_subsumption(candidate_node, best_nodes_with_positive_score):
                best_nodes_with_positive_score.append(candidate_node)
                # Clear diff of all descendants
                print(".", end="", flush=True)
                self.calculate_node_differences(knowledge_graph, candidate_node.get_code_and_descendant_codes(set()),
                                                group_a_size, group_b_size, True)
            try:
                candidate_nodes_for_positive.remove(candidate_node)
            except KeyError:
                print("Failed to remove candidate node")
        print()

        best_nodes_with_negative_score = list()
        candidate_nodes_for_negative = set(candidate_nodes)
        print("Finding best nodes with negative difference")
        while len(best_nodes_with_negative_score) < self.maxClusters and len(candidate_nodes_for_negative) > 0:
            sorted_nodes = sorted(candidate_nodes_for_negative,
                                  key=lambda node: (node.get_depth_boosted_aggregate_group_difference(), node.get_depth()),
                                  reverse=False)
            candidate_node = sorted_nodes[0]
            if candidate_node.get_depth_boosted_aggregate_group_difference() * -1 < self.minDiff:
                break
            if not self.any_subsumption(candidate_node, best_nodes_with_negative_score):
                best_nodes_with_negative_score.append(candidate_node)
                # Clear diff of all descendants
                print(".", end="", flush=True)
                self.calculate_node_differences(knowledge_graph, candidate_node.get_code_and_descendant_codes(set()),
                                                group_a_size, group_b_size, True)
            try:
                candidate_nodes_for_negative.remove(candidate_node)
            except KeyError:
                print("Failed to remove candidate node")
        print()

        all_best_nodes = list(best_nodes_with_positive_score)
        for code in best_nodes_with_negative_score:
            all_best_nodes.append(code)
        return all_best_nodes

    @staticmethod
    def any_subsumption(node, other_nodes):
        if node in other_nodes:
            return True
        node_ancestors = node.get_ancestors()
        for otherNode in other_nodes:
            if otherNode in node_ancestors or node in otherNode.get_ancestors():
                return True
        return False

    def calculate_node_differences(self, graph_builder, all_codes_used, group_a_size, group_b_size, force_zero):
        nodes = set()
        total = len(all_codes_used)
        done = 0
        last_progress = -1
        for code_used in all_codes_used:
            node = graph_builder.get_node(code_used)
            if node is not None:
                node.calculate_group_difference_with_subtypes(group_a_size, group_b_size, force_zero)
                nodes.add(node)
                for ancestor in node.get_ancestors():
                    ancestor.calculate_group_difference_with_subtypes(group_a_size, group_b_size, force_zero)
                    nodes.add(ancestor)
            done += 1
            progress = int((done/total)*100)
            if force_zero == False and progress > last_progress and progress % 5 == 0:
                print(f'{progress}%')
                last_progress = progress
        return nodes

    def run_clustering(self):
        print("< SNOMED Knowledge Graph Difference Clustering >")
        all_codes_used = pd.concat([self.group_a['snomedCode'], self.group_b['snomedCode']]).unique()
        graph_builder = self.load_knowledge_graph_from_tx(all_codes_used)

        missing_nodes = set()

        # Add patient record events into the SNOMED concept graph
        for index, row in self.group_a.iterrows():
            code = row['snomedCode']
            role_id = row['patient_id']
            node = graph_builder.get_node(code)
            if node is not None:
                node.add_group_a_patient(role_id)
            else:
                missing_nodes.add(code)

        for index, row in self.group_b.iterrows():
            code = row['snomedCode']
            role_id = row['patient_id']
            node = graph_builder.get_node(code)
            if node is not None:
                node.add_group_b_patient(role_id)
            else:
                missing_nodes.add(code)

        if len(missing_nodes) > 0:
            print(f'{len(missing_nodes)} missing nodes: {missing_nodes}')

        group_a_patient_count = len(self.group_a['patient_id'].unique())
        group_b_patient_count = len(self.group_b['patient_id'].unique())

        print("Ranking node difference")
        best_nodes = self.rank_nodes_by_difference_and_gain(graph_builder, all_codes_used,
                                                            group_a_patient_count, group_b_patient_count)

        for node in best_nodes:
            if node.label == "":
                node.set_label(self.tx.snomed_get_label(node.code))

        print("Best nodes:")
        for node in best_nodes:
            print(node)

        return best_nodes

    def load_knowledge_graph_from_tx(self, codes_used):
        # Get ancestors of all used concepts
        parents_dic = {
            138875005: []
        }
        print('> Loading relevant parts of the SNOMED CT hierarchy into a graph structure...', end='')
        for code in codes_used:
            self.get_parents_recursive(code, parents_dic)
        print()

        # nodes_dic = {}
        # for code in parents_dic:
        #     self.add_node_recursive(code, parents_dic, nodes_dic)
        # print(f'> Codes in data: {len(codes_used):,}, graph size: {len(nodes_dic):,}')

        # root_node: Node = nodes_dic[138875005]
        # root_node.record_depth(0)

        builder = GraphBuilder()
        for code in parents_dic:
            for parent in parents_dic[code]:
                builder.add_child_parent_link(code, parent)
        builder.get_root_node().record_depth(0)
        return builder

    def add_node_recursive(self, code, parents_dic, nodes_dic):
        parents = set()
        for parent in parents_dic[code]:
            parent_node = self.add_node_recursive(parent, parents_dic, nodes_dic)
            parents.add(parent_node)

        if code in nodes_dic:
            node = nodes_dic[code]
        else:
            node = Node(code)
            nodes_dic[code] = node

        node.parent_nodes = parents
        for parent in parents:
            parent.children.add(node)
        return node

    def get_parents_recursive(self, code, parents_dic):
        parents = self.tx.snomed_get_immediate_parents(code)
        if len(parents) == 0:
            # Concept inactive, lookup active equivalents and use those as parents for this analysis
            parents = self.tx.snomed_map_inactive_to_active_codes(code)
        parents_dic[code] = parents
        if len(parents_dic) % 100 == 0:
            print('.', end='')
        for parent in parents:
            parent_code = parent['code']
            if parent_code not in parents_dic:
                self.get_parents_recursive(parent_code, parents_dic)
        pass

    def run_clustering_a(self, knowledge_graph_file, knowledge_graph_labels_file, instance_data_file,
                         instance_cohorts_file, group_b_indicator):

        print(time.time())
        print("< Graph Pattern Analysis >")
        print("Loading knowledge graph")
        graph_builder = self.load_knowledge_graph(knowledge_graph_file)
        self.load_knowledge_graph_labels(graph_builder, knowledge_graph_labels_file)
        print("Loading patient records")
        patient_records = self.load_patient_records(instance_data_file)
        print("Loading patient cohorts")
        patient_cohorts = self.load_patient_cohorts(instance_cohorts_file)
        all_codes_used = set()
        group_a_size = 0
        group_b_size = 0
        for cohort_id in patient_cohorts:
            if cohort_id == group_b_indicator:
                group_b_cohort = patient_cohorts[group_b_indicator]
                group_b_size = len(group_b_cohort)
                for patient_id in group_b_cohort:
                    if patient_id in patient_records:
                        patient_events = patient_records[patient_id]
                        for patient_event in patient_events:
                            graph_builder.get_node(patient_event).add_group_b_patient(patient_id)
                            all_codes_used.add(patient_event)
            else:
                other_cohort = patient_cohorts[cohort_id]
                group_a_size += len(other_cohort)
                for patient_id in other_cohort:
                    if patient_id in patient_records:
                        patient_events = patient_records[patient_id]
                        for patient_event in patient_events:
                            graph_builder.get_node(patient_event).add_group_a_patient(patient_id)
                            all_codes_used.add(patient_event)

        graph_builder.rootNode.record_depth(0)

        print("Ranking node difference")
        best_nodes = self.rank_nodes_by_difference_and_gain(graph_builder, all_codes_used, group_a_size, group_b_size)
        print("Best nodes:")
        for node in best_nodes:
            print(node)
        # self.calculate_node_differences(graph_builder, patient_records, group_b_indicator)
        # significant_nodes = cluster_nodes_by_difference(graph_builder, min_difference)


# This would be the entry point if running as a script
if __name__ == "__main__":
    GraphDifferenceClustering.main(sys.argv[1:])
