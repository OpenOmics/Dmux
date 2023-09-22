#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import argparse
from pathlib import Path
from Dmux.config import DIRECTORY_CONFIGS
from Dmux.files import runid2samplesheet, parse_samplesheet
from Dmux import utils

main_parser = argparse.ArgumentParser(prog='dmux')
sub_parser = main_parser.add_subparsers(help='sub-command help')
parser_run = sub_parser.add_parser('run', help='run subcommand help')
parser_logs = sub_parser.add_parser('logs', help='logs subcommand help')


def run(args):
    # 1. form sample sheet into snakemake configuration json
    # 2. subprocess.Popen to kick off valid demux snakemake pipeline
    # 3. Log demultiplexing pipeline execution, run time, start finish, 
    sample_sheets = [parse_samplesheet(Path(x, 'SampleSheet.csv')) for x in args.rundir]
    import ipdb; ipdb.set_trace()


def logs(args):
    # 1. check if sqlite log exists, make if not exists, return empty log message
    # 2. given it exists, query log based on cli filters
    # 3. return log pretty message
    import ipdb; ipdb.set_trace()


if __name__ == '__main__':
    main_parser = argparse.ArgumentParser(prog='dmux')
    sub_parsers = main_parser.add_subparsers(help='run subcommand help')

    parser_run = sub_parsers.add_parser('run')
    parser_run.add_argument('rundir', metavar='Run directory', nargs="+", type=utils.valid_run_input, help='Full & complete run id, no wildcards or regex (format YYMMDD_INSTRUMENTID_TIME_FLOWCELLID)')
    parser_run.set_defaults(func = run)

    parser_logs = sub_parsers.add_parser('logs', help='logs subcommand help')
    parser_logs.add_argument('Run', type=utils.valid_runid, help='Partial or full run id, can use wildcards')
    parser_logs.add_argument('--before', type=str, dest='before', default=None, required=False, help='Only look at log results demultiplexed before this date (format MMDDYYYY)')
    parser_logs.add_argument('--after', type=str, dest='after', default=None,  required=False, help='Only look at log results demultiplexed after this date (format MMDDYYYY)')
    parser_logs.set_defaults(func = logs)

    args = main_parser.parse_args()
    args.func(args)