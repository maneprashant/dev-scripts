#!/usr/bin/env python3.6

from matplotlib import pyplot as plt
import argparse
import sys
import subprocess
from datetime import datetime
import matplotlib
import time

matplotlib.use("Agg")


def run_cmd(cmd, use_sudo=False):
    # print(cmd)
    # time.sleep(1)
    if use_sudo == True:
        subprocess.call(["sudo"] + cmd)
    subprocess.call(cmd)


def remove_policy_gobgp(network, entryId):
    start = datetime.now()

    # add policy to global export
    run_cmd(["gobgp","global","policy","export", "del","policy-{}".format(network)])
    # add statement to policy
    run_cmd(["gobgp","policy","del","policy-{}".format(network), "statement-{}".format(network)])
    # create policy
    run_cmd(["gobgp","policy","del","policy-{}".format(network)])
    # add action to statement
    run_cmd(["gobgp","policy","statement","statement-{}".format(network),"del","action","accept"])
    # add condition to statement 
    run_cmd(["gobgp","policy","statement","statement-{}".format(network),"del","condition","prefix","prefix-{}".format(network)])
    # create policy statement 
    run_cmd(["gobgp","policy","statement","del","statement-{}".format(network)])
    # create policy prefix-set
    run_cmd(["gobgp","policy","prefix","del","prefix-{}".format(network)])

    end = datetime.now()
    timeTaken = end - start
    print(
        "{} Removed route-map entry for network {}, time-taken -> {}".format(
            entryId, network, timeTaken
        )
    )
    return timeTaken.total_seconds()


def add_policy_gobgp(network, entryId):
    '''
    gobgp policy prefix add ps3 10.33.0.0/32
    '''
    start = datetime.now()
    # create policy prefix-set
    run_cmd(["gobgp","policy","prefix","add","prefix-{}".format(network)])
    # create policy statement 
    run_cmd(["gobgp","policy","statement","add","statement-{}".format(network)])
    # add condition to statement 
    run_cmd(["gobgp","policy","statement","statement-{}".format(network),"add","condition","prefix","prefix-{}".format(network)])
    # add action to statement
    run_cmd(["gobgp","policy","statement","statement-{}".format(network),"add","action","accept"])
    # create policy
    run_cmd(["gobgp","policy","add","policy-{}".format(network)])
    # add statement to policy
    run_cmd(["gobgp","policy","add","policy-{}".format(network), "statement-{}".format(network)])
    # add policy to global export
    run_cmd(["gobgp","global","policy","export", "add","policy-{}".format(network)])

    end = datetime.now()
    timeTaken = end - start
    print("{} Added route-map entry for network: {}, time-taken: {}".format(
            entryId, network, timeTaken))
    return timeTaken.total_seconds()


def add_route_map_quagga(network, as_num, entryId):
    start = datetime.now()
    run_cmd(
        [
            "vtysh",
            "-c",
            "conf t",
            "-c",
            "route-map prepend-{} permit 10".format(network),
            "-c",
            "router bgp {}".format(as_num),
            "-c",
            "network {} route-map prepend-{}".format(network, network),
        ]
    )
    end = datetime.now()
    timeTaken = end - start
    print(
        "{} Added route-map entry for network: {}, time-taken: {}".format(
            entryId, network, timeTaken
        )
    )
    return timeTaken.total_seconds()


def remove_route_map_quagga(network, as_num, entryId):
    start = datetime.now()
    run_cmd(
        [
            "vtysh",
            "-c",
            "conf t",
            "-c",
            "router bgp {}".format(as_num),
            "-c",
            "no network {} route-map prepend-{}".format(network, network),
            "-c",
            "no route-map prepend-{} permit 10".format(network),
        ]
    )
    end = datetime.now()
    timeTaken = end - start
    print(
        "{} Removed route-map entry for network {}, time-taken -> {}".format(
            entryId, network, timeTaken
        )
    )
    return timeTaken.total_seconds()


def add_remove_rmap_test(numNetworks, as_num, is_delete, bgp_stack_name):
    count = 0
    networkIdToTimeTaken = []
    totalTimeTaken = 0
    for i in range(1, 254):
        for j in range(1, 254):
            for k in range(1, 254):
                for l in range(1, 254):
                    networkCidr = "{}.{}.{}.{}/32".format(i, j, k, l)
                    timeTakenMicroseconds = 0
                    if is_delete:
                        if bgp_stack_name == 'gobgp':
                            timeTakenMicroseconds = remove_policy_gobgp(
                                networkCidr, count + 1)
                        if bgp_stack_name == 'quagga' or bgp_stack_name == 'frr':
                            timeTakenMicroseconds = remove_route_map_quagga(
                                networkCidr, as_num, count + 1)
                    else:
                        if bgp_stack_name == 'gobgp':
                            timeTakenMicroseconds = add_policy_gobgp(
                                networkCidr, count + 1)
                        if bgp_stack_name == 'quagga' or bgp_stack_name == 'frr':
                            timeTakenMicroseconds = add_route_map_quagga(
                                networkCidr, as_num, count + 1)
                    count = count + 1
                    totalTimeTaken = totalTimeTaken + timeTakenMicroseconds 
                    networkIdToTimeTaken.append((count, timeTakenMicroseconds))
                    if numNetworks == count:
                        break
                else:
                    continue
                break
            else:
                continue
            break
        else:
            continue
        break
    plot_time_taken_vs_entryId(networkIdToTimeTaken, numNetworks, is_delete, bgp_stack_name, totalTimeTaken)


def plot_time_taken_vs_entryId(networkIdToTimetaken, numNetworks, isDelete, bgp_stack_name, totalTimeTaken):
    x_val = [x[0] for x in networkIdToTimetaken]
    y_val = [x[1] for x in networkIdToTimetaken]

    print(x_val)
    print(y_val)

    timeTakenStr = "total {} secs".format(totalTimeTaken)
    if isDelete:
        plt.title("{} route-map remove test ({})".format(bgp_stack_name, timeTakenStr))
    else:
        plt.title("{} route-map add test ({})".format(bgp_stack_name, timeTakenStr))
    plt.xlabel("Network ID (monotonically increasing with time)")
    plt.ylabel("Time Taken (sec)")
    plt.plot(x_val, y_val, linewidth=0.5)
    plt.savefig(
        "{}_bgp_test_{}_{}.pdf".format(bgp_stack_name,
            numNetworks, "remove" if isDelete else "add")
    )


def main(options):
    add_remove_rmap_test(options.num_networks, options.as_num,
                         options.delete, options.target)


def get_parser():
    """Generate a parser"""
    parser = argparse.ArgumentParser(description="BGP test tool")
    parser.add_argument(
        "-d",
        "--delete",
        action="store_true",
        default=False,
        help="Indicates delete",
    )
    parser.add_argument(
        "-n",
        "--num_networks",
        type=int,
        required=True,
        action="store",
        help="num networks to add/delete",
    )
    parser.add_argument(
        "-a",
        "--as_num",
        type=int,
        required=True,
        action="store",
        help="gateway AS number",
    )
    parser.add_argument(
        "-t",
        "--target",
        required=True,
        action="store",
        choices=['gobgp', 'quagga', 'frr'],
        help="bgp stack name",
    )

    return parser


def parse_args(args=None):
    options = get_parser().parse_args(args=args)
    return options


if __name__ == "__main__":
    sys.exit(not main(parse_args()))
