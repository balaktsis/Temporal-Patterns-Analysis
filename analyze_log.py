import pm4py
import numpy as np
import sys
import matplotlib.pyplot as plt
from collections import defaultdict

# Load the XES files
def load_xes(log_path):
    return pm4py.read_xes(log_path)

def find_names(log):
    names = []
    for trace in log:
        names.append(trace[-1]['concept:name'])
        if(trace[-1]['concept:name'] == 'Cancel Invoice Receipt'):
            for event in trace:
                print(event)
            exit(0)
    return set(names)

# Preprocess the log: split traces based on the rejected attribute
def split_log_by_rejection(log):
    success_log = []
    fail_log = []
    
    # 2017
    for trace in log:
        if any(word in trace[-1]['concept:name'] for word in {'A_Pending', 'A_denied', 'A_Cancelled', 'A_Approved'}):
            success_log.append(trace)
        else:
            fail_log.append(trace)    
    return success_log, fail_log

# Extract activity pairs and their durations from a log
def extract_patterns(log):
    patterns = defaultdict(list)

    for trace in log:
        events = trace._list
        for i in range(len(events) - 1):
            act1, act2 = events[i]['concept:name'], events[i+1]['concept:name']
            time1, time2 = events[i]['time:timestamp'], events[i+1]['time:timestamp']
            duration = (time2 - time1).total_seconds()
            patterns[(act1, act2)].append(duration)
    return patterns

# Calculate mean, std and other metrics for each pattern in L1
def calculate_statistics(patterns):
    stats = {}
    for pattern, durations in patterns.items():
        mean_duration = np.mean(durations)
        std_duration = np.std(durations)
        stats[pattern] = {
            'mean': mean_duration,
            'std': std_duration,
            'durations': durations
        }
    return stats

# Calculate deviation of patterns in L2 from the base log L1
def calculate_deviations(base_stats, patterns_l2):
    deviations = {}
    for pattern, durations_l2 in patterns_l2.items():
        if pattern in base_stats:
            mean_l1 = base_stats[pattern]['mean']
            deviations[pattern] = []
            for duration in durations_l2:
                deviation = duration - mean_l1
                if abs(deviation) > base_stats[pattern]['std']:
                    deviations[pattern].append((duration, deviation, "Violated"))
    return deviations


# Main function to process the logs and analyze patterns
def analyze_logs(log_path):
    # Load the log
    log = load_xes(log_path)

    # print(find_names(log))
    # exit(1)


    # Preprocess: Split log into success and failure logs based on 'rejected' attribute
    log_l1, log_l2 = split_log_by_rejection(log)
    
    print(log_l1[0])

    support_threshold = 1 # * len(log)
    
    # Extract patterns and calculate their statistics
    patterns_l1 = extract_patterns(log_l1)
    patterns_l2 = extract_patterns(log_l2)
    
    # Filter patterns based on support
    patterns_l1 = {k: v for k, v in patterns_l1.items() if len(v) >= support_threshold}
    patterns_l2 = {k: v for k, v in patterns_l2.items() if len(v) >= support_threshold and k in patterns_l1}

    
    # Calculate statistics for L1 patterns
    stats_l1 = calculate_statistics(patterns_l1)
    
    # Calculate statistics for L2 patterns
    stats_l2 = calculate_statistics(patterns_l2)
    
    # Calculate deviations for patterns in L2
    deviations = calculate_deviations(stats_l1, patterns_l2)

    return stats_l1, stats_l2, deviations


if __name__ == '__main__':
    log_path = sys.argv[1]  # path to the XES log file
    std_threshold = 1.2

    # Run analysis
    stats_l1, stats_l2, deviations = analyze_logs(log_path)


    with open("violating-patterns.txt", "w") as file:
        file.write("Patterns frequently violated in L2:\n")
        for pattern, stats in stats_l2.items():
            if abs(stats['mean'] - stats_l1[pattern]['mean']) > std_threshold * stats_l1[pattern]['std']:
                file.write(f"Pattern {pattern}: Mean_L1 = {stats_l1[pattern]['mean']:.4f}, Mean_L2 = {stats['mean']:.4f}\n")

    with open("deviations.txt", "w") as file:
        file.write("Deviations in L2:\n")
        for pattern, deviation_list in deviations.items():
            if len(deviation_list) > 0:
                file.write(f"\nPattern in L1 {pattern}: Mean = {stats_l1[pattern]['mean']:.4f}, Std = {stats_l1[pattern]['std']:.4f}\n")
                for duration, deviation, status in deviation_list:
                    file.write(f"Duration: {duration:.4f}, Deviation: {deviation:.4f}\n")

