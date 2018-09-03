#!/usr/bin/env python
import argparse
import subprocess

from common import load_config
from common import query_status


def main(args):
    all_status = query_status(args)
    if len(all_status):
        print("Error: A cluster with the name '{}' exists. ".format(args["name"]) +
              "Please choose a different cluster name.\n" +
              "Note: If you want to check the status of the cluster '{}', ".format(args["name"]) +
              "please use `./check-cluster`.")
        return
    create_command = """
    AWS_ACCESS_KEY_ID="{}" AWS_SECRET_ACCESS_KEY="{}" \
    aws ec2 run-instances \
        --image-id {} \
        --count {} \
        --instance-type {} \
        --key-name {} \
        --instance-market-options 'MarketType=spot,SpotOptions={{MaxPrice='0.3'}}' \
        --tag-specifications 'ResourceType=instance,Tags=[{{Key=cluster-name,Value={}}}]' \
        --associate-public-ip-address \
        --block-device-mappings \
            '[{{\"DeviceName\":\"/dev/xvdb\",\"VirtualName\":\"ephemeral0\"}}, \
              {{\"DeviceName\":\"/dev/xvdc\",\"VirtualName\":\"ephemeral1\"}}]' \
        --no-dry-run
    """.format(
        args["aws_access_key_id"],
        args["aws_secret_access_key"],
        args["ami"],
        args["count"],
        args["type"],
        args["key"],
        args["name"]
    )
    print("Creating the cluster...")
    subprocess.run(create_command, shell=True, check=True)
    setup_security_group = """
    AWS_ACCESS_KEY_ID="{}" AWS_SECRET_ACCESS_KEY="{}" \
    aws ec2 authorize-security-group-ingress \
        --group-name default \
        --protocol tcp \
        --port 8888 \
        --cidr 0.0.0.0/0
    """.format(
        args["aws_access_key_id"],
        args["aws_secret_access_key"],
    )
    print("Setting up security group...")
    subprocess.run(setup_security_group, shell=True, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Crate a cluster using AWS spot instances")
    parser.add_argument("-c", "--count",
                        required=True,
                        help="the number of instances in the cluster")
    parser.add_argument("--name",
                        required=True,
                        help="cluster name")
    parser.add_argument("-t", "--type",
                        help="the type of the instances")
    parser.add_argument("--ami",
                         help="AMI type")
    parser.add_argument("--credential",
                        help="path to the credential file")
    args = vars(parser.parse_args())
    if args["ami"] is None:
        args["ami"] = "ami-a4dc46db"
    if args["type"] is None:
        args["type"] = "m3.xlarge"
    config = load_config(args)
    main(config)
