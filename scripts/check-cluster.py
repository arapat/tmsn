#!/usr/bin/env python
import argparse

from operator import itemgetter
from common import load_config
from common import query_status


def main(args):
    all_status = query_status(args)
    if len(all_status) == 0:
        print("No instance found in the cluster '{}'. Quit.".format(args["name"]))
        return
    print("{} clusters found with the name '{}'.".format(len(all_status), args["name"]))

    num_ready = 0
    for idx, status in enumerate(all_status):
        total = len(status)
        if total == 0:
            continue
        print("\nCluster {}:".format(idx + 1))
        ready = sum(t[0] == "running" for t in status)
        neighbors = list(map(itemgetter(1), status))
        print("    Total instances: {}\n    Running: {}".format(total, ready))
        if ready == 0:
            print("    Instances status: {}".format(status[0][0]))
            continue
        with open("neighbors.txt", 'w') as f:
            if total == ready:
                f.write("Ready. ")
            else:
                f.write("NOT ready. ")
            f.write("IP addresses of all instances:\n")
            f.write('\n'.join(neighbors))
        print("    The public IP addresses of the instances have been written into "
              "`./neighbors.txt`")
    if num_ready > 1:
        print("WARN: More than 1 cluster with the name '{}' exists. "
              "Only the IP addresses of the instances of the last cluster have been written to disk.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Check the status of a cluster")
    parser.add_argument("--name",
                        required=True,
                        help="cluster name")
    parser.add_argument("--credential",
                        help="path to the credential file")
    config = load_config(vars(parser.parse_args()))
    main(config)