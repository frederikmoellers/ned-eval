#!/usr/bin/env python3

# Licensed under the EUPL

import bisect
import ctypes
import datetime
import functools
import gc
import math
import multiprocessing
import multiprocessing.sharedctypes
import random
import socket
import sys
from typing import Iterable, List, MutableSequence, Optional, Set, Tuple, Union

import settings
from databasehandler import DatabaseHandler, Message, System

# a shared memory ctypes array to hold the complete system output including dummy messages
output_messages_shared: MutableSequence[int] = []
output_ia_times_shared: MutableSequence[int] = []


def compute_ned_dummies(chunk_genuine: List[int], system_id: Union[str, int], chunk_lambda: float):
    # if chunk_lambda is negative, do not generate any dummy traffic and just return the indentical list
    if chunk_lambda < 0:
        return chunk_genuine[0:-1]
    chunk_output: List[int] = [chunk_genuine[0]]
    # change lambda's magnitude to match that of the system's timestamps
    chunk_lambda *= settings.TIMESTAMP_PRECISION[system_id]
    # i is the index of the previous genuine message
    for i in range(len(chunk_genuine)-1):
        last: int = chunk_genuine[i]
        next_genuine: int = chunk_genuine[i+1]
        # check for outage
        if next_genuine - last > settings.INTERARRIVAL_THRESHOLDS[system_id]:
            # if outage is encountered, just skip the time between these messages
            chunk_output.append(next_genuine)
            continue
        # generate dummies until the next genuine message appears
        next_dummy: int = last
        while True:
            ned_draw = math.floor(random.expovariate(chunk_lambda))
            next_dummy += ned_draw
            if next_dummy >= next_genuine:
                break
            # append dummies to output
            chunk_output.append(next_dummy)
        chunk_output.append(next_genuine)
    return chunk_output[0:-1]


def compute_matches(system_id: Union[str, int], sample: List[int], all_interactions: List[int]):
    matches_task: int = 0 # number of matches where an interaction was performed
    matches_notask: int = 0 # number of matches where no or a different interaction was performed
    sample_duration = round(settings.SAMPLE_DURATION / settings.TIMESTAMP_PRECISION[system_id])
    # if the sample is empty, we "only" need to count the number of empty samples in the output
    if not sample:
        for ia_time in output_ia_times_shared:
            if ia_time > settings.INTERARRIVAL_THRESHOLDS[system_id]:
                continue
            matches_between: int = ia_time - sample_duration
            if matches_between > 0:
                matches_notask += matches_between
    # if the sample contains a single message, we need to look for IA times > that followed by something > sample_duration
    elif len(sample) == 1:
        for i in range(1, len(output_ia_times_shared)):
            if output_ia_times_shared[i] > settings.INTERARRIVAL_THRESHOLDS[system_id]:
                continue
            if output_ia_times_shared[i-1] > settings.INTERARRIVAL_THRESHOLDS[system_id]:
                continue
            if output_ia_times_shared[i] > sample_duration and output_ia_times_shared[i-1] > sample[0]:
                insert_p = bisect.bisect_left(all_interactions, output_messages_shared[i])
                if insert_p < len(all_interactions) and output_messages_shared[i] == all_interactions[insert_p]:
                    matches_task += 1
                else:
                    matches_notask += 1
    # if the sample contains multiple messages, the IA times of those have to match the IA times in output_ia_times_shared
    else:
        i = 0
        """
        The following loop uses a layered check to boost performance. The first
        check is fast to compute and already fails for many elements. Later
        checks are harder to compute and are therefore only executed if the sample
        is likely to match
        """
        while i < len(output_ia_times_shared) - len(sample):
            # go to the next distinct timestamp
            if output_ia_times_shared[i] == 0:
                while i < len(output_ia_times_shared) and output_ia_times_shared[i] == 0:
                    i += 1
            else:
                i += 1
            # check if first message matches
            if output_ia_times_shared[i-1] <= sample[0]:
                continue
            # check if sample matches
            match = True
            for j in range(1, len(sample)):
                if output_ia_times_shared[i+j-1] != sample[j]:
                    match = False
                    break
            if not match:
                continue
            #if output_ia_times_shared[i:i+len(sample)-1] != sample[1:]:
            #    continue
            # check if next message would still be within sample_duration
            if output_messages_shared[i+len(sample)] - output_messages_shared[i] <= sample_duration:
                continue
            task: bool = False
            # determine whether the sample contains a task
            if bisect.bisect_left(all_interactions, output_messages[i]) != bisect.bisect_left(all_interactions, output_messages[i] + sample_duration):
                matches_task += 1
            else:
                matches_notask += 1
    #print("\nReturning matches_task = {} and matches_notask = {} for sample {}".format(matches_task, matches_notask, sample))
    return matches_task, matches_notask


