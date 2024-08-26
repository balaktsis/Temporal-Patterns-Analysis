import pm4py
import numpy as np
import sys
from collections import defaultdict

# Load the XES files
def load_xes(log_path):
    return pm4py.read_xes(log_path)

# Preprocess the log: split traces based on the rejected attribute
def split_log_by_rejection(log):
    success_log = []
    fail_log = []
    
    for trace in log:
        if trace.attributes["rejected"] == "false":
            success_log.append(trace)
        elif trace.attributes["rejected"] == "true":
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
def calculate_deviations(base_stats, patterns_l2, threshold):
    deviations = {}
    for pattern, durations_l2 in patterns_l2.items():
        if pattern in base_stats:
            mean_l1 = base_stats[pattern]['mean']
            deviations[pattern] = []
            for duration in durations_l2:
                deviation = duration - mean_l1
                if abs(deviation) > threshold:
                    deviations[pattern].append((duration, deviation, "Violated"))
                else:
                    deviations[pattern].append((duration, deviation, "Ok"))
    return deviations

# Main function to process the logs and analyze patterns
def analyze_logs(log_path, support_threshold, deviation_threshold):
    # Load the log
    log = load_xes(log_path)
    
    # Preprocess: Split log into success and failure logs based on 'rejected' attribute
    log_l1, log_l2 = split_log_by_rejection(log)
    
    # Extract patterns and calculate their statistics
    patterns_l1 = extract_patterns(log_l1)
    patterns_l2 = extract_patterns(log_l2)
    
    # Filter patterns based on support
    patterns_l1 = {k: v for k, v in patterns_l1.items() if len(v) >= support_threshold}
    patterns_l2 = {k: v for k, v in patterns_l2.items() if len(v) >= support_threshold}
    
    # Calculate statistics for L1 patterns
    stats_l1 = calculate_statistics(patterns_l1)
    
    # Calculate deviations for patterns in L2
    deviations = calculate_deviations(stats_l1, patterns_l2, deviation_threshold)
    
    return stats_l1, deviations


if __name__ == '__main__':
    log_path = sys.argv[1]  # path to the XES log file
    support_threshold = 5  # minimum support to consider a pattern
    deviation_threshold = 10  # threshold for violation in seconds

    # Run analysis
    stats_l1, deviations = analyze_logs(log_path, support_threshold, deviation_threshold)
 
    # Output results
    for pattern, stats in stats_l1.items():
        print(f"Pattern {pattern}: Mean = {stats['mean']}, Std = {stats['std']}")

    print("\nDeviations in L2:")
    for pattern, deviation_list in deviations.items():
        print(f"\nPattern {pattern}:")
        for duration, deviation, status in deviation_list:
            print(f"Duration: {duration}, Deviation: {deviation}, Status: {status}")
