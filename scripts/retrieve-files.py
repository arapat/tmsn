#!/usr/bin/env python
import argparse
import os
import subprocess
import yaml


def check_exists(path):
    return os.path.isfile(path)


def main(args):
    if not check_exists(args["key"]):
        print("Error: File '{}' does not exist.".format(args["key"]))
        return
    if not check_exists(args["neighbors"]):
        print("Error: File '{}' does not exist.".format(args["neighbors"]))
        return

    with open(args["neighbors"]) as f:
        status = f.readline()
        if status[0] != 'R':  # Not "Ready."
            print("Please run `check-cluster.py` first and "
                  "make sure all instances in the cluster is up and running.")
            return
        instances = [t.strip() for t in f if t.strip()]

    # Retrieve the files
    local_dir = args["local"]
    remote_files = args["remote"]
    key = args["key"]
    commands = []
    for idx, url in enumerate(instances):
        local_path = os.path.join(local_dir, "worker-{}".format(idx))
        command = "mkdir -p {}".format(local_path)
        subprocess.run(command, shell=True, check=True)
        for filepath in remote_files:
            commands.append(("scp -o StrictHostKeyChecking=no -i {} ubuntu@{}:{} {}"
                             "").format(key, url, filepath, local_path))
    command = " & ".join(commands)
    subprocess.run(command, shell=True, check=True)
    print("Done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Retrieve the files from the instances of a cluster")
    parser.add_argument("--remote",
                        required=True,
                        nargs='+',
                        help="Path of the remote files to be downloaded. "
                             "For multiple files, separate them using spaces")
    parser.add_argument("--local",
                        required=True,
                        help="Path of the local directory to download the remote files")
    # parser.add_argument("-k", "--key",
    #                     required=True,
    #                     help="File path of the EC2 key pair file")
    args = vars(parser.parse_args())
    args["neighbors"] = "./neighbors.txt"
    with open("credentials.yml") as f:
        creds = yaml.load(f)
        creds = list(creds.values())[0]
        args["key"] = creds["ssh_key"]
    main(args)