# split systems, from crdt/stats.py
if len(sys.argv) < 2:
    print("Usage: ned.py <database>")
    sys.exit(255)
dbh: DatabaseHandler = DatabaseHandler(sys.argv[-1])
systems: List[System] = list(dbh.systems())

sys2 = systems[1]
sys21 = System(sys2._dbh, "2.1", "System 2.1")
setattr(sys21, "messages", functools.partial(sys2.messages, to_timestamp=1352588400))
setattr(sys21, "timespan", functools.partial(sys2.timespan, override_to=1352588400))
sys22 = System(sys2._dbh, "2.2", "System 2.2")
setattr(sys22, "messages", functools.partial(sys2.messages, from_timestamp=1352588400))
setattr(sys22, "timespan", functools.partial(sys2.timespan, override_from=1352588400))
systems[1:2] = [sys21, sys22]

# print LaTeX table header
output_file_suffix: str = ""
if len(sys.argv) > 2:
    output_file_suffix = "-" + sys.argv[1]
results_latex = open(socket.gethostname() + output_file_suffix + "-ned-results-" + str(settings.SAMPLE_COUNT) + "-" + str(settings.SAMPLE_DURATION) + ".tex", "w")
print("System")
for l, _ in settings.lambdas:
    print(" & \\multicolumn{{2}}{{c}}{{$\\lambda={:.6f}$}}".format(l), end="", file=results_latex)
print(" \\\\", file=results_latex)
for l, _ in settings.lambdas:
    print("& TI & $\\varepsilon,\\delta$", end="", file=results_latex)
print(" \\\\", file=results_latex)

for system in systems:
    print("System {}:".format(system.id))
    print("{}".format(system.id), end="", file=results_latex)
    # get system timespan
    from_ts, to_ts = system.timespan()
    from_ts = round(from_ts / settings.TIMESTAMP_PRECISION[system.id])
    to_ts = round(to_ts / settings.TIMESTAMP_PRECISION[system.id])
    # make a list of genuine messages, possibly multiplying by 10^x to get integers
    genuine: List[int] = []
    # make two lists for present and absent inter-arrival times
    last_message: Optional[Message] = None
    for message in system.messages():
        timestamp = round(message.timestamp / settings.TIMESTAMP_PRECISION[system.id])
        genuine.append(timestamp)
        last_message = message
        print("    Reading genuine messages {: 3,d}%".format(round((message.timestamp - from_ts)/(to_ts - from_ts)*100)), end="\r")
    print()
    print("    {:,d} messages read".format(len(genuine)))
    # try out all specified values for lambda
    for lambd, description in settings.lambdas:
        print("    Lambda {:.6f} ({})".format(lambd, description))
        output_messages: List[int] = [genuine[0]]
        # parallellise
        with multiprocessing.Pool(initializer=random.seed) as pool:
            chunk_size: int = 5000
            results = []
            for i in range(0, len(genuine)-1, chunk_size):
                chunk = genuine[i:min(i+chunk_size+1, len(genuine))]
                results.append(pool.apply_async(compute_ned_dummies, [chunk, system.id, lambd]))
                print("        Delegating {} chunks".format(len(results)), end="\r")
            print()
            for i in range(len(results)):
                print("        Waiting for results {: 2d}/{: 2d}".format(i+1, len(results)), end="\r")
                output_messages += results[i].get()
        print()
        print("        System output: {:,d} messages ({:,d} dummies)".format(len(output_messages), len(output_messages) - len(genuine)))
        print("        Traffic increase (factor): {: 1,.2f}".format(len(output_messages) / len(genuine) - 1))
        print(" & \\num{{{:1.2f}}}".format(len(output_messages) / len(genuine) - 1), end="", file=results_latex)

        # convert output_messages into a shared_ctypes array
        print("        Converting system output...", end="")
        sys.stdout.flush()
        # note: we use a RawArray without a lock because subprocesses will only read, not write
        output_messages_shared = multiprocessing.sharedctypes.RawArray(ctypes.c_uint64, output_messages)
        print(" ✓", end="")
        sys.stdout.flush()
        output_ia_times: List[int] = [output_messages_shared[i+1] - output_messages_shared[i] for i in range(len(output_messages_shared) - 1)]
        print(" ✓", end="")
        sys.stdout.flush()
        output_ia_times_shared = multiprocessing.sharedctypes.RawArray(ctypes.c_uint64, output_ia_times)
        print(" ✓", end="")
        sys.stdout.flush()
        print()

        # get all messages from interactive devices
        print("        Estimating epsilon and delta")
        c = dbh.cursor()
        # fix split systems
        if isinstance(system.id, str):
            real_system_id: int = int(system.id[0:1])
            from_to: str = "AND messages.timestamp >= {} AND messages.timestamp <= {}".format(*system.timespan(fix=False))
        else:
            real_system_id = system.id
            from_to = ""

        c.execute("""
            SELECT DISTINCT messages.timestamp
            FROM 
                messages 
                INNER JOIN sources ON messages.message_id = sources.message_id
                INNER JOIN devices ON sources.device_id = devices.device_id
                INNER JOIN presence ON messages.message_id = presence.message_id
            WHERE
                messages.system_id = ? AND
                (
                    devices.description GLOB "*3S*" OR
                    devices.description GLOB "F *.*" OR
                    devices.description GLOB "* KF *.*" OR
                    messages.system_id = 3
                )
                {}
            ;
        """.format(from_to), (real_system_id,))
        user_interactions: List[int] = [round(r[0] / settings.TIMESTAMP_PRECISION[system.id]) for r in c.fetchall()]
        print("            {} user interactions found".format(len(user_interactions)))
        # calculate how many samples there are containing interactions and how many there are containing none
        print("            Counting samples with/without user interaction...", end="\r")
        i = 0
        samples_task_total = samples_notask_total = 0
        next_interaction_index = 0
        sample_duration = round(settings.SAMPLE_DURATION / settings.TIMESTAMP_PRECISION[system.id])
        while i < len(output_messages) and output_messages[i] < to_ts - sample_duration:
            print("            Counting samples with/without user interaction... {: 3.0f}%".format(i / len(output_messages) * 100), end="\r")
            # index of the next message after the current sample
            next_after_sample_index = bisect.bisect_left(output_messages, output_messages[i] + sample_duration)
            # if we reached the end, quit
            if next_after_sample_index == len(output_messages):
                break
            # check if there's an outage
            if output_messages[next_after_sample_index] - output_messages[i] > settings.INTERARRIVAL_THRESHOLDS[system.id]:
                i = next_after_sample_index
                next_interaction_index = bisect.bisect_left(user_interactions, output_messages[next_after_sample_index])
                continue
            # if there is no more user interaction, set it virtually beyond the end of the capture
            if next_interaction_index >= len(user_interactions):
                next_interaction = output_messages[-1] + settings.INTERARRIVAL_THRESHOLDS[system.id]
            else:
                next_interaction = user_interactions[next_interaction_index]
            to_next_interaction = next_interaction - output_messages[i]
            # if the next interaction is within the current sample, step to it
            if to_next_interaction < sample_duration:
                samples_task_total += to_next_interaction
                i = bisect.bisect_left(output_messages, next_interaction)
                next_interaction_index += 1
                continue
            # if the next interaction is somewhere within non-outage range, step to it
            if to_next_interaction < settings.INTERARRIVAL_THRESHOLDS[system.id]:
                samples_task_total += sample_duration
                samples_notask_total += to_next_interaction - sample_duration
                i = bisect.bisect_left(output_messages, next_interaction)
                next_interaction_index += 1
                continue
            # if there's an outage between here and the next interaction, step towards it
            # however, we know that there's no outage within sample_duration seconds
            samples_notask_total += output_messages[next_after_sample_index] - output_messages[i]
            i = next_after_sample_index
        print()
        print("            {} samples with tasks, {} without".format(samples_task_total, samples_notask_total))
        # compute epsilon and delta for various samples in parallel
        epsilon: float = 0.0
        delta: float = 0.0
        # keep track of which samples we already checked; make sure we don't check a sample twice (e.g. an empty one)
        samples_checked: Set[Tuple[int]] = set()
        with multiprocessing.Pool(initializer=random.seed) as pool:
            results = []
            computation_start: datetime.datetime = datetime.datetime.now()
            # make sure to get an even number of task and no-task samples if possible
            samples_task: int = 0
            samples_notask: int = 0
            print("            Delegating samples.", end="\r")
            # collect SAMPLE_COUNT samples, but use a timeout in case we don't get the number we want
            while len(results) < settings.SAMPLE_COUNT and (datetime.datetime.now() - computation_start).total_seconds() < settings.SAMPLE_TIMEOUT:
                # generate a sample start time
                sample_start_time: int = random.randint(from_ts + 1, to_ts - sample_duration)
                # collect garbage from time to time
                if sample_start_time % 100 == 0:
                    gc.collect()
                # check if it's close to or inside an outage
                insert_pos: List[int] = [
                    bisect.bisect_left(output_messages, sample_start_time),
                    bisect.bisect_left(output_messages, sample_start_time + sample_duration)
                ]
                in_outage: bool = False
                for insert_p in insert_pos:
                    if 0 < insert_p < len(output_messages) and output_ia_times[insert_p - 1] > settings.INTERARRIVAL_THRESHOLDS[system.id]:
                        in_outage = True
                        break
                if in_outage:
                    del sample_start_time, insert_pos, in_outage
                    continue
                del in_outage
                # assemble the sample
                sample: List[int] = []
                for i in range(insert_pos[0], len(output_messages)):
                    if i == insert_pos[0]:
                        difference: int = output_messages[i] - sample_start_time
                    else:
                        difference = output_messages[i] - output_messages[i-1]
                    if difference > sample_duration:
                        break
                    sample.append(difference)
                del insert_pos
                # check if sample contains an interaction
                task = False
                insert_p = bisect.bisect_left(user_interactions, sample_start_time)
                if insert_p < len(user_interactions) and user_interactions[insert_p] - sample_start_time <= sample_duration:
                    task = True
                # if we already have too many task samples, try again
                if task and samples_task > 1.5 * samples_notask + 900:
                    del sample, sample_start_time, task, insert_p
                    continue
                # if we already have too many non-task samples, try again
                elif not task and samples_notask > 1.5 * samples_task + 900:
                    del sample, sample_start_time, task, insert_p
                    continue
                # check if we already had this sample
                sample_tuple = tuple(sample)
                if sample_tuple in samples_checked:
                    del sample, sample_start_time, sample_tuple, task, insert_p
                    continue
                samples_checked.add(sample_tuple)
                del sample_tuple
                if task:
                    samples_task += 1
                else:
                    samples_notask += 1
                # now submit the sample to the subprocesses
                results.append(
                    pool.apply_async(
                        compute_matches,
                        [
                            system.id,
                            sample,
                            user_interactions
                        ]
                    )
                )
                del sample, sample_start_time, task, insert_p
                print("            Delegated {} samples; {} tasks and {} non-tasks".format(len(results), samples_task, samples_notask), end="\r")
            print()
            for i in range(1, len(results) + 1):
                print("            Waiting for results {: 3d}/{: 3d}".format(i, len(results)), end="")
                sys.stdout.flush()
                matches_task, matches_notask = results[i-1].get()

                # Pr(O|T)
                prob_1 = matches_task / samples_task_total
                # Pr(O|not(T))
                prob_2 = matches_notask / samples_notask_total
                # if either probability is 0, we have a delta
                #print("\nGot matches_task = {}, matches_notask = {} for task_total {} and notask_total {}".format(matches_task, matches_notask, samples_task_total, samples_notask_total))
                if prob_1 == 0.0 or prob_2 == 0.0:
                    delta = max(delta, prob_1, prob_2)
                else:
                    epsilon = max(epsilon, math.log(max(prob_1, prob_2) / min(prob_1, prob_2)))
                now: datetime.datetime = datetime.datetime.now()
                eta: datetime.timedelta = (now - computation_start) * (len(results) - i) / i
                eta_time: datetime.datetime = now + eta
                print("    ETA: {: 6d}s ({})".format(int(eta.total_seconds()), eta_time.strftime("%H:%M:%S")), end="\r")
            print("            Waiting for results {: 3d}/{: 3d}, total duration: {}".format(len(results), len(results), str(now - computation_start)))
        print("            Epsilon: {: .10f}".format(epsilon))
        print("            Delta:   {: .10f}".format(delta))
        print(" & $\\varepsilon={:.10f}$ $\\delta={:.10f}$".format(epsilon, delta), end="", file=results_latex)
    print(" \\\\", file=results_latex)
results_latex.close()